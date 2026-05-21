import os
import webbrowser
import asyncio
import glob
from core.registry import reflex_registry

@reflex_registry.reflex("setup_gaming", ["set my laptop for gaming",
        "gaming mode",
        "open steam and discord",
        "time to game",
        "prepare for gaming",
        "setups game",
        "gaming work",])
async def setup_gaming():
    """Launches gaming applications like Steam and Discord."""
    print("Launching Gaming Setup...")
    try:
        # os.startfile is the most native way to open URIs and apps on Windows
        os.startfile("steam://")
        os.startfile("steam://rungameid/730")
        # Launch Discord
        discord_path = os.path.expandvars(r"%LocalAppData%\Discord\Update.exe")
        # We pass the arguments as a separate string if needed, or just launch the update executable
        os.system(f'"{discord_path}" --processStart Discord.exe')
        print("Gaming setup launched successfully.")

    except Exception as e:
        print(f"Error launching gaming setup: {e}")

@reflex_registry.reflex("setup_study", ["set it for study",
        "study mode",
        "time to study",
        "prepare my laptop for study",
        "open my study tabs",
        "study work",
        "setups study",])
async def setup_study():
    """Opens study-related websites."""
    print("Launching Study Setup...")
    try:
        # Open default browser with specified URLs
        webbrowser.open("https://www.youtube.com")
        webbrowser.open("https://notebooklm.google.com/")
        webbrowser.open("https://gemini.google.com/app")
        webbrowser.open("https://moodle.hcw.ac.at/")
    except Exception as e:
        print(f"Error launching study setup: {e}")

@reflex_registry.reflex("setup_coding", ["set it for coding",
        "set my laptop for coding",
        "coding mode",
        "time to code",
        "prepare for coding",
        "setups code",])
async def setup_coding():
    print("Launching Coding Setup...")
    try:
        webbrowser.open("https://github.com/")
        webbrowser.open("https://www.youtube.com/")
        webbrowser.open("https://gemini.google.com/app")
        search_pattern = r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe"
        matches = glob.glob(search_pattern)
        if not matches:
            print("Error: Could not find PyCharm in the JetBrains folder.")
            return
        latest_pycharm = sorted(matches)[-1]

        print(f"Launching PyCharm from: {latest_pycharm}")
        os.startfile(latest_pycharm)
    except Exception as e:
        print(f"Error launching coding setup: {e}")

if __name__ == "__main__":
    asyncio.run(setup_coding())