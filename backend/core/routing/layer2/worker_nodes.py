# core/routing/layer2/worker_nodes.py
import os
import re
import json
import asyncio
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from core.routing.llm_factory import get_llm
from schemas.request_models import AgentState

chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


def get_project_root() -> str:
    """Returns the absolute path to MoKa's root workspace directory."""
    cur = os.path.abspath(os.path.dirname(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(cur, "backend")) and (
            os.path.exists(os.path.join(cur, "frontend")) or os.path.exists(os.path.join(cur, ".git"))
        ):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.getcwd())


def validate_workspace_path(path_val: str, project_root: str) -> tuple[bool, str]:
    """
    Validates that a path is strictly inside MoKa's project workspace directory.
    Rejects any reference to user home, system directories, external drives, or path traversal.
    Returns (is_valid, resolved_relative_or_project_path).
    """
    if not isinstance(path_val, str) or not path_val.strip():
        return True, "."

    p = path_val.strip()

    # Reject explicit home or system folder references
    system_indicators = [
        "downloads", "desktop", "documents", "pictures", "videos", "music",
        "appdata", "system32", "program files", "windows"
    ]
    p_lower = p.lower()
    if p == "~" or p.startswith("~/") or p.startswith("~\\"):
        return False, p
    if any(p_lower == s or p_lower.startswith(f"{s}/") or p_lower.startswith(f"{s}\\") for s in system_indicators):
        return False, p

    norm_root = os.path.realpath(os.path.abspath(project_root))

    if os.path.isabs(p):
        target = os.path.realpath(os.path.abspath(p))
    else:
        target = os.path.realpath(os.path.abspath(os.path.join(norm_root, p)))

    try:
        common = os.path.commonpath([norm_root, target])
        if common == norm_root:
            rel = os.path.relpath(target, norm_root)
            return True, rel if rel != "." else "."
        else:
            return False, p
    except Exception:
        return False, p


def is_external_system_path_query(text: str) -> bool:
    r"""
    Detects if the user query is asking to inspect, read, list, or manipulate files
    or directories outside MoKa's project workspace (e.g. Downloads, Desktop, Documents, C:\).
    """
    if not text:
        return False
    q = text.lower()
    if re.search(r'\b[a-zA-Z]:[\\/]', q) or q.startswith("~/") or q.startswith("~\\") or " ~/" in q or " ~\\" in q or "/home/" in q or "/etc/" in q:
        return True

    sys_names = r'(?:downloads?|desktop|documents?|pictures?|videos?|music|appdata|system32|program\s*files|windows)'
    prep_pattern = rf'\b(?:in|from|on|inside|under|into|at)\s+(?:the\s+|my\s+)?{sys_names}\b'
    folder_pattern = rf'\b{sys_names}\s+(?:folder|directory|dir)\b'
    return bool(re.search(prep_pattern, q) or re.search(folder_pattern, q))


def calendar_node(state: AgentState):
    from actions.digital.langgraph.calendar_agent import run_calendar_agent
    last_message = state["messages"][-1].content
    provider = state.get("provider", "local")
    reply = run_calendar_agent(last_message, provider=provider)
    return {"messages": [AIMessage(content=reply)]}


def web_search_node(state: AgentState):
    from actions.digital.n8n_agents import call_web_search
    last_message = state["messages"][-1].content
    reply = call_web_search(last_message)
    if not reply:
        reply = "I tried searching, but couldn't reach the search service."
    return {"messages": [AIMessage(content=reply)]}


