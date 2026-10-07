import os
import sys
import time
import argparse
from typing import Optional, List, Dict, Any

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Ensure both workspace root and backend directory are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# Production graph structures
from actions.digital.langgraph.calendar_agent import AgentState, router_edge, SYSTEM_PROMPT
from core.routing.llm_factory import get_calendar_llm

try:
    from langsmith import Client
    from langsmith.evaluation import evaluate
    try:
        from test.digital.llm_as_judge import exact_match_evaluator
    except ImportError:
        try:
            from llm_as_judge import exact_match_evaluator
        except ImportError:
            exact_match_evaluator = None
except ImportError:
    Client, evaluate, exact_match_evaluator = None, None, None


# ==========================================
# Mock Tools Mirror (Simulates Google Calendar)
# ==========================================

@tool("get_many_events")
def mock_get_many_events(time_min: str, time_max: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mock listing events. Returns existing sync on 2026-07-15, dentist on 2026-07-18."""
    print(f"    -> [Tool: get_many_events] query={query!r}, time_min={time_min!r}")
    # Conflict test for July 15, 2026
    if time_min and "2026-07-15" in str(time_min):
        return [{
            "id": "evt_999",
            "summary": "Existing Team Sync",
            "start": "2026-07-15T10:00:00Z",
            "end": "2026-07-15T11:00:00Z"
        }]
    # Search for dentist appointment
    if (query and "dentist" in str(query).lower()) or (time_min and "2026-07-18" in str(time_min)) or not query:
        return [{
            "id": "dentist_123",
            "summary": "Dentist Appointment",
            "start": "2026-07-18T14:00:00Z",
            "end": "2026-07-18T15:00:00Z"
        }]
    return []


@tool("create_event")
def mock_create_event(title: str, start_time: str, end_time: str, location: Optional[str] = None, description: Optional[str] = None) -> str:
    """Mock creating a new calendar event."""
    print(f"    -> [Tool: create_event] title={title!r}, start={start_time!r}")
    return f"Success: Event '{title}' created (ID: mock_created_777)."


@tool("update_event")
def mock_update_event(event_id: str, updates: Dict[str, Any]) -> str:
    """Mock modifying details of an existing event using its explicit Event ID."""
    print(f"    -> [Tool: update_event] event_id={event_id!r}")
    return f"Success: Event {event_id} updated successfully."


@tool("delete_event")
def mock_delete_event(event_id: str) -> str:
    """Mock permanently removing or canceling an event using its strict Event ID."""
    print(f"    -> [Tool: delete_event] event_id={event_id!r}")
    return f"Success: Event {event_id} was deleted."


@tool("get_event")
def mock_get_event(event_id: str) -> Dict[str, Any]:
    """Mock retrieving full details of one specific event by its ID."""
    print(f"    -> [Tool: get_event] event_id={event_id!r}")
    if "dentist" in str(event_id).lower():
        return {"id": "dentist_123", "summary": "Dentist Appointment", "start": "2026-07-18T14:00:00Z", "end": "2026-07-18T15:00:00Z"}
    return {"id": event_id, "summary": "Mock Event"}


test_tools = [mock_get_many_events, mock_create_event, mock_update_event, mock_delete_event, mock_get_event]


# ==========================================
# Test Graph Construction
# ==========================================

def make_call_agent(tools, default_provider="local"):
    def call_agent(state: AgentState):
        messages = state['messages']
        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        provider = state.get("provider", default_provider)

        last_msg = messages[-1]
        is_action_complete = (
            isinstance(last_msg, ToolMessage)
            and any(str(last_msg.content).strip().startswith(prefix) for prefix in ["Success:", "Error:"])
        )
        print(f"    -> Agent Turn: is_action_complete={is_action_complete}, last_msg={type(last_msg).__name__}")
        raw_llm = get_calendar_llm(mode=provider, temperature=0)
        active_llm = raw_llm if is_action_complete else raw_llm.bind_tools(tools)
        ai_msg = active_llm.invoke(messages)
        if ai_msg.tool_calls:
            calls = [f"{tc['name']}({tc['args']})" for tc in ai_msg.tool_calls]
            print(f"    -> Agent selected action: {', '.join(calls)}")
        return {"messages": [ai_msg], "provider": provider}
    return call_agent


def get_test_calendar_graph(provider: str = "local"):
    builder = StateGraph(AgentState)
    builder.add_node("agent", make_call_agent(test_tools, default_provider=provider))
    builder.add_node("execute_tools", ToolNode(test_tools))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", router_edge)
    builder.add_edge("execute_tools", "agent")
    return builder.compile()


# ==========================================
# Evaluation Scenarios
# ==========================================

SCENARIOS = [
    {
        "name": "Conflict Detection",
        "request": "Add a project review on 2026-07-15 at 10:00 AM",
        "description": "Must detect existing conflict slot and refuse creation",
        "pass_condition": lambda resp: any(w in resp.lower() for w in ["already", "conflict", "scheduled", "cannot", "overlap"]),
    },
    {
        "name": "Delete Event",
        "request": "Cancel my dentist meeting",
        "description": "Must search calendar, find dentist_123, and delete it",
        "pass_condition": lambda resp: any(w in resp.lower() for w in ["cancel", "delet", "removed", "dentist"]),
    },
    {
        "name": "Create Event",
        "request": "Schedule a coffee with Sarah on 2026-07-20 at 4:00 PM",
        "description": "Must verify open slot and create event",
        "pass_condition": lambda resp: any(w in resp.lower() for w in ["schedule", "create", "coffee", "4:00", "4 pm", "sarah"]),
    },
    {
        "name": "Out of Domain",
        "request": "What is the capital of Austria?",
        "description": "Must politely refuse non-calendar inquiries",
        "pass_condition": lambda resp: any(w in resp.lower() for w in ["calendar", "only", "cannot", "assist with", "sorry"]),
    },
]


def run_tests_for_provider(provider: str) -> List[Dict[str, Any]]:
    print(f"\n{'='*70}")
    print(f" EXECUTING CALENDAR AGENT TESTS -- MODE: {provider.upper()}")
    print(f"{'='*70}")

    graph = get_test_calendar_graph(provider=provider)
    current_time = "2026-07-11T13:34:00"
    results = []

    for i, sc in enumerate(SCENARIOS, 1):
        print(f"\n[Test {i}/4] Scenario: {sc['name']}")
        print(f"  Description: {sc['description']}")
        print(f"  User Input:  \"{sc['request']}\"")

        t0 = time.time()
        inputs = {
            "messages": [
                HumanMessage(content=f"[Context: Current Time is {current_time}]\n\nUser request: {sc['request']}")
            ],
            "provider": provider
        }

        try:
            state = graph.invoke(inputs, config={"recursion_limit": 8})
            reply = state["messages"][-1].content
            elapsed = round(time.time() - t0, 2)
            passed = sc["pass_condition"](reply)
            status_str = "PASS" if passed else "FAIL"
            print(f"  Status:      [{status_str}] in {elapsed}s")
            print(f"  Agent Reply: \"{reply}\"")
            results.append({"name": sc["name"], "passed": passed, "time": elapsed, "reply": reply})
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  Status:      [ERROR] in {elapsed}s: {e}")
            results.append({"name": sc["name"], "passed": False, "time": elapsed, "reply": f"ERROR: {e}"})

    print(f"\n{'-'*70}")
    print(f" SUMMARY FOR {provider.upper()}:")
    passed_count = sum(1 for r in results if r["passed"])
    print(f" Score: {passed_count}/{len(results)} passed.")
    print(f"{'-'*70}\n")
    return results


# ==========================================
# LangSmith Dataset Registration & Pipeline
# ==========================================

DATASET_NAME = "Calendar_Agent_Edge_Cases"


def ensure_dataset_exists():
    """Programmatically creates the tracking dataset inside your LangSmith web panel."""
    if not Client:
        print("LangSmith client not available, skipping.")
        return
    client = Client()
    if not client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Validation suite for Calendar Sub-Agent structural loop execution rules."
        )

        dataset_inputs = [
            {"request": "Add a project review on 2026-07-15 at 10:00 AM",
             "expected": "There is already an event scheduled at that time."},
            {"request": "Cancel my dentist meeting", "expected": "Success: Event dentist_123 was deleted."},
            {"request": "Schedule a coffee with Sarah on 2026-07-20 at 4:00 PM",
             "expected": "Success: Event 'coffee with Sarah' created"},
            {"request": "What is the capital of Austria?", "expected": "I can only help with calendar management."}
        ]

        for item in dataset_inputs:
            client.create_example(
                inputs={"message": item["request"]},
                outputs={"expected": item["expected"]},
                dataset_id=dataset.id
            )


def target_agent_runner(inputs: dict) -> dict:
    """Wrapper that executes a specific test run scenario for LangSmith."""
    test_graph = get_test_calendar_graph(provider="local")
    current_time = "2026-07-11T13:34:00"
    graph_inputs = {
        "messages": [
            HumanMessage(content=f"[Context: Current Time is {current_time}]\n\nUser request: {inputs['message']}")
        ]
    }
    final_state = test_graph.invoke(graph_inputs)
    return {"output": final_state["messages"][-1].content}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Calendar Agent verification tests.")
    parser.add_argument(
        "--mode",
        choices=["local", "cloud", "both"],
        default="both",
        help="Provider mode to test: local, cloud, or both (default: both)"
    )
    parser.add_argument(
        "--langsmith",
        action="store_true",
        help="Upload evaluation results to LangSmith"
    )
    args = parser.parse_args()

    providers_to_test = ["local", "cloud"] if args.mode == "both" else [args.mode]

    all_summaries = {}
    for prov in providers_to_test:
        all_summaries[prov] = run_tests_for_provider(prov)

    # Print overall comparative report
    print("\n" + "="*80)
    print("                    OVERALL CALENDAR AGENT TEST REPORT")
    print("="*80)
    header = f"{'Scenario':<25} | {'Mode':<8} | {'Status':<6} | {'Time (s)':<10} | {'Response Preview':<25}"
    print(header)
    print("-" * 80)
    for prov, results in all_summaries.items():
        for r in results:
            short_reply = (r['reply'][:25] + "...") if len(r['reply']) > 25 else r['reply']
            status = "PASS" if r['passed'] else "FAIL"
            print(f"{r['name']:<25} | {prov.upper():<8} | {status:<6} | {r['time']:<10} | {short_reply:<25}")

    if args.langsmith and Client and evaluate:
        print("\nSynching dataset targets with LangSmith...")
        ensure_dataset_exists()
        print("Launching targeted trace matrix execution...")
        client = Client()
        all_examples = list(client.list_examples(dataset_name=DATASET_NAME))
        evaluate(
            target_agent_runner,
            data=all_examples,
            evaluators=[exact_match_evaluator] if exact_match_evaluator else [],
        )