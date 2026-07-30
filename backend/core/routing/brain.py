import time
from datetime import datetime
import asyncio

async def process_user_intent(command: str, session_id: str = "cozmo_default_session", mute: bool = False) -> str:
    """
    The Unified Brain (Union Brain) of Cozmo.
    Processes any user input (from terminal or speech) through a tiered pipeline:
    1. Tier 1 (Semantic Layer / Reflexes): Fast, local, and deterministic.
    2. Tier 2 (Cognitive Layer / LangGraph Router): RAG, Memory, and LLM-driven actions.
    """
    from core.routing.layer1.semantic_layer import check_layer_1, execute_reflex
    from core.routing.layer2.router import run_cozmo_agent
    from actions.physical.speak import respond

    command_clean = command.strip()
    if not command_clean:
        return ""
    #  Tier 1: Check deterministic semantic reflexes
    print(f"\n [Union Brain] Checking Tier 1 (Semantic Reflexes) for: '{command_clean}'")
    layer_1_route = check_layer_1(command_clean)
    
    if layer_1_route:
        print(f" [Union Brain] Tier 1 Triggered! Route: '{layer_1_route}'")
        try:
            if await execute_reflex(layer_1_route, mute=mute):
                return ""  # Execution handled within the reflex itself
        except Exception as e:
            print(f" [Union Brain] Error executing reflex '{layer_1_route}': {e}")
            
        # Fallbacks for any unregistered reflexes
        if layer_1_route == "get_date":
            today = datetime.now().strftime("%A, %B %d, %Y")
            msg = f"Today is {today}."
            await respond(msg, mute=mute)
            return msg
        elif layer_1_route == "dock_with_charger":
            msg = "Heading back to base! Disabling AI, triggering wheel motors..."
            await respond(msg, mute=mute)
            return msg
        elif layer_1_route == "tell_joke":
            msg = "Why do robots never get scared? Because they have nerves of steel!"
            await respond(msg, mute=mute)
            return msg
            
        return ""

    #  Tier 2: Heavy Cognitive Layer (LangGraph Router)
    print(f" [Union Brain] Tier 2 Triggered (LangGraph Router) for: '{command_clean}'")
    try:
        final_answer = run_cozmo_agent(command_clean, thread_id=session_id)
        await respond(final_answer, mute=mute)
        return final_answer
    except Exception as e:
        if "ConnectError" in str(type(e)) or "ConnectError" in str(e):
            err_msg = "I'm having trouble connecting to my local brain (Ollama). Please ensure Ollama is running on port 11434."
        else:
            err_msg = f"Oops! I encountered an error: {e}"
        await respond(err_msg, mute=mute)
        return err_msg


async def stream_user_intent(command: str, session_id: str = "cozmo_default_session", mute: bool = False):
    """
    Streaming generator for the Unified Brain.
    Yields Server-Sent Events data chunks: data: {"token": "..."}\n\n
    """
    import json
    from core.routing.layer1.semantic_layer import check_layer_1, execute_reflex
    from core.routing.layer2.router import cozmo_graph
    from actions.physical.speak import respond
    from langchain_core.messages import HumanMessage

    command_clean = command.strip()
    if not command_clean:
        yield "data: [DONE]\n\n"
        return

    # Tier 1: Check deterministic semantic reflexes
    layer_1_route = check_layer_1(command_clean)
    if layer_1_route:
        if layer_1_route == "get_date":
            today = datetime.now().strftime("%A, %B %d, %Y")
            msg = f"Today is {today}."
            yield f"data: {json.dumps({'token': msg})}\n\n"
            if not mute:
                await respond(msg, mute=mute)
            yield "data: [DONE]\n\n"
            return
        elif layer_1_route == "tell_joke":
            msg = "Why do robots never get scared? Because they have nerves of steel!"
            yield f"data: {json.dumps({'token': msg})}\n\n"
            if not mute:
                await respond(msg, mute=mute)
            yield "data: [DONE]\n\n"
            return
        else:
            try:
                await execute_reflex(layer_1_route, mute=mute)
            except Exception as e:
                print(f"[Union Brain Stream] Reflex error: {e}")
            yield "data: [DONE]\n\n"
            return

    # Tier 2: Heavy Cognitive Layer (LangGraph Stream)
    config = {
        "configurable": {"thread_id": session_id},
        "metadata": {
            "session_id": session_id,
            "application_mode": "Terminal" if session_id.startswith("terminal") else "Physical_Cozmo"
        }
    }
    initial_state = {
        "messages": [HumanMessage(content=command_clean)],
        "retrieved_memories": []
    }

    accumulated = []
    loop = asyncio.get_running_loop()

    sentinel = object()
    def get_stream_iterator():
        return cozmo_graph.stream(initial_state, config=config, stream_mode="messages")

    def safe_next(it):
        return next(it, sentinel)

    try:
        iterator = iter(get_stream_iterator())
        while True:
            item = await loop.run_in_executor(None, safe_next, iterator)
            if item is sentinel:
                break
            chunk, meta = item
            if hasattr(chunk, "content") and chunk.content:
                node_name = meta.get("langgraph_node", "")
                is_chunk = type(chunk).__name__ == "AIMessageChunk"
                is_node_msg = type(chunk).__name__ == "AIMessage" and node_name in ("execute_tool_node", "weather_node", "web_search_node", "calendar_node", "code_executor_node")
                
                if (is_chunk and node_name in ("chat_node", "weather_node")) or is_node_msg:
                    token_str = str(chunk.content)
                    accumulated.append(token_str)
                    yield f"data: {json.dumps({'token': token_str})}\n\n"
    except Exception as e:
        err_msg = f"Oops! I encountered an error: {e}"
        yield f"data: {json.dumps({'token': err_msg})}\n\n"

    full_response = "".join(accumulated)
    if full_response and not mute:
        try:
            await respond(full_response, mute=mute)
        except Exception as e:
            print(f"[Brain Stream Speech Error]: {e}")

    yield "data: [DONE]\n\n"