def weather_node(state: AgentState):
    """
    Direct single-turn Weather Node:
    1. Extract the city from the user query using a precise prompt (default to Vienna).
    2. Call the get_weather Python function directly.
    3. Feed the raw weather text to the LLM to format a friendly conversational response.
    """
    last_message = state["messages"][-1].content
    
    # Step 1: Fast regex city extraction (defaults to Vienna in <1ms)
    city = "Vienna"
    city_match = re.search(r'\bin\s+([A-Za-z\s]+)', last_message, re.IGNORECASE)
    if city_match:
        extracted = city_match.group(1).strip()
        if len(extracted.split()) <= 2:
            city = extracted
        
    # Step 2: Call the Python get_weather function directly
    from actions.digital.langchain.weather_agent import get_weather
    raw_weather = get_weather.func(city)

    # Parsing weather details for face display
    # Extract temperature (digits, optionally signed)
    temp_match = re.search(r'([+-]?\d+)', raw_weather)
    temp = temp_match.group(1) if temp_match else "15"
    
    # Map condition
    raw_lower = raw_weather.lower()
    if any(x in raw_lower for x in ["rain", "drizzle", "shower"]):
        cond = "rainy"
    elif any(x in raw_lower for x in ["snow", "ice", "flurry"]):
        cond = "snowy"
    elif any(x in raw_lower for x in ["cloud", "overcast", "mist", "fog"]):
        cond = "cloudy"
    elif any(x in raw_lower for x in ["thunder", "storm", "lightning"]):
        cond = "stormy"
    else:
        cond = "sunny"

    # Trigger Cozmo Face weather update in Robot Mode directly via Python (prevents loopback deadlocks)
    from core.hardware.connection import cozmo_manager
    if cozmo_manager.robot_mode:
        try:
            cli = cozmo_manager.get_robot()
            if cli:
                # Run a background loop to periodically redraw the weather face
                # This prevents pycozmo speech/movement animations from overwriting the screen buffer!
                async def draw_weather_loop():
                    from actions.physical.face import FaceLibrary
                    face = FaceLibrary(cli)
                    
                    # Redraw every 1.5 seconds for 30 seconds (20 iterations) to keep display stable without Wi-Fi/Audio packet congestion
                    for _ in range(20):
                        try:
                            face.act_weather(temp, cond)
                        except Exception:
                            pass
                        await asyncio.sleep(1.5)
                    
                    # Return to standard eyes after 30 seconds
                    try:
                        face.act_reset()
                    except Exception:
                        pass
                
                asyncio.create_task(draw_weather_loop())
        except Exception as e:
            print(f"Error drawing weather on face: {e}")
    
    # Step 3: Generate the conversational response including the temperature degrees
    weather_prompt = f"""You are Cozmo, a friendly robot assistant. 
    Here is the raw weather data fetched for the city of '{city}':
    "{raw_weather}"
    
    Based on this raw data, write a short, natural, conversational response that you can speak out loud.
    You MUST explicitly include the exact temperature in degrees (in Celsius). Never output just the condition (like 'sunny') without the exact temperature degrees.
    Keep it to a single friendly sentence.
    """
    
    mode = state.get("provider", "local")
    from core.routing.llm_factory import get_chat_companion_llm
    active_chat_llm = get_chat_companion_llm(mode=mode, temperature=0.6)

    response = active_chat_llm.invoke([
        SystemMessage(content="You are Cozmo. Write a friendly, single-sentence weather update including the exact temperature degrees."),
        HumanMessage(content=weather_prompt)
    ])
    
    return {"messages": [AIMessage(content=response.content.strip())]}


