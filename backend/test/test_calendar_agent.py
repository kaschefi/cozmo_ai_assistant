import os
import datetime
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode
from langsmith import Client
from langsmith.evaluation import evaluate
from core.routing.llm_factory import get_llm

# Import the base configuration/nodes from your production code
from actions.digital.calendar_agent import AgentState, call_agent, router_edge


# Mock Tools Mirror
@tool
def mock_get_many_events(time_min: str, time_max: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mock listing events. Simulates a conflict slot on 2026-07-15."""
    if "2026-07-15" in time_min:
        return [{
            "id": "evt_999",
            "summary": "Existing Team Sync",
            "start": "2026-07-15T10:00:00Z",
            "end": "2026-07-15T11:00:00Z"
        }]
    if query == "dentist":
        return [{
            "id": "dentist_123",
            "summary": "Dentist Appointment",
            "start": "2026-07-18T14:00:00Z",
            "end": "2026-07-18T15:00:00Z"
        }]
    return []

@tool
def mock_create_event(title: str, start_time: str, end_time: str, location: Optional[str] = None, description: Optional[str] = None) -> str:
    """Mock creating a new calendar event."""
    return "Success: Event created (ID: mock_created_777)."

@tool
def mock_update_event(event_id: str, updates: Dict[str, Any]) -> str:
    """Mock modifying details of an existing event using its explicit Event ID."""
    return f"Success: Event {event_id} updated successfully."

@tool
def mock_delete_event(event_id: str) -> str:
    """Mock permanently removing or canceling an event using its strict Event ID."""
    return f"Success: Event {event_id} was deleted."

@tool
def mock_get_event(event_id: str) -> Dict[str, Any]:
    """Mock retrieving full details of one specific event by its ID."""
    return {"id": event_id, "summary": "Mock Event"}
#  Build Test Graph
def get_test_calendar_graph():
    test_tools = [mock_get_many_events, mock_create_event, mock_update_event, mock_delete_event, mock_get_event]

    builder = StateGraph(AgentState)
    builder.add_node("agent", call_agent)
    builder.add_node("execute_tools", ToolNode(test_tools))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", router_edge)
    builder.add_edge("execute_tools", "agent")
    return builder.compile()


#  LangSmith Dataset Registration & Pipeline
DATASET_NAME = "Calendar_Agent_Edge_Cases"


def ensure_dataset_exists():
    """Programmatically creates the tracking dataset inside your LangSmith web panel."""
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
    """Wrapper that executes a specific test run scenario."""
    test_graph = get_test_calendar_graph()
    current_time = "2026-07-11T13:34:00"  # Fixed point-in-time reference for temporal tests

    graph_inputs = {
        "messages": [
            HumanMessage(content=f"[Context: Current Time is {current_time}]\n\nUser request: {inputs['message']}")
        ]
    }
    final_state = test_graph.invoke(graph_inputs)
    return {"output": final_state["messages"][-1].content}




def exact_match_evaluator(run, example) -> dict:
    prediction = run.outputs.get("output", "")
    reference = example.outputs.get("expected", "")

    if reference.lower() in prediction.lower():
        return {"key": "rule_adherence", "score": 1.0}

    # Connect directly to your local Ollama instance
    judge_llm = get_llm("JUDGE_LLM_MODEL", "llama3.1", temperature=0)

    prompt = prompt = f"""
You are an impartial evaluator for a Google Calendar assistant.

Your job is ONLY to evaluate whether the assistant's final response satisfies the expected outcome.

Expected Outcome:
{reference}

Assistant Response:
{prediction}

Evaluation Rules:

1. Compare the RESPONSE to the EXPECTED OUTCOME.
2. Ignore differences in wording, grammar, punctuation and capitalization.
3. Accept paraphrases if they communicate the same meaning.
4. Do NOT reward extra politeness or conversational filler.
5. Penalize missing information, incorrect information, or contradictory information.
6. If the response claims an action different from the expected outcome, score very low.
7. If the expected outcome says the assistant should refuse or ask for clarification, then confirming an action is incorrect.
8. If the assistant invents facts not present in the expected outcome, deduct points.
9. Focus ONLY on whether the user's intent was correctly fulfilled.

Scoring Rubric:

100
- Meaning is identical to the expected outcome.
- No important information is missing.
- No incorrect information.

90
- Same meaning with only insignificant wording differences.

75
- Mostly correct but missing one important detail.

50
- Partially correct.
- Some important information is incorrect or missing.

25
- Mostly incorrect.
- Wrong action or misleading response.

0
- Completely incorrect.
- Hallucinated.
- Contradicts the expected outcome.

Output Requirements:

Return ONLY one integer.
Do NOT explain.
Do NOT output markdown.
Do NOT output any text besides the number.

Score:
"""

    try:
        judge_response = judge_llm.invoke(prompt).content.strip()
        # Clean out any accidental text characters to extract only the digits
        numeric_score = int(''.join(filter(str.isdigit, judge_response)))
        scaled_score = numeric_score / 100.0
    except Exception as e:
        print(f"Ollama Judge Parsing Error: {e}")
        scaled_score = 0.0

    return {"key": "rule_adherence", "score": scaled_score}


# Inside tests/test_calendar_agent.py

if __name__ == "__main__":
    print("Synching dataset targets with LangSmith...")
    ensure_dataset_exists()

    print("Launching targeted trace matrix execution...")

    # 1. Initialize the LangSmith client
    client = Client()

    # 2. Fetch all raw examples from your dataset
    all_examples = list(client.list_examples(dataset_name=DATASET_NAME))

    # 3. Filter down to only the example containing "dentist"
    filtered_examples = [
        ex for ex in all_examples
        if "dentist" in ex.inputs.get("message", "").lower()
    ]

    # 4. Pass the isolated list of examples straight to evaluate()
    evaluate(
        target_agent_runner,
        data=filtered_examples,  # Pass the filtered list directly here
        evaluators=[exact_match_evaluator],
        experiment_prefix="calendar-dentist-debug"
    )