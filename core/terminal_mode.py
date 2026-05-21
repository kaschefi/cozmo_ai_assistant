import os
import sys
import socket
import subprocess
import time
import threading
from datetime import datetime
from core.semantic_layer import check_layer_1, execute_reflex, initialize_router
from core.router import run_cozmo_agent
import asyncio

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
    """Boots n8n silently in the background if it isn't running."""
    if not is_service_running(5678):
        print(f"{GRAY}n8n is not running. Booting it up in the background...{RESET}")
        subprocess.Popen(["n8n", "start"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(15):
            if is_service_running(5678):
                print(f"{GRAY} n8n server is online!{RESET}\n")
                return
            time.sleep(1)
        print(f"{GRAY}⚠ n8n is taking a while to boot. Proceeding anyway...{RESET}\n")
    else:
        print(f"{GRAY} n8n server is already online!{RESET}\n")


def ensure_ollama_started():
    """Checks if Ollama is running, and warns the user if it isn't."""
    if not is_service_running(11434):
        print(f"{BLUE}⚠ Ollama is not running!{RESET}")
        print(f"{GRAY}Layer 2 (Router & Chat) requires Ollama to be active on port 11434.{RESET}")
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

def terminal_chat():
    print("\n=======================================")
    print("            WELCOME TO MY BRAIN!         ")
    print("=======================================\n")

    # Check and start n8n/Ollama before we allow user input
    ensure_n8n_started()
    ensure_ollama_started()

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

        layer_1_route = check_layer_1(command)

        if layer_1_route:
            print(f"{GRAY} [LAYER 1 TRIGGERED]: Route -> '{layer_1_route}'{RESET}")

            # Since terminal_chat is sync, we use asyncio.run to execute the async reflex
            try:
                if asyncio.run(execute_reflex(layer_1_route)):
                    print(f"{GRAY}---------------------------------------{RESET}\n")
                    continue
            except Exception as e:
                print(f"{GRAY}Error executing reflex '{layer_1_route}': {e}{RESET}")

            # Fallback for manual routes not in registry (or if registry execution failed/not implemented)
            if layer_1_route == "get_date":
                today = datetime.now().strftime("%A, %B %d, %Y")
                print(f"{BLUE}Today is {today}.{RESET}")
            elif layer_1_route == "dock_with_charger":
                print(f"{BLUE}Heading back to base!{RESET}")
                print(f"{GRAY} [Hardware Mock]: Disabling AI, triggering wheel motors...{RESET}")
            elif layer_1_route == "tell_joke":
                print(f"{BLUE}Why do robots never get scared? Because they have nerves of steel!{RESET}")

            print(f"{GRAY}---------------------------------------{RESET}\n")
            continue

        done_event = threading.Event()
        #run the animation in a separate thread
        loading_thread = threading.Thread(target=animate_loading, args=(done_event,))
        loading_thread.start()

        try:
            final_answer = run_cozmo_agent(command)
            done_event.set()
            loading_thread.join()
            print(f"{BLUE}{final_answer}{RESET}")
        except Exception as e:
            done_event.set()
            loading_thread.join()
            if "ConnectError" in str(type(e)) or "ConnectError" in str(e):
                print(f"{BLUE}I'm having trouble connecting to my local brain (Ollama).{RESET}")
                print(f"{GRAY}Please ensure Ollama is running on port 11434.{RESET}")
            else:
                print(f"{BLUE}Oops! I encountered an error: {e}{RESET}")

        print(f"{GRAY}---------------------------------------{RESET}\n")


if __name__ == "__main__":
    terminal_chat()
    import sys
    import os

    # Ensure the root folder is in the path so it can find main.py
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    import main

    main.main()