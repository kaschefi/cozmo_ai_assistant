import os
import sys
from typing import Optional, List, Dict, Any

# Ensure both workspace root and backend directory are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode
from langsmith import Client
from langsmith.evaluation import evaluate

try:
    from test.digital.llm_as_judge import exact_match_evaluator
except ImportError:
    try:
        from llm_as_judge import exact_match_evaluator
    except ImportError:
        exact_match_evaluator = None

# Import the base configuration/nodes from production code
try:
    from actions.digital.calendar_agent import AgentState, call_agent, router_edge
except ImportError:
    AgentState, call_agent, router_edge = None, None, None


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
    current_time = "2026-07-11T13:34:00"
    graph_inputs = {
        "messages": [
            HumanMessage(content=f"[Context: Current Time is {current_time}]\n\nUser request: {inputs['message']}")
        ]
    }
    final_state = test_graph.invoke(graph_inputs)
    return {"output": final_state["messages"][-1].content}






if __name__ == "__main__":
    print("Synching dataset targets with LangSmith...")
    ensure_dataset_exists()

    print("Launching targeted trace matrix execution...")

    # Initialize the LangSmith client
    client = Client()

    #  Fetch all raw examples from your dataset
    all_examples = list(client.list_examples(dataset_name=DATASET_NAME))

    evaluate(
        target_agent_runner,
        data=all_examples,
        evaluators=[exact_match_evaluator],
    )