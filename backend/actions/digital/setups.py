import os
import webbrowser
import asyncio
import glob
from core.routing.layer1.registry import reflex_registry
from core.routing.layer2.tool_vector_db import tool_rag_registry
from actions.physical.speak import respond

tool_rag_registry.register_tool_schema(
    name="setup_gaming",
    description="Prepares the laptop for gaming, launching Steam, CS2, and Discord. Use when the user wants to play games, launch game launcher, or start gaming session."
)
tool_rag_registry.register_tool_schema(
    name="setup_study",
    description="Prepares the workstation for studying, opening Moodle, Gemini, NotebookLM, YouTube, or study materials and notes."
)
tool_rag_registry.register_tool_schema(
    name="setup_coding",
    description="Prepares the developer workspace, launching PyCharm IDE, GitHub, and coding resources for writing code or software programming."
)

@reflex_registry.reflex(
    "setup_gaming",
    [
        "set my laptop for gaming",
        "gaming mode",
        "open steam and discord",
        "time to game",
        "prepare for gaming",
        "setups game",
        "gaming work",
        "launch steam and discord for game time",
        "prepare for gaming mode",
        "set it for gaming",
    ],
    score_threshold=0.80
)
async def setup_gaming():
    """Launches gaming applications like Steam and Discord."""
    await respond("Launching gaming setup...")
    try:
        # os.startfile is the most native way to open URIs and apps on Windows
        os.startfile("steam://")
        os.startfile("steam://rungameid/730")
        # Launch Discord
        discord_path = os.path.expandvars(r"%LocalAppData%\Discord\Update.exe")
        # We pass the arguments as a separate string if needed, or just launch the update executable
        os.system(f'"{discord_path}" --processStart Discord.exe')
        await respond("Gaming setup launched successfully.")

    except Exception as e:
        await respond(f"Error launching gaming setup: {e}")

@reflex_registry.reflex(
    "setup_study",
    [
        "set it for study",
        "study mode",
        "time to study",
        "prepare my laptop for study",
        "open my study tabs",
        "study work",
        "setups study",
        "open my moodle and study tabs",
        "prepare for studying mode",
        "set my laptop for study",
    ],
    score_threshold=0.80
)
async def setup_study():
    """Opens study-related websites."""
    await respond("Launching study setup...")
    try:
        # Open default browser with specified URLs
        webbrowser.open("https://www.youtube.com")
        webbrowser.open("https://notebooklm.google.com/")
        webbrowser.open("https://gemini.google.com/app")
        webbrowser.open("https://moodle.hcw.ac.at/")
        await respond("Study setup launched successfully.")
    except Exception as e:
        await respond(f"Error launching study setup: {e}")

@reflex_registry.reflex(
    "setup_coding",
    [
        "set it for coding",
        "set my laptop for coding",
        "coding mode",
        "time to code",
        "prepare for coding",
        "setups code",
        "prepare my laptop for programming and open pycharm",
        "launch my coding setup with github and ide",
        "coding setup",
    ],
    score_threshold=0.80
)
async def setup_coding():
    await respond("Launching coding setup...")
    try:
        webbrowser.open("https://github.com/")
        webbrowser.open("https://www.youtube.com/")
        webbrowser.open("https://gemini.google.com/app")
        search_pattern = r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe"
        matches = glob.glob(search_pattern)
        if not matches:
            await respond("Error: Could not find PyCharm in the JetBrains folder.")
            return
        latest_pycharm = sorted(matches)[-1]

        await respond(f"Launching PyCharm from: {latest_pycharm}")
        os.startfile(latest_pycharm)
    except Exception as e:
        await respond(f"Error launching coding setup: {e}")

if __name__ == "__main__":
    asyncio.run(setup_coding())