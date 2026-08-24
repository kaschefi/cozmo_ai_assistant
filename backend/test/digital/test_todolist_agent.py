import os
import sys
import datetime
from typing import Optional, List, Dict, Any

# Ensure both workspace root and backend directory are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode

try:
    from actions.digital.todolist_agent import AgentState, call_agent, router_edge, handle_todoist_api_exception
except ImportError:
    try:
        from backend.actions.digital.todolist_agent import AgentState, call_agent, router_edge, handle_todoist_api_exception
    except ImportError:
        AgentState, call_agent, router_edge, handle_todoist_api_exception = None, None, None, None


# Mock Tools Mirror
@tool
def mock_get_tasks(project_id: Optional[str] = None, filter: Optional[str] = None, section_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mock listing active tasks."""
    return [
        {
            "id": "task_101",
            "content": "Buy groceries",
            "description": "Milk, Eggs, Bread",
            "due": {"string": "tomorrow"},
            "priority": 1,
            "project_id": "proj_1",
            "is_completed": False
        },
        {
            "id": "task_102",
            "content": "Finish report",
            "description": "Quarterly report",
            "due": None,
            "priority": 4,
            "project_id": "proj_1",
            "is_completed": False
        }
    ]


@tool
def mock_create_task(
    content: str,
    description: Optional[str] = None,
    due_string: Optional[str] = None,
    priority: Optional[int] = None,
    project_id: Optional[str] = None
) -> str:
    """Mock creating a new task."""
    return f"Success: Task '{content}' created (ID: mock_task_999)."


@tool
def mock_update_task(
    task_id: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    due_string: Optional[str] = None,
    priority: Optional[int] = None
) -> str:
    """Mock updating an existing task."""
    return f"Success: Task {task_id} updated successfully."


@tool
def mock_complete_task(task_id: str) -> str:
    """Mock completing a task."""
    return f"Success: Task {task_id} marked as completed."


@tool
def mock_delete_task(task_id: str) -> str:
    """Mock deleting a task."""
    return f"Success: Task {task_id} was deleted."


@tool
def mock_get_task(task_id: str) -> Dict[str, Any]:
    """Mock getting single task."""
    return {"id": task_id, "content": "Mock task content"}


@tool
def mock_get_projects() -> List[Dict[str, Any]]:
    """Mock listing projects."""
    return [{"id": "proj_1", "name": "Inbox"}, {"id": "proj_2", "name": "Work"}]


def get_test_todolist_graph():
    test_tools = [
        mock_get_tasks,
        mock_create_task,
        mock_update_task,
        mock_complete_task,
        mock_delete_task,
        mock_get_task,
        mock_get_projects
    ]

    builder = StateGraph(AgentState)
    builder.add_node("agent", call_agent)
    builder.add_node("execute_tools", ToolNode(test_tools))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", router_edge)
    builder.add_edge("execute_tools", "agent")
    return builder.compile()


def test_todolist_tools_direct():
    """Verify tool functions return valid responses."""
    res = mock_create_task.invoke({"content": "Call doctor"})
    assert "Success:" in res

    res_complete = mock_complete_task.invoke({"task_id": "task_101"})
    assert "Success:" in res_complete
    assert "task_101" in res_complete

    err_str = handle_todoist_api_exception(ValueError("Test error"))
    assert "Formatting Error" in err_str


if __name__ == "__main__":
    test_todolist_tools_direct()
    print("Direct todolist mock tools tests passed successfully!")