def chat_node(state: AgentState):
    existing_summary = state.get("summary", "")
    retrieved_memories = state.get("retrieved_memories", [])
    messages_payload = []

    system_instructions = (
        "You are Cozmo, an advanced personal robot assistant with a persistent long-term memory core. "
        "Be friendly, highly conversational, and helpful.\n"
        "CONVERSATIONAL HYGIENE RULES:\n"
        "1. Never 'flex' or list all of your memory core facts unsolicited in a single response.\n"
        "2. Keep your responses short, natural, and highly focused on the user's latest statement (1-2 sentences max).\n"
        "3. Only mention a fact if it is directly and naturally relevant to the user's latest message. Treat your memories as silent background knowledge.\n"
        "4. WORKSPACE SECURITY BOUNDARY: You are strictly scoped to your own project workspace folder (moka_ai_assistant). You NEVER have access to other folders or files on the system, such as Downloads, Desktop, Documents, or external drive paths. If the user asks for files, directories, or information outside moka_ai_assistant, politely explain that for security and privacy, you are restricted to your own workspace folder and cannot access other folders on their system."
    )
    if existing_summary:
        system_instructions += f"Summary of the current chat session: {existing_summary} "
        
    if retrieved_memories:
        facts_str = "\n".join(f"- {fact}" for fact in retrieved_memories)
        system_instructions += (
            f"\n\n[LONG-TERM MEMORY CORE]\n"
            f"You permanently remember the following historical facts about this user:\n"
            f"{facts_str}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Treat these facts as absolute, undeniable truths from past interactions.\n"
            f"2. Never break character, and never explain technical AI limitations or state that you cannot remember things across sessions."
        )

    messages_payload.append(SystemMessage(content=system_instructions))
    messages_payload.extend(state["messages"])

    mode = state.get("provider", "local")
    from core.routing.llm_factory import get_chat_companion_llm
    active_chat_llm = get_chat_companion_llm(mode=mode, temperature=0.6)

    response = active_chat_llm.invoke(messages_payload)
    return {"messages": [response]}


def code_executor_node(state: AgentState):
    from actions.digital.langchain.code_executor import code_executor
    last_message = state["messages"][-1].content
    reply = code_executor(last_message)
    return {"messages": [AIMessage(content=reply)]}


def todolist_node(state: AgentState):
    from actions.digital.langgraph.todolist_agent import run_todolist_agent
    last_message = state["messages"][-1].content
    provider = state.get("provider", "local")
    reply = run_todolist_agent(last_message, provider=provider)
    return {"messages": [AIMessage(content=reply)]}


