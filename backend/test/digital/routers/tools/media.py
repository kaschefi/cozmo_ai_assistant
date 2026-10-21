# backend/test/digital/routers/tools/media.py
"""
Namespace: media.*
Multimedia controls: Spotify music playback, YouTube streaming, media controls.
Prepared for scaling to 30 / 50 / 100 tools.
"""

from typing import Dict, List

MEDIA_NAMESPACE = "media"

# Active media tools (empty until physical/digital media integrations or synthetic tools are activated)
MEDIA_TOOLS: Dict[str, str] = {}

# Planned / synthetic media tools for scaling experiments
PLANNED_MEDIA_TOOLS: Dict[str, str] = {
    "spotify_play_playlist": (
        "Starts playback of a specified Spotify music playlist or genre station. "
        "Use when user wants to play music playlists, chill music, or study playlists."
    ),
    "spotify_resume_track": (
        "Resumes playback of the currently paused Spotify track or song. "
        "Use when user wants to resume music, continue song, or unpause playback."
    ),
    "spotify_pause_playback": (
        "Pauses the active Spotify music stream. "
        "Use when user tells the music to pause, stop playing songs, or silence playback."
    ),
    "youtube_play_video": (
        "Searches and launches a YouTube video in a background or active browser tab. "
        "Use when user wants to watch a video, play a podcast on YouTube, or view a clip."
    ),
}

MEDIA_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": MEDIA_NAMESPACE}
    for name, desc in MEDIA_TOOLS.items()
]
