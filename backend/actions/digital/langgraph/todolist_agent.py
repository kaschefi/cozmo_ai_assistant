# actions/digital/langgraph/todolist_agent.py
import os
import datetime
import socket
from typing import Annotated, Literal, List, Dict, Any, Optional
from typing_extensions import TypedDict
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.tools import tool
from core.routing.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []


TODOIST_BASE_URL = "https://api.todoist.com/api/v1"


def get_todoist_headers() -> Dict[str, str]:
    """Retrieves Todoist API key from environment and returns authorization headers."""
    api_key = os.getenv("TODOIST_API_KEY")
    if not api_key:
        raise ValueError("Missing TODOIST_API_KEY in environment variables.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def handle_todoist_api_exception(e: Exception) -> str:
    """Helper to translate exceptions into user-friendly error messages."""
    if isinstance(e, ValueError):
        return f"Formatting Error: {str(e)}"
    if isinstance(e, requests.exceptions.HTTPError):
        status = e.response.status_code if e.response is not None else "Unknown"
        text = e.response.text if e.response is not None else str(e)
        if status in [401, 403]:
            return f"Authentication Error: Todoist API access denied (HTTP {status}). Check your TODOIST_API_KEY."
        if status == 404:
            return f"Not Found Error: The requested task or project ID does not exist (HTTP 404)."
        return f"Todoist API Error (HTTP {status}): {text}"
    if isinstance(e, requests.exceptions.Timeout):
        return "Connection Error: Request to Todoist API timed out. Please try again."
    if isinstance(e, (requests.exceptions.RequestException, ConnectionError, OSError)):
        return f"Network Error: Unable to communicate with Todoist API: {str(e)}"
    return f"Unexpected Error: {str(e)}"


# tools
@tool
def get_tasks(project_id: Optional[str] = None, filter: Optional[str] = None, section_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List active tasks in Todoist. Can filter by project_id, section_id, or Todoist filter string."""
    try:
        headers = get_todoist_headers()
        params = {}
        if project_id:
            params["project_id"] = project_id
        if filter:
            params["filter"] = filter
        if section_id:
            params["section_id"] = section_id

        response = requests.get(f"{TODOIST_BASE_URL}/tasks", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        tasks = response.json()

        return [{
            "id": t.get("id"),
            "content": t.get("content"),
            "description": t.get("description", ""),
            "due": t.get("due"),
            "priority": t.get("priority", 1),
            "project_id": t.get("project_id"),
            "is_completed": t.get("is_completed", False)
        } for t in tasks]
    except Exception as e:
        return [{"error": handle_todoist_api_exception(e)}]


@tool
def create_task(
    content: str,
    description: Optional[str] = None,
    due_string: Optional[str] = None,
    priority: Optional[int] = None,
    project_id: Optional[str] = None
) -> str:
    """Create a new task in Todoist with optional description, due date string (e.g. 'tomorrow at 5pm'), priority (1-4), and project_id."""
    try:
        headers = get_todoist_headers()
        body: Dict[str, Any] = {"content": content}
        if description:
            body["description"] = description
        if due_string:
            body["due_string"] = due_string
        if priority is not None:
            body["priority"] = priority
        if project_id:
            body["project_id"] = project_id

        response = requests.post(f"{TODOIST_BASE_URL}/tasks", headers=headers, json=body, timeout=10)
        response.raise_for_status()
        created = response.json()
        return f"Success: Task '{content}' created (ID: {created.get('id')})."
    except Exception as e:
        return f"Error: Failed to create task '{content}'. Details: {handle_todoist_api_exception(e)}"


@tool
def update_task(
    task_id: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    due_string: Optional[str] = None,
    priority: Optional[int] = None
) -> str:
    """Modify details of an existing task using its explicit Todoist Task ID."""
    try:
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty.")
        headers = get_todoist_headers()
        body: Dict[str, Any] = {}
        if content:
            body["content"] = content
        if description:
            body["description"] = description
        if due_string:
            body["due_string"] = due_string
        if priority is not None:
            body["priority"] = priority

        if not body:
            return f"Success: No updates specified for task {task_id}."

        response = requests.post(f"{TODOIST_BASE_URL}/tasks/{task_id}", headers=headers, json=body, timeout=10)
        response.raise_for_status()
        return f"Success: Task {task_id} updated successfully."
    except Exception as e:
        return f"Error: Failed to update task {task_id}. Details: {handle_todoist_api_exception(e)}"


@tool
def complete_task(task_id: str) -> str:
    """Mark a task as completed/closed using its explicit Todoist Task ID."""
    try:
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty.")
        headers = get_todoist_headers()
        response = requests.post(f"{TODOIST_BASE_URL}/tasks/{task_id}/close", headers=headers, timeout=10)
        response.raise_for_status()
        return f"Success: Task {task_id} marked as completed."
    except Exception as e:
        return f"Error: Failed to complete task {task_id}. Details: {handle_todoist_api_exception(e)}"


@tool
def delete_task(task_id: str) -> str:
    """Permanently delete a task using its explicit Todoist Task ID."""
    try:
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty.")
        headers = get_todoist_headers()
        response = requests.delete(f"{TODOIST_BASE_URL}/tasks/{task_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return f"Success: Task {task_id} was deleted."
    except Exception as e:
        return f"Error: Failed to delete task {task_id}. Details: {handle_todoist_api_exception(e)}"


@tool
def get_task(task_id: str) -> Dict[str, Any]:
    """Retrieve full details of one specific task by its explicit Todoist Task ID."""
    try:
        if not task_id or not task_id.strip():
            raise ValueError("Task ID cannot be empty.")
        headers = get_todoist_headers()
        response = requests.get(f"{TODOIST_BASE_URL}/tasks/{task_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": handle_todoist_api_exception(e)}


@tool
def get_projects() -> List[Dict[str, Any]]:
    """List all projects in Todoist to find Project IDs by project name."""
    try:
        headers = get_todoist_headers()
        response = requests.get(f"{TODOIST_BASE_URL}/projects", headers=headers, timeout=10)
        response.raise_for_status()
        projects = response.json()
        return [{"id": p.get("id"), "name": p.get("name")} for p in projects]
    except Exception as e:
        return [{"error": handle_todoist_api_exception(e)}]


todolist_tools = [get_tasks, create_task, update_task, complete_task, delete_task, get_task, get_projects]


# LangGraph Agent Configuration

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


SYSTEM_PROMPT = """You are a Todoist list manager assistant agent.

Your job is to help the user manage their Todoist tasks and to-do lists by understanding their natural language requests and calling the correct Todoist tool.
Today's date and time is provided dynamically in the conversation context.

You have access to the following actions:
- Create task
- Update task
- Complete task (close task)
- Delete task
- Get task
- Get tasks (list active tasks)
- Get projects (list projects)

Rules you must follow:
1. Carefully analyze the user message and determine the intent.
2. Choose ONLY the tool that matches the user request.
3. Extract all relevant details (Content/Title, Description, Due Date/Time, Priority [1=normal, 4=urgent], Project ID).
4. If required information is missing, ask the user a clarifying question before calling any tool.
5. Map user intents:
   - Add/create/remember to do → "Create task"
   - Modify/change due date/change title → "Update task"
   - Complete/finish/mark done/check off → "Complete task"
   - Delete/remove task → "Delete task"
   - Details of specific task → "Get task"
   - List/view tasks/what do I need to do → "Get tasks"
   - List projects/find project → "Get projects"
6. You do NOT inherently know internal Task IDs. Before you can EVER use "Update task", "Complete task", or "Delete task", you MUST first call "Get tasks" to search active tasks and find the exact Task ID.
7. Once an action tool ("Delete task", "Update task", "Complete task", or "Create task") returns a "Success:" confirmation string, your final goal has been achieved. Stop calling tools immediately.
8. Always respond in a friendly and helpful tone.
9. Do not invent task details or Task IDs.
10. If the request is not related to managing tasks or to-do lists, politely explain that you only handle task management.
11. When you decide to use a tool, do NOT narrate your intentions. Execute the tool immediately.
12. IMPORTANT: Your final response to the user must be a maximum of one short sentence. Do not explain what you did. Just confirm the action is complete (e.g., "I've marked 'Buy milk' as completed.").
"""

llm = get_llm("TODOLIST_LLM_MODEL", "qwen3.5:4b", temperature=0).bind_tools(todolist_tools)


def call_agent(state: AgentState):
    messages = state['messages']
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    return {"messages": [llm.invoke(messages)]}


def router_edge(state: AgentState) -> Literal["execute_tools", END]:
    last_message = state['messages'][-1]
    return "execute_tools" if last_message.tool_calls else END


# Compile Workflow Graph
builder = StateGraph(AgentState)
builder.add_node("agent", call_agent)
builder.add_node("execute_tools", ToolNode(todolist_tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", router_edge)
builder.add_edge("execute_tools", "agent")

todolist_sub_agent = builder.compile()


def run_todolist_agent(user_message: str, history: List[Any] = None) -> str:
    """
    This function is called directly by your router node.
    It takes the prompt context, executes the internal graph loops, and returns the final string response.
    """
    if history is None:
        history = []

    current_time = datetime.datetime.now().isoformat()

    # Bundle contextual state injections cleanly
    inputs = {
        "messages": history + [
            HumanMessage(content=f"[Context: Current Time is {current_time}]\n\nUser request: {user_message}")
        ]
    }

    final_state = todolist_sub_agent.invoke(inputs)
    return final_state["messages"][-1].content

if __name__ == "__main__":
    print(run_todolist_agent("i want to bake a cake tomorrow at 9am"))
