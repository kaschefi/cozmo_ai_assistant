import os
import sys
import socket
import subprocess
import time
import threading
from datetime import datetime
from core.semantic_layer import check_layer_1
from core.router import run_cozmo_agent

# --- ANSI Color Codes ---
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"
GRAY = "\033[90m"

# Enable ANSI colors on Windows Terminals
os.system("")


def is_n8n_running(port=5678):
    """Checks if something (n8n) is listening on the given port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def ensure_n8n_started():
    """Boots n8n silently in the background if it isn't running."""
    if not is_n8n_running():
        print(f"{GRAY}n8n is not running. Booting it up in the background...{RESET}")

        # shell=True ensures Windows finds the n8n command in your global PATH
        subprocess.Popen(
            ["n8n", "start"],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait up to 15 seconds for it to initialize
        for _ in range(15):
            if is_n8n_running():
                print(f"{GRAY} n8n server is online!{RESET}\n")
                return
            time.sleep(1)

        print(f"{GRAY}⚠n8n is taking a while to boot. Proceeding anyway...{RESET}\n")
    else:
        print(f"{GRAY} n8n server is already online!{RESET}\n")


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
    print("=======================================")
    print("            COZMO BRAIN")
    print("=======================================\n")

    # Check and start n8n before we allow user input
    ensure_n8n_started()

    print(f"{GRAY}Type 'quit' to exit.{RESET}\n")

    while True:
        # The prompt is invisible, but makes the user's typed text GREEN
        command = input(f":{GREEN}")

        # Immediately reset color so system text doesn't turn green
        print(f"{RESET}", end="")

        if command.lower() in ['quit', 'exit']:
            print(f"{GRAY}Shutting down brain...{RESET}")
            break

        print(f"{GRAY}Processing...{RESET}")

        layer_1_route = check_layer_1(command)

        if layer_1_route:
            print(f"{GRAY} [LAYER 1 TRIGGERED]: Route -> '{layer_1_route}'{RESET}")

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

        final_answer = run_cozmo_agent(command)

        done_event.set()
        loading_thread.join()
        print(f"{BLUE}{final_answer}{RESET}")
        print(f"{GRAY}---------------------------------------{RESET}\n")


if __name__ == "__main__":
    terminal_chat()