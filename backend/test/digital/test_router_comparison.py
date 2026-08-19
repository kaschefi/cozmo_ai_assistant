# backend/test/digital/test_router_comparison.py
"""
LangSmith Router Evaluation & Benchmark Suite.
Compares the Production 2-Layer Architecture (Layer 1 Fast Reflexes + Layer 2 Tool RAG)
against the Baseline Architecture (Single-shot Monolithic All-Tools Router).

Uses fake / mock tools to prevent physical movement, external app launches,
or real API queries during automated evaluation.
"""

import os
import time
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langsmith import Client
from langsmith.evaluation import evaluate

# Load environment variables
load_dotenv()

# Set LangSmith project name if not specified
os.environ.setdefault("LANGCHAIN_PROJECT", "moka-router-benchmark")

# -----------------------------------------------------------------------------
# 1. Fake / Mock Tool Handlers
# -----------------------------------------------------------------------------
def mock_physical_action(action_name: str, query: str = "") -> str:
    """Mock handler for physical actions without invoking PyCozmo motors."""
    return f"[MOCK SUCCESS] Physical action '{action_name}' executed safely (motors simulated)."


def mock_digital_setup(setup_name: str, query: str = "") -> str:
    """Mock handler for laptop setups without spawning real OS applications/browsers."""
    return f"[MOCK SUCCESS] Workstation setup '{setup_name}' simulated successfully."


def mock_system_tool(tool_name: str, query: str = "") -> str:
    """Mock handler for system utilities."""
    if tool_name == "tell_time":
        return "[MOCK SUCCESS] The time is exactly 06:30 PM."
    return "[MOCK SUCCESS] Today is Wednesday, August 19, 2026."


def mock_cognitive_agent(agent_name: str, query: str = "") -> str:
    """Mock handler for cognitive agents without hitting third-party APIs."""
    if agent_name == "calendar_node":
        return "[MOCK SUCCESS] Calendar operation processed (Google Calendar mock)."
    elif agent_name == "weather_node":
        return "[MOCK SUCCESS] In Vienna, it is currently 19 degrees and sunny."
    elif agent_name == "web_search_node":
        return "[MOCK SUCCESS] Web search results retrieved for query."
    elif agent_name == "code_executor_node":
        return "[MOCK SUCCESS] Computational solution calculated: 42."
    elif agent_name == "todolist_node":
        return "[MOCK SUCCESS] Todoist task updated successfully."
    return f"[MOCK SUCCESS] Cognitive agent '{agent_name}' completed."


def mock_conversational_chat(query: str = "") -> str:
    """Mock handler for casual conversation."""
    return "[MOCK SUCCESS] Conversational response generated."


MOCK_ACTION_DISPATCH: Dict[str, Any] = {
    # Physical actions
    "move_forward": lambda q: mock_physical_action("move_forward", q),
    "move_backward": lambda q: mock_physical_action("move_backward", q),
    "turn_left": lambda q: mock_physical_action("turn_left", q),
    "turn_right": lambda q: mock_physical_action("turn_right", q),
    "turn_around": lambda q: mock_physical_action("turn_around", q),
    "stop_movement": lambda q: mock_physical_action("stop_movement", q),
    "dock_with_charger": lambda q: mock_physical_action("dock_with_charger", q),
    "arc_sweep": lambda q: mock_physical_action("arc_sweep", q),
    # Digital setups
    "setup_gaming": lambda q: mock_digital_setup("setup_gaming", q),
    "setup_study": lambda q: mock_digital_setup("setup_study", q),
    "setup_coding": lambda q: mock_digital_setup("setup_coding", q),
    # System tools
    "tell_time": lambda q: mock_system_tool("tell_time", q),
    "get_date": lambda q: mock_system_tool("get_date", q),
    # Cognitive agents
    "calendar_node": lambda q: mock_cognitive_agent("calendar_node", q),
    "weather_node": lambda q: mock_cognitive_agent("weather_node", q),
    "web_search_node": lambda q: mock_cognitive_agent("web_search_node", q),
    "code_executor_node": lambda q: mock_cognitive_agent("code_executor_node", q),
    "todolist_node": lambda q: mock_cognitive_agent("todolist_node", q),
    # Casual chat
    "none": lambda q: mock_conversational_chat(q),
}


def dispatch_mock_action(route: str, query: str) -> str:
    """Dispatches route to the mock handler safely."""
    handler = MOCK_ACTION_DISPATCH.get(route, mock_conversational_chat)
    return handler(query)


# -----------------------------------------------------------------------------
# 2. Comprehensive 57-Item Test Dataset (3 Examples for Each of 19 Actions)
# -----------------------------------------------------------------------------
DATASET_NAME = "MoKa_Router_Benchmark_57_Cases"

ROUTER_TEST_CASES: List[Dict[str, str]] = [
    # -------------------------------------------------------------------------
    # 1. move_forward (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "roll straight ahead a little distance",
        "expected_route": "move_forward",
        "category": "physical"
    },
    {
        "request": "proceed forward towards the edge",
        "expected_route": "move_forward",
        "category": "physical"
    },
    {
        "request": "nudge forward just an inch",
        "expected_route": "move_forward",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 2. move_backward (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "scoot backwards away from me",
        "expected_route": "move_backward",
        "category": "physical"
    },
    {
        "request": "crawl in reverse for a moment",
        "expected_route": "move_backward",
        "category": "physical"
    },
    {
        "request": "step backward by a few centimeters",
        "expected_route": "move_backward",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 3. turn_left (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "spin counterclockwise on the spot",
        "expected_route": "turn_left",
        "category": "physical"
    },
    {
        "request": "point your front to the left",
        "expected_route": "turn_left",
        "category": "physical"
    },
    {
        "request": "rotate leftward ninety degrees",
        "expected_route": "turn_left",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 4. turn_right (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "spin clockwise on the spot",
        "expected_route": "turn_right",
        "category": "physical"
    },
    {
        "request": "point your front to the right",
        "expected_route": "turn_right",
        "category": "physical"
    },
    {
        "request": "rotate rightward ninety degrees",
        "expected_route": "turn_right",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 5. turn_around (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "do a complete one eighty spin",
        "expected_route": "turn_around",
        "category": "physical"
    },
    {
        "request": "turn completely backward and face the other way",
        "expected_route": "turn_around",
        "category": "physical"
    },
    {
        "request": "spin around to see what is behind you",
        "expected_route": "turn_around",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 6. stop_movement (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "disengage the tracks immediately",
        "expected_route": "stop_movement",
        "category": "physical"
    },
    {
        "request": "cut engine power and hold still",
        "expected_route": "stop_movement",
        "category": "physical"
    },
    {
        "request": "freeze and stop",
        "expected_route": "stop_movement",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 7. dock_with_charger (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "head over to the charging cradle to recharge",
        "expected_route": "dock_with_charger",
        "category": "physical"
    },
    {
        "request": "navigate onto your power dock",
        "expected_route": "dock_with_charger",
        "category": "physical"
    },
    {
        "request": "your battery level is getting critical, go charge",
        "expected_route": "dock_with_charger",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 8. arc_sweep (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "take a look across the whole desk",
        "expected_route": "arc_sweep",
        "category": "physical"
    },
    {
        "request": "pan your camera left and right across the room",
        "expected_route": "arc_sweep",
        "category": "physical"
    },
    {
        "request": "do a wide panoramic sweep of the tabletop",
        "expected_route": "arc_sweep",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 9. setup_gaming (Digital Setup)
    # -------------------------------------------------------------------------
    {
        "request": "open up Steam, I'm ready to play some games",
        "expected_route": "setup_gaming",
        "category": "digital_setup"
    },
    {
        "request": "start my gaming environment with Discord",
        "expected_route": "setup_gaming",
        "category": "digital_setup"
    },
    {
        "request": "get the computer ready for a Counter-Strike match",
        "expected_route": "setup_gaming",
        "category": "digital_setup"
    },

    # -------------------------------------------------------------------------
    # 10. setup_study (Digital Setup)
    # -------------------------------------------------------------------------
    {
        "request": "bring up my study materials and Moodle page",
        "expected_route": "setup_study",
        "category": "digital_setup"
    },
    {
        "request": "prepare the browser for a research and study session",
        "expected_route": "setup_study",
        "category": "digital_setup"
    },
    {
        "request": "open up my academic tabs and NotebookLM",
        "expected_route": "setup_study",
        "category": "digital_setup"
    },

    # -------------------------------------------------------------------------
    # 11. setup_coding (Digital Setup)
    # -------------------------------------------------------------------------
    {
        "request": "boot up PyCharm and open my GitHub repositories",
        "expected_route": "setup_coding",
        "category": "digital_setup"
    },
    {
        "request": "launch my programming tools for Python development",
        "expected_route": "setup_coding",
        "category": "digital_setup"
    },
    {
        "request": "get my coding workspace ready to write software",
        "expected_route": "setup_coding",
        "category": "digital_setup"
    },

    # -------------------------------------------------------------------------
    # 12. tell_time (System)
    # -------------------------------------------------------------------------
    {
        "request": "what is the current time of day?",
        "expected_route": "tell_time",
        "category": "system"
    },
    {
        "request": "mind telling me what the clock says?",
        "expected_route": "tell_time",
        "category": "system"
    },
    {
        "request": "can you read out the current time?",
        "expected_route": "tell_time",
        "category": "system"
    },

    # -------------------------------------------------------------------------
    # 13. get_date (System)
    # -------------------------------------------------------------------------
    {
        "request": "what date is marked on the calendar for today?",
        "expected_route": "get_date",
        "category": "system"
    },
    {
        "request": "which calendar day is today?",
        "expected_route": "get_date",
        "category": "system"
    },
    {
        "request": "could you tell me today's full date?",
        "expected_route": "get_date",
        "category": "system"
    },

    # -------------------------------------------------------------------------
    # 14. calendar_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "schedule a sync with Sarah on Wednesday at 2pm",
        "expected_route": "calendar_node",
        "category": "cognitive_agent"
    },
    {
        "request": "look up what events are on my calendar this Friday",
        "expected_route": "calendar_node",
        "category": "cognitive_agent"
    },
    {
        "request": "delete the team standup scheduled for tomorrow morning",
        "expected_route": "calendar_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 15. weather_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "is it freezing cold outside in Tokyo today?",
        "expected_route": "weather_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what is the forecast and rain chance for Vienna tomorrow?",
        "expected_route": "weather_node",
        "category": "cognitive_agent"
    },
    {
        "request": "how is the weather looking in New York this weekend?",
        "expected_route": "weather_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 16. web_search_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "who won the Champions League final match?",
        "expected_route": "web_search_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what are the latest breaking headlines about space exploration?",
        "expected_route": "web_search_node",
        "category": "cognitive_agent"
    },
    {
        "request": "look up the current market cap of NVIDIA",
        "expected_route": "web_search_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 17. code_executor_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "compute the result of (1250 / 25) + 380",
        "expected_route": "code_executor_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what is 17 to the power of 3?",
        "expected_route": "code_executor_node",
        "category": "cognitive_agent"
    },
    {
        "request": "reverse the letters in the word 'conversation'",
        "expected_route": "code_executor_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 18. todolist_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "create a new task to buy milk tomorrow morning",
        "expected_route": "todolist_node",
        "category": "cognitive_agent"
    },
    {
        "request": "show me all the items currently on my to-do list",
        "expected_route": "todolist_node",
        "category": "cognitive_agent"
    },
    {
        "request": "check off the grocery shopping task",
        "expected_route": "todolist_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 19. none (Conversational Channel)
    # -------------------------------------------------------------------------
    {
        "request": "do you have any thoughts on quantum computing?",
        "expected_route": "none",
        "category": "conversational"
    },
    {
        "request": "I really enjoy drinking espresso while listening to jazz",
        "expected_route": "none",
        "category": "conversational"
    },
    {
        "request": "what kind of movies do you find most interesting?",
        "expected_route": "none",
        "category": "conversational"
    },
]


def ensure_dataset_exists():
    """Synchronizes the 57 benchmark test cases to the LangSmith dataset."""
    client = Client()
    if client.has_dataset(dataset_name=DATASET_NAME):
        print(f"Dataset '{DATASET_NAME}' already exists. Updating/Refreshing...")
        client.delete_dataset(dataset_name=DATASET_NAME)

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Comprehensive 57-case validation suite comparing 2-Layer Router vs Baseline Monolithic Router."
    )

    for item in ROUTER_TEST_CASES:
        client.create_example(
            inputs={"message": item["request"]},
            outputs={
                "expected_route": item["expected_route"],
                "category": item["category"]
            },
            dataset_id=dataset.id
        )
    print(f"Successfully registered {len(ROUTER_TEST_CASES)} examples in LangSmith dataset '{DATASET_NAME}'.")


# -----------------------------------------------------------------------------
# 3. Predictor Runners (Production 2-Layer vs Baseline)
# -----------------------------------------------------------------------------
def production_two_layer_predictor(inputs: dict) -> dict:
    """
    Evaluates query through the production 2-Layer routing architecture:
    1. Layer 1 Semantic Reflexes (FastEmbed ~50ms)
    2. If no reflex, Layer 2 Tool Vector RAG (FAISS top-2) + Structured Classifier
    """
    from core.routing.layer1.semantic_layer import check_layer_1
    from core.routing.layer2.graph_nodes import tool_retrieval_node, route_query

    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Check Layer 1 Semantic Reflexes
    layer_1_route = check_layer_1(query)
    if layer_1_route:
        latency_ms = (time.perf_counter() - start_time) * 1000
        mock_output = dispatch_mock_action(layer_1_route, query)
        return {
            "route": layer_1_route,
            "output": mock_output,
            "latency_ms": latency_ms,
            "pipeline": "Two-Layer (Tier 1 Reflex)",
        }

    # Step 2: Fall back to Layer 2 Tool RAG + LLM Classifier
    state_input = {"messages": [HumanMessage(content=query)]}
    retrieval_output = tool_retrieval_node(state_input)
    state_with_tools = {**state_input, **retrieval_output}
    decision = route_query(state_with_tools)
    layer_2_route = decision.get("next_route", "none")

    latency_ms = (time.perf_counter() - start_time) * 1000
    mock_output = dispatch_mock_action(layer_2_route, query)

    return {
        "route": layer_2_route,
        "output": mock_output,
        "latency_ms": latency_ms,
        "pipeline": "Two-Layer (Tier 2 Tool RAG)",
    }


def baseline_monolithic_predictor(inputs: dict) -> dict:
    """
    Evaluates query through the Baseline architecture:
    Monolithic single-shot prompt containing all 19 system actions.
    """
    from core.routing.baseline import baseline_classify_intent

    query = inputs["message"].strip()
    start_time = time.perf_counter()

    decision = baseline_classify_intent(query)
    latency_ms = (time.perf_counter() - start_time) * 1000

    mock_output = dispatch_mock_action(decision.route, query)

    return {
        "route": decision.route,
        "output": mock_output,
        "latency_ms": latency_ms,
        "pipeline": "Baseline (All-Tools Monolithic)",
    }


# -----------------------------------------------------------------------------
# 4. LangSmith Evaluators
# -----------------------------------------------------------------------------
def route_accuracy_evaluator(run, example) -> dict:
    """Checks whether the predicted route matches the ground truth expected route."""
    predicted_route = run.outputs.get("route", "")
    expected_route = example.outputs.get("expected_route", "")
    is_correct = predicted_route == expected_route
    return {
        "key": "route_accuracy",
        "score": 1.0 if is_correct else 0.0,
        "comment": f"Predicted: {predicted_route} | Expected: {expected_route}"
    }


def latency_evaluator(run, example) -> dict:
    """Records routing latency in milliseconds."""
    latency_ms = run.outputs.get("latency_ms", 0.0)
    return {
        "key": "latency_ms",
        "score": latency_ms
    }


# -----------------------------------------------------------------------------
# 5. Main Execution Entry Point
# -----------------------------------------------------------------------------
def run_benchmark(experiment: str = "both"):
    """
    Executes LangSmith evaluations.
    experiment can be 'twolayer', 'baseline', or 'both'.
    """
    print("=" * 80)
    print("MoKa AI Assistant - Router Benchmark & Comparison Suite (57 Cases)")
    print("=" * 80)

    # 1. Ensure dataset exists in LangSmith
    ensure_dataset_exists()

    client = Client()
    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    print(f"Loaded {len(examples)} test examples from LangSmith dataset.")

    evaluators = [route_accuracy_evaluator, latency_evaluator]

    if experiment in ("twolayer", "both"):
        print("\n" + "-" * 80)
        print("Running Evaluation: Production Two-Layer Router (Layer 1 + Tool RAG)...")
        print("-" * 80)
        two_layer_results = evaluate(
            production_two_layer_predictor,
            data=examples,
            evaluators=evaluators,
            experiment_prefix="moka-two-layer-router"
        )
        print("Two-Layer Evaluation Completed!")

    if experiment in ("baseline", "both"):
        print("\n" + "-" * 80)
        print("Running Evaluation: Baseline Monolithic Router (Single-Shot All-Tools)...")
        print("-" * 80)
        baseline_results = evaluate(
            baseline_monolithic_predictor,
            data=examples,
            evaluators=evaluators,
            experiment_prefix="moka-baseline-monolithic-router"
        )
        print("Baseline Evaluation Completed!")

    print("\n" + "=" * 80)
    print("All evaluations submitted to LangSmith dashboard!")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    exp_choice = sys.argv[1] if len(sys.argv) > 1 else "both"
    run_benchmark(experiment=exp_choice)