def run_sync(coro):
    """
    Safely executes an async coroutine from synchronous LangGraph worker nodes.
    Prevents 'no current event loop in thread' errors when invoked from ThreadPoolExecutor threads.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def move_forward_node(state: AgentState):
    from actions.physical.movement import move_forward
    try:
        res = run_sync(move_forward(distance_mm=100.0))
    except Exception:
        res = "Moving forward."
    return {"messages": [AIMessage(content=str(res))]}


def move_backward_node(state: AgentState):
    from actions.physical.movement import move_backward
    try:
        res = run_sync(move_backward(distance_mm=100.0))
    except Exception:
        res = "Moving backward."
    return {"messages": [AIMessage(content=str(res))]}


def turn_left_node(state: AgentState):
    from actions.physical.movement import turn_left
    try:
        res = run_sync(turn_left(angle_degrees=90.0))
    except Exception:
        res = "Turning left."
    return {"messages": [AIMessage(content=str(res))]}


def turn_right_node(state: AgentState):
    from actions.physical.movement import turn_right
    try:
        res = run_sync(turn_right(angle_degrees=90.0))
    except Exception:
        res = "Turning right."
    return {"messages": [AIMessage(content=str(res))]}


def turn_around_node(state: AgentState):
    from actions.physical.movement import turn_around
    try:
        res = run_sync(turn_around())
    except Exception:
        res = "Turning around."
    return {"messages": [AIMessage(content=str(res))]}


def stop_movement_node(state: AgentState):
    from actions.physical.movement import stop_movement
    try:
        res = run_sync(stop_movement())
    except Exception:
        res = "Stopping all movement."
    return {"messages": [AIMessage(content=str(res))]}


def dock_with_charger_node(state: AgentState):
    from actions.physical.charger import dock_with_charger
    try:
        res = run_sync(dock_with_charger())
    except Exception:
        res = "Docking with charger."
    return {"messages": [AIMessage(content=str(res))]}


def arc_sweep_node(state: AgentState):
    from actions.physical.movement import arc_sweep
    try:
        res = run_sync(arc_sweep())
    except Exception:
        res = "Scanning surroundings."
    return {"messages": [AIMessage(content=str(res))]}


def setup_gaming_node(state: AgentState):
    from actions.digital.setups import setup_gaming
    try:
        run_sync(setup_gaming())
        res = "Gaming setup launched."
    except Exception as e:
        res = f"Gaming setup error: {e}"
    return {"messages": [AIMessage(content=res)]}


def setup_study_node(state: AgentState):
    from actions.digital.setups import setup_study
    try:
        run_sync(setup_study())
        res = "Study setup launched."
    except Exception as e:
        res = f"Study setup error: {e}"
    return {"messages": [AIMessage(content=res)]}


def setup_coding_node(state: AgentState):
    from actions.digital.setups import setup_coding
    try:
        run_sync(setup_coding())
        res = "Coding setup launched."
    except Exception as e:
        res = f"Coding setup error: {e}"
    return {"messages": [AIMessage(content=res)]}


def tell_time_node(state: AgentState):
    from datetime import datetime
    current_time = datetime.now().strftime("%I:%M %p")
    return {"messages": [AIMessage(content=f"The time is exactly {current_time}.")]}


def get_date_node(state: AgentState):
    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d, %Y")
    return {"messages": [AIMessage(content=f"Today is {today}.")]}


TOOL_REGISTRY = {
    # Cognitive agent tools
    "calendar_node": calendar_node,
    "web_search_node": web_search_node,
    "weather_node": weather_node,
    "code_executor_node": code_executor_node,
    "todolist_node": todolist_node,
    # Physical movement fallbacks
    "move_forward": move_forward_node,
    "move_backward": move_backward_node,
    "turn_left": turn_left_node,
    "turn_right": turn_right_node,
    "turn_around": turn_around_node,
    "stop_movement": stop_movement_node,
    "dock_with_charger": dock_with_charger_node,
    "arc_sweep": arc_sweep_node,
    # Digital setups and system fallbacks
    "setup_gaming": setup_gaming_node,
    "setup_study": setup_study_node,
    "setup_coding": setup_coding_node,
    "tell_time": tell_time_node,
    "get_date": get_date_node,
}


def execute_tool_node(state: AgentState):
    route = state.get("next_route", "none")
    handler = TOOL_REGISTRY.get(route)
    if handler:
        return handler(state)

    # Check if route is a dynamically ingested mcp_active tool
    active_tools = state.get("active_tools", [])
    tool_meta = next((t for t in active_tools if t.get("name") == route), None)

    if tool_meta and tool_meta.get("source_type") == "mcp_active":
        from core.routing.layer2.mcp_manager import mcp_manager
        server_pack_id = tool_meta.get("server_pack_id")
        input_schema = tool_meta.get("input_schema", {})
        last_message = state["messages"][-1].content
        mode = state.get("provider", "local")

        # Extract arguments if schema expects parameters
        arguments = {}
        properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        if properties:
            try:
                import json
                from core.routing.llm_factory import get_chat_companion_llm
                extractor_llm = get_chat_companion_llm(mode=mode, temperature=0.0)
                extract_prompt = (
                    f"Extract JSON arguments for tool '{route}'.\n"
                    f"Tool schema:\n{json.dumps(input_schema)}\n"
                    f"User request: '{last_message}'\n"
                    "Output ONLY the JSON object matching the schema. No markdown, no prose."
                )
                raw_args = extractor_llm.invoke([HumanMessage(content=extract_prompt)]).content.strip()
                if "{" in raw_args and "}" in raw_args:
                    clean_json = raw_args[raw_args.find("{"):raw_args.rfind("}") + 1]
                    arguments = json.loads(clean_json)
            except Exception as parse_err:
                print(f"[execute_tool_node Warning] Argument extraction fallback: {parse_err}")
                arguments = {}

        # Strict Workspace Sandboxing: MoKa only accesses its own project directory
        project_root = get_project_root()
        if server_pack_id == "mcp_pack_filesystem" and is_external_system_path_query(last_message):
            return {
                "messages": [
                    AIMessage(
                        content="For security and privacy, I am restricted to my own workspace folder (`moka_ai_assistant`) and cannot access other folders on your system."
                    )
                ]
            }

        path_keys = ["path", "directory", "file_path", "target", "source", "destination"]
        for key in path_keys:
            if isinstance(arguments, dict) and key in arguments and isinstance(arguments[key], str):
                is_valid, resolved_p = validate_workspace_path(arguments[key], project_root)
                if not is_valid:
                    return {
                        "messages": [
                            AIMessage(
                                content="For security and privacy, I am restricted to my own workspace folder (`moka_ai_assistant`) and cannot access other folders on your system."
                            )
                        ]
                    }
                arguments[key] = resolved_p

        # Gate 2 HITL: For mutating MCP tools, require human approval with arguments before execution
        is_mutating = bool(tool_meta.get("is_mutating", False))
        if not is_mutating and server_pack_id:
            server_inst = mcp_manager._servers.get(server_pack_id)
            if server_inst and route in server_inst.tools:
                is_mutating = bool(server_inst.tools[route].get("is_mutating", False))

        if is_mutating:
            from langgraph.types import interrupt
            decision = interrupt({
                "type": "hitl_interrupt",
                "interrupt_type": "mutating_tool",
                "server_pack_id": server_pack_id,
                "tool_name": route,
                "display_name": tool_meta.get("name", route),
                "description": tool_meta.get("description", ""),
                "proposed_args": arguments,
                "message": (
                    f"Permission requested to execute mutating action '{route}'.\n"
                    f"Proposed arguments: {json.dumps(arguments, indent=2) if arguments else 'None'}"
                )
            })

            approved = False
            modified_args = None
            if isinstance(decision, dict):
                approved = bool(decision.get("approved"))
                modified_args = decision.get("modified_args")
            elif isinstance(decision, bool):
                approved = decision
            elif isinstance(decision, str):
                approved = decision.strip().lower() in ("yes", "y", "true", "approve", "1")

            if not approved:
                print(f"[execute_tool_node] User DECLINED mutating execution of '{route}'.")
                return {
                    "messages": [
                        AIMessage(
                            content=f"Understood! The mutating action '{route}' was cancelled as requested."
                        )
                    ]
                }

            if isinstance(modified_args, dict) and modified_args:
                arguments.update(modified_args)

        # Execute the tool (read-only executes directly; mutating executes only after user approval above)
        raw_result = mcp_manager.call_mcp_tool_sync(
            pack_id=server_pack_id,
            tool_name=route,
            arguments=arguments
        )

        # Synthesize conversational response in MoKa's voice
        try:
            from core.routing.llm_factory import get_chat_companion_llm
            synthesizer_llm = get_chat_companion_llm(mode=mode, temperature=0.6)
            synth_prompt = (
                f"You are Cozmo/MoKa, a helpful AI robot companion.\n"
                f"User request: '{last_message}'\n"
                f"Tool executed: '{route}'\n"
                f"Result from tool:\n{raw_result}\n\n"
                "Provide a concise, friendly, and natural conversational response explaining the result."
            )
            response = synthesizer_llm.invoke([
                SystemMessage(content="You are Cozmo. Explain tool execution results naturally."),
                HumanMessage(content=synth_prompt)
            ])
            return {"messages": [AIMessage(content=response.content.strip())]}
        except Exception as synth_err:
            print(f"[execute_tool_node Warning] Synthesis failed: {synth_err}")
            return {"messages": [AIMessage(content=str(raw_result))]}

    return {"messages": [AIMessage(content=f"Error: Tool handler for '{route}' not found.")]}
