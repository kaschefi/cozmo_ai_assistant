import os
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import sys
import uvicorn
# Ensure backend directory is in the Python search path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))


def main():
    from core.services.semantic_etl_launcher import start_semantic_etl_background, stop_semantic_etl

    start_semantic_etl_background()

    # THIS LOOP IS THE SECRET!
    # It ensures that whenever a mode finishes, the menu redraws itself.
    try:
        while True:
            print("\n=======================================")
            print("           COZMO AI ASSISTANT          ")
            print("=======================================")
            print("1. Start Terminal Mode (No Robot Required)")
            print("2. Start Cozmo Mode(Physical Robot)")
            print("3. Exit")

            try:
                choice = input("\nSelect a mode (1/2/3): ").strip()
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)

            if choice == '1':
                print("\n[Launching Terminal Mode...]\n")
                import asyncio
                from core.modes.terminal_mode import terminal_chat
                asyncio.run(terminal_chat())

            elif choice == '2':
                print("\n[Launching Cozmo Mode on localhost:8000...]\n")
                from core.modes import cozmo_mode
                try:
                    uvicorn.run(cozmo_mode.app, host="localhost", port=8000)
                except KeyboardInterrupt:
                    print("\nShutting down Cozmo server...")

            elif choice == '3' or choice.lower() in ['q', 'quit', 'exit']:
                print("Exiting...")
                sys.exit(0)

            else:
                print("Invalid choice. Please select 1, 2, or 3.")
    finally:
        stop_semantic_etl()


if __name__ == "__main__":
    main()