import os
import sys

# Ensure backend is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.routing.llm_factory import (
    get_chat_companion_llm,
    get_calendar_llm,
    get_todolist_llm
)
from schemas.request_models import ChatRequest, AgentState

def test_llm_factory_modes():
    print("--- 1. Testing LLM Factory Dynamic Modes ---")
    local_chat = get_chat_companion_llm("local")
    print(f"Local Chat Class: {local_chat.__class__.__name__}, Model: {getattr(local_chat, 'model', 'N/A')}")
    assert local_chat.__class__.__name__ == "ChatOllama"

    cloud_chat = get_chat_companion_llm("cloud")
    print(f"Cloud Chat Class: {cloud_chat.__class__.__name__}, Deployment: {getattr(cloud_chat, 'deployment_name', getattr(cloud_chat, 'model_name', 'N/A'))}")
    assert cloud_chat.__class__.__name__ == "AzureChatOpenAI"

    local_cal = get_calendar_llm("local")
    print(f"Local Calendar Class: {local_cal.__class__.__name__}, Model: {getattr(local_cal, 'model', 'N/A')}")
    assert local_cal.__class__.__name__ == "ChatOllama"

    cloud_cal = get_calendar_llm("cloud")
    print(f"Cloud Calendar Class: {cloud_cal.__class__.__name__}, Deployment: {getattr(cloud_cal, 'deployment_name', getattr(cloud_cal, 'model_name', 'N/A'))}")
    assert cloud_cal.__class__.__name__ == "AzureChatOpenAI"

    local_todo = get_todolist_llm("local")
    print(f"Local Todo Class: {local_todo.__class__.__name__}")
    assert local_todo.__class__.__name__ == "ChatOllama"

    cloud_todo = get_todolist_llm("cloud")
    print(f"Cloud Todo Class: {cloud_todo.__class__.__name__}")
    assert cloud_todo.__class__.__name__ == "AzureChatOpenAI"

    print(" ALL LLM Factory tests passed successfully!\n")


def test_schema_modes():
    print("--- 2. Testing ChatRequest & AgentState Schemas ---")
    req_local = ChatRequest(message="Hello local", provider="local")
    assert req_local.provider == "local"

    req_cloud = ChatRequest(message="Hello cloud", provider="cloud")
    assert req_cloud.provider == "cloud"

    # Default fallback
    req_default = ChatRequest(message="Hello default")
    assert req_default.provider == "local"

    print(" ALL Schema tests passed successfully!\n")


if __name__ == "__main__":
    test_llm_factory_modes()
    test_schema_modes()
    print(" Everything verified successfully!")
