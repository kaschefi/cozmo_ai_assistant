import sys
import uvicorn
from core.terminal_mode import terminal_chat


def main():
    # THIS LOOP IS THE SECRET!
    # It ensures that whenever a mode finishes, the menu redraws itself.
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
            terminal_chat()

        elif choice == '2':
            print("\n[Launching Cozmo Mode on localhost:8000...]\n")
            import cozmo_mode
            try:
                uvicorn.run(cozmo_mode.app, host="localhost", port=8000)
            except KeyboardInterrupt:
                print("\nShutting down Cozmo server...")

        elif choice == '3' or choice.lower() in ['q', 'quit', 'exit']:
            print("Exiting...")
            sys.exit(0)

        else:
            print("Invalid choice. Please select 1, 2, or 3.")


if __name__ == "__main__":
    main()