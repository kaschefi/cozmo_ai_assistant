import time
from datetime import datetime
import asyncio

async def process_user_intent(command: str, session_id: str = "cozmo_default_session", mute: bool = False, provider: str = "local") -> str:
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
            handled, result_msg = await execute_reflex(layer_1_route, mute=mute)
            if handled:
                return result_msg
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
        final_answer = await asyncio.to_thread(run_cozmo_agent, command_clean, session_id, provider)
        await respond(final_answer, mute=mute)
        return final_answer
    except Exception as e:
        if "ConnectError" in str(type(e)) or "ConnectError" in str(e):
            err_msg = "I'm having trouble connecting to my local brain (Ollama). Please ensure Ollama is running on port 11434."
        else:
            err_msg = f"Oops! I encountered an error: {e}"
        await respond(err_msg, mute=mute)
        return err_msg


async def stream_user_intent(command: str, session_id: str = "cozmo_default_session", mute: bool = False, provider: str = "local"):
    """
    Streaming generator for the Unified Brain.
    Yields Server-Sent Events data chunks:
    - Status telemetry: data: {"type": "status", "stage": "...", "title": "...", "text": "...", "step": 1, ...}\n\n
    - Token chunks: data: {"type": "token", "token": "..."}\n\n
    - Terminal: data: [DONE]\n\n
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

    # Pipeline Init Event
    yield f"data: {json.dumps({'type': 'status', 'stage': 'intent', 'title': 'INTENT ROUTER', 'text': 'Parsing user query & checking semantic reflexes...', 'step': 1, 'provider': provider})}\n\n"

    # Tier 1: Check deterministic semantic reflexes
    layer_1_route = check_layer_1(command_clean)
    if layer_1_route:
        friendly_reflex = layer_1_route.replace('_', ' ').title()
        yield f"data: {json.dumps({'type': 'status', 'stage': 'reflex', 'title': 'FAST-PATH REFLEX', 'text': f'Triggered semantic reflex: {friendly_reflex}', 'step': 2, 'tool': layer_1_route, 'provider': 'reflex'})}\n\n"
        if layer_1_route == "get_date":
            today = datetime.now().strftime("%A, %B %d, %Y")
            msg = f"Today is {today}."
            yield f"data: {json.dumps({'type': 'token', 'token': msg})}\n\n"
            if not mute:
                await respond(msg, mute=mute)
            yield "data: [DONE]\n\n"
            return
        elif layer_1_route == "tell_joke":
            msg = "Why do robots never get scared? Because they have nerves of steel!"
            yield f"data: {json.dumps({'type': 'token', 'token': msg})}\n\n"
            if not mute:
                await respond(msg, mute=mute)
            yield "data: [DONE]\n\n"
            return
        else:
            try:
                handled, result_msg = await execute_reflex(layer_1_route, mute=mute)
                if result_msg:
                    yield f"data: {json.dumps({'type': 'token', 'token': result_msg})}\n\n"
            except Exception as e:
                print(f"[Union Brain Stream] Reflex error: {e}")
            yield "data: [DONE]\n\n"
            return

    # Tier 2: Heavy Cognitive Layer (LangGraph Stream)
    yield f"data: {json.dumps({'type': 'status', 'stage': 'memory', 'title': 'EPISODIC MEMORY', 'text': 'Querying long-term memory core & user profile...', 'step': 1, 'provider': provider})}\n\n"

    config = {
        "configurable": {"thread_id": session_id},
        "metadata": {
            "session_id": session_id,
            "application_mode": "Terminal" if session_id.startswith("terminal") else "Physical_Cozmo"
        }
    }
    initial_state = {
        "messages": [HumanMessage(content=command_clean)],
        "retrieved_memories": [],
        "provider": provider
    }

    accumulated = []
    loop = asyncio.get_running_loop()

    sentinel = object()
    def get_stream_iterator():
        return cozmo_graph.stream(initial_state, config=config, stream_mode=["messages", "updates"])

    def safe_next(it):
        return next(it, sentinel)

    try:
        iterator = iter(get_stream_iterator())
        while True:
            item = await loop.run_in_executor(None, safe_next, iterator)
            if item is sentinel:
                break

            # Process structured dual stream updates
            if isinstance(item, tuple) and len(item) == 2:
                stream_type, payload = item
                if stream_type == "updates" and isinstance(payload, dict):
                    for node_name, node_data in payload.items():
                        if node_name == "memory_retrieval_node":
                            mems = node_data.get("retrieved_memories", [])
                            txt = f"Recalled {len(mems)} relevant facts from memory" if mems else "Memory core scanned (no prior facts)"
                            yield f"data: {json.dumps({'type': 'status', 'stage': 'memory_done', 'title': 'EPISODIC MEMORY', 'text': txt, 'step': 1, 'memories_count': len(mems)})}\n\n"
                            yield f"data: {json.dumps({'type': 'status', 'stage': 'tools_rag', 'title': 'TOOL VECTOR SEARCH', 'text': 'Searching tool embedding space...', 'step': 2})}\n\n"

                        elif node_name == "tool_retrieval_node":
                            tools = node_data.get("active_tools", [])
                            tool_names = [t.get("name", "") for t in tools if isinstance(t, dict)]
                            txt = f"Identified candidates: {', '.join(tool_names)}" if tool_names else "Direct conversation route"
                            yield f"data: {json.dumps({'type': 'status', 'stage': 'tools_matched', 'title': 'TOOL CANDIDATES', 'text': txt, 'step': 2, 'tools': tool_names})}\n\n"
                            yield f"data: {json.dumps({'type': 'status', 'stage': 'router', 'title': 'INTENT ROUTER', 'text': 'Evaluating route with neural classifier...', 'step': 2})}\n\n"

                        elif node_name == "route_query":
                            route = node_data.get("next_route", "none")
                            if route and route != "none":
                                friendly = route.replace("_node", "").replace("_agent", "").replace("_", " ").title() + " Agent"
                                yield f"data: {json.dumps({'type': 'status', 'stage': 'routed', 'title': 'TOOL SELECTED', 'text': f'Dispatched to {friendly}', 'step': 2, 'tool': route})}\n\n"
                                yield f"data: {json.dumps({'type': 'status', 'stage': 'executing', 'title': 'EXECUTING AGENT', 'text': f'Calling {friendly}...', 'step': 3, 'tool': route})}\n\n"
                            else:
                                yield f"data: {json.dumps({'type': 'status', 'stage': 'routed', 'title': 'CHAT ROUTE', 'text': 'Direct conversational synthesis selected', 'step': 2, 'tool': 'none'})}\n\n"
                                yield f"data: {json.dumps({'type': 'status', 'stage': 'synthesizing', 'title': 'RESPONSE SYNTHESIS', 'text': 'Formulating natural response...', 'step': 3})}\n\n"

                        elif node_name in ("execute_tool_node", "weather_node", "calendar_node", "web_search_node", "todolist_node", "code_executor_node"):
                            yield f"data: {json.dumps({'type': 'status', 'stage': 'tool_complete', 'title': 'TOOL FINISHED', 'text': 'Tool execution complete, preparing answer...', 'step': 3})}\n\n"

                elif stream_type == "messages":
                    chunk, meta = payload
                    if hasattr(chunk, "content") and chunk.content:
                        node_name = meta.get("langgraph_node", "") if isinstance(meta, dict) else ""
                        is_chunk = type(chunk).__name__ == "AIMessageChunk"
                        is_node_msg = type(chunk).__name__ == "AIMessage" and node_name in ("execute_tool_node", "weather_node", "web_search_node", "calendar_node", "code_executor_node", "todolist_node")
                        
                        if (is_chunk and node_name in ("chat_node", "weather_node")) or is_node_msg:
                            token_str = str(chunk.content)
                            accumulated.append(token_str)
                            yield f"data: {json.dumps({'type': 'token', 'token': token_str})}\n\n"

            # Fallback for plain messages stream item
            elif isinstance(item, tuple) and len(item) == 2 and not isinstance(item[0], str):
                chunk, meta = item
                if hasattr(chunk, "content") and chunk.content:
                    token_str = str(chunk.content)
                    accumulated.append(token_str)
                    yield f"data: {json.dumps({'type': 'token', 'token': token_str})}\n\n"

    except Exception as e:
        err_msg = f"Oops! I encountered an error: {e}"
        yield f"data: {json.dumps({'type': 'token', 'token': err_msg})}\n\n"

    full_response = "".join(accumulated)
    if full_response and not mute:
        try:
            await respond(full_response, mute=mute)
        except Exception as e:
            print(f"[Brain Stream Speech Error]: {e}")

    yield "data: [DONE]\n\n"
