import time
from datetime import datetime
from core.routing.semantic_layer import check_layer_1, execute_reflex
from core.routing.router import run_cozmo_agent
from actions.physical.speak import respond
from actions.physical.face import FaceLibrary
from actions.physical.timer import run_timer_logic
import asyncio

async def process_user_intent(command: str, session_id: str = "cozmo_default_session") -> str:
    """
    The Unified Brain (Union Brain) of Cozmo.
    Processes any user input (from terminal or speech) through a tiered pipeline:
    1. Tier 1 (Semantic Layer / Reflexes): Fast, local, and deterministic.
    2. Tier 2 (Cognitive Layer / LangGraph Router): RAG, Memory, and LLM-driven actions.
    """
    command_clean = command.strip()
    if not command_clean:
        return ""

    #  Handle Timer Command deterministically
    if "timer" in command_clean.lower():
        from actions.physical.listen import extract_seconds
        seconds = extract_seconds(command_clean)
        if seconds:
            from core.hardware.connection import cozmo_manager
            msg = f"Starting a timer for {seconds} seconds."
            await respond(msg)
            if cozmo_manager.robot_mode:
                # Trigger physical timer directly on the robot (prevents loopback deadlocks)
                try:
                    cli = cozmo_manager.get_robot()
                    if cli:
                        face = FaceLibrary(cli)
                        asyncio.create_task(run_timer_logic(seconds, face))
                except Exception as e:
                    print(f" [Union Brain] Error triggering physical timer: {e}")
            else:
                # In terminal mode, run a simulated background timer
                async def terminal_timer():
                    await asyncio.sleep(seconds)
                    print(f"\n\033[ [Timer of {seconds}s Finished!]\033[0m\n: ", end="")
                    import sys
                    sys.stdout.flush()
                asyncio.create_task(terminal_timer())
            return msg

    #  Tier 1: Check deterministic semantic reflexes
    print(f"\n [Union Brain] Checking Tier 1 (Semantic Reflexes) for: '{command_clean}'")
    layer_1_route = check_layer_1(command_clean)
    
    if layer_1_route:
        print(f" [Union Brain] Tier 1 Triggered! Route: '{layer_1_route}'")
        try:
            if await execute_reflex(layer_1_route):
                return ""  # Execution handled within the reflex itself
        except Exception as e:
            print(f" [Union Brain] Error executing reflex '{layer_1_route}': {e}")
            
        # Fallbacks for any unregistered reflexes
        if layer_1_route == "get_date":
            today = datetime.now().strftime("%A, %B %d, %Y")
            msg = f"Today is {today}."
            await respond(msg)
            return msg
        elif layer_1_route == "dock_with_charger":
            msg = "Heading back to base! Disabling AI, triggering wheel motors..."
            await respond(msg)
            return msg
        elif layer_1_route == "tell_joke":
            msg = "Why do robots never get scared? Because they have nerves of steel!"
            await respond(msg)
            return msg
            
        return ""

    #  Tier 2: Heavy Cognitive Layer (LangGraph Router)
    print(f" [Union Brain] Tier 2 Triggered (LangGraph Router) for: '{command_clean}'")
    try:
        final_answer = run_cozmo_agent(command_clean, thread_id=session_id)
        await respond(final_answer)
        return final_answer
    except Exception as e:
        if "ConnectError" in str(type(e)) or "ConnectError" in str(e):
            err_msg = "I'm having trouble connecting to my local brain (Ollama). Please ensure Ollama is running on port 11434."
        else:
            err_msg = f"Oops! I encountered an error: {e}"
        await respond(err_msg)
        return err_msg
