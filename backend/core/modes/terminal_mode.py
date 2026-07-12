import os
import sys
import socket
import subprocess
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from core.routing.semantic_layer import check_layer_1, initialize_router
from core.routing.brain import process_user_intent
import asyncio
from actions.physical.speak import respond

load_dotenv()

N8N_PORT = int(os.getenv("N8N_PORT", "5678"))
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

# --- ANSI Color Codes ---
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"
GRAY = "\033[90m"

# Enable ANSI colors on Windows Terminals
os.system("")


def is_service_running(port):
    """Checks if something is listening on the given port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def ensure_n8n_started():
    """Boots n8n in a background thread so the terminal starts immediately."""
    def check_and_boot():
        if not is_service_running(N8N_PORT):
            #sys.stdout.write(f"{GRAY}n8n is not running. Booting it up in the background...{RESET}\n")
            sys.stdout.flush()
            subprocess.Popen(["n8n", "start"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(30):
                if is_service_running(N8N_PORT):
                    #sys.stdout.write(f"\n{GRAY}[Background] n8n server is online!{RESET}\n: ")
                    sys.stdout.flush()
                    return
                time.sleep(1)
            sys.stdout.write(f"\n{GRAY}[Background] ⚠ n8n is taking a while to boot. Proceeding anyway...{RESET}\n: ")
            sys.stdout.flush()
        else:
            sys.stdout.write(f"{GRAY} n8n server is already online!{RESET}\n")
            sys.stdout.flush()

    threading.Thread(target=check_and_boot, daemon=True).start()


def ensure_ollama_started():
    """Checks if Ollama is running, and warns the user if it isn't."""
    if not is_service_running(OLLAMA_PORT):
        print(f"{BLUE}[Warning] Ollama is not running!{RESET}")
        print(f"{GRAY}Layer 2 (Router & Chat) requires Ollama to be active on port {OLLAMA_PORT}.{RESET}")
        print(f"{GRAY}Please start the Ollama application and try again.{RESET}\n")
        # We don't try to auto-start Ollama as it's usually a desktop app on Windows
        return False
    else:
        print(f"{GRAY} Ollama server is online!{RESET}\n")
        return True


def kill_n8n():
    """Forcefully terminates the background n8n (Node) process."""
    print(f"{GRAY} Sweeping background processes...{RESET}")
    try:
        # /F forces termination, /T kills child processes, /IM targets the image name
        subprocess.run(
            ["taskkill", "/F", "/T", "/IM", "node.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"{GRAY} n8n server shut down.{RESET}")
    except Exception as e:
        print(f"{GRAY}Could not automatically close n8n: {e}{RESET}")

def animate_loading(done_event):
    """Creates an animated loading text on a single line."""
    dots = ["   ",".  ", ".. ", "..."]
    i = 0
    while not done_event.is_set():
        # \r forces the terminal to overwrite the current line instead of making a new one
        sys.stdout.write(f"\r{GRAY} Working on it {dots[i % 3]}{RESET}")
        sys.stdout.flush()
        time.sleep(0.4)
        i += 1

    # Once the event is complete, clear the loading line with blank spaces
    sys.stdout.write(f"\r{' ' * 40}\r")
    sys.stdout.flush()

async def terminal_chat():
    print(f"\n{GRAY}[Booting Cozmo AI Assistant...]{RESET}")

    # Check and start n8n/Ollama before we allow user input
    ensure_n8n_started()
    ensure_ollama_started()

    await asyncio.sleep(0.1)

    print("\n=======================================")
    print("            WELCOME TO MY BRAIN!         ")
    print("=======================================\n")

    session_thread_id = f"terminal_{int(time.time())}"
    print(f"{GRAY} Session initialized with Thread ID: {session_thread_id}{RESET}\n")

    print(f"start the conversation down below.{RESET}")
    print(f"Type 'quit' to exit.{RESET}\n")
    print(f"type 'back' to go back to the main page.{RESET}\n ")

    while True:
        command = input(f"{GREEN}: ")

        # Immediately reset color so system text doesn't turn green
        print(f"{RESET}", end="")

        if command.lower() in ['quit', 'exit','q']:
            print(f"{GRAY}Shutting down brain...{RESET}")
            sys.exit(0)
        if command.lower() in ['back','b']:
            return
        if command.lower() == 'rebuild':
            if os.path.exists("cozmo_route_index.json"):
                initialize_router()
                print(f"{BLUE}Brain index deleted! Please type 'quit' and restart to rebuild.{RESET}\n")
            else:
                print(f"{GRAY}No index found to delete.{RESET}\n")
            continue

        print(f"{GRAY}Processing...{RESET}")

        # Check layer 1 for animation decision
        layer_1_route = check_layer_1(command)
        if layer_1_route:
            await process_user_intent(command, session_id=session_thread_id)
        else:
            done_event = threading.Event()
            # run the animation in a separate thread
            loading_thread = threading.Thread(target=animate_loading, args=(done_event,))
            loading_thread.start()
            try:
                await process_user_intent(command, session_id=session_thread_id)
            finally:
                done_event.set()
                if loading_thread.is_alive():
                    loading_thread.join()

        print(f"{GRAY}---------------------------------------{RESET}\n")


if __name__ == "__main__":
    asyncio.run(terminal_chat())
    import sys
    import os

    # Ensure the root folder is in the path so it can find main.py
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

    import main

    main.main()