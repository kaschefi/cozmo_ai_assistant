import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from actions.digital.langgraph.calendar_agent import run_calendar_agent


def test_calendar_plan_for_today():
    prompt = "whats my plan for today"

    print("=" * 70)
    print(" TESTING CALENDAR AGENT: 'whats my plan for today'")
    print("=" * 70)

    # 1. Local (Ollama) execution
    print("\n--- [1] Executing with LOCAL Provider (Ollama) ---")
    t0 = time.time()
    try:
        local_response = run_calendar_agent(prompt, provider="local")
        elapsed_local = round(time.time() - t0, 2)
        print(f"Status: SUCCESS ({elapsed_local}s)")
        print(f"Response:\n{local_response}\n")
    except Exception as e:
        elapsed_local = round(time.time() - t0, 2)
        print(f"Status: ERROR ({elapsed_local}s): {e}\n")
        local_response = None

    # 2. Cloud (Azure Phi-4-mini) execution
    print("\n--- [2] Executing with CLOUD Provider (Azure Phi-4-mini) ---")
    t1 = time.time()
    try:
        cloud_response = run_calendar_agent(prompt, provider="cloud")
        elapsed_cloud = round(time.time() - t1, 2)
        print(f"Status: SUCCESS ({elapsed_cloud}s)")
        print(f"Response:\n{cloud_response}\n")
    except Exception as e:
        elapsed_cloud = round(time.time() - t1, 2)
        print(f"Status: ERROR ({elapsed_cloud}s): {e}\n")
        cloud_response = None

    print("=" * 70)
    print(" COMPARISON SUMMARY")
    print("=" * 70)
    print(f"Local Model Status:  {'PASS' if local_response else 'FAIL'} ({elapsed_local}s)")
    print(f"Cloud Model Status:  {'PASS' if cloud_response else 'FAIL'} ({elapsed_cloud}s)")
    print("=" * 70)


if __name__ == "__main__":
    test_calendar_plan_for_today()
