# backend/test/digital/routers/tools/media.py
"""
Namespace: media.*
Multimedia controls: Spotify music playback, YouTube streaming, media controls.
Synthetic tools for scaling experiments (14 tools).
"""

from typing import Dict, List

MEDIA_NAMESPACE = "media"

MEDIA_TOOLS: Dict[str, str] = {
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
    "spotify_next_track": (
        "Skips to the next song in the Spotify queue. "
        "Use when user says next song, skip this track, or play something else."
    ),
    "spotify_previous_track": (
        "Goes back to the previous song or restarts the current Spotify track. "
        "Use when user says previous song, go back a track, or play that again."
    ),
    "spotify_set_volume": (
        "Sets the Spotify player volume level inside the app. "
        "Use when user says turn the music up, make the music quieter, or set Spotify volume."
    ),
    "spotify_toggle_shuffle": (
        "Turns Spotify shuffle mode or repeat mode on or off. "
        "Use when user says shuffle my music, turn off shuffle, or repeat this song."
    ),
    "spotify_like_song": (
        "Saves the currently playing Spotify song to the Liked Songs library. "
        "Use when user says like this song, save this track, or add this to my favorites."
    ),
    "spotify_play_artist": (
        "Plays songs by a named artist or band, or a specific song or album, on Spotify. "
        "Use when user says play Coldplay, put on some Daft Punk, or play the album."
    ),
    "spotify_add_to_queue": (
        "Adds a specific song to the Spotify queue to play next without interrupting the current song. "
        "Use when user says queue this song, add to queue, or play it after this one."
    ),
    "spotify_now_playing": (
        "Tells which song, artist, and album is currently playing on Spotify. "
        "Use when user asks what song is this, who sings this, or what is playing."
    ),
    "play_podcast": (
        "Finds and plays a podcast show or its latest episode. "
        "Use when user says play a podcast, latest episode of a show, or put on a podcast."
    ),
    "set_music_sleep_timer": (
        "Sets a timer that fades out and stops the music playback after a set duration. "
        "Use when user says stop the music in 30 minutes, music sleep timer, or fall asleep to music."
    ),
}

MEDIA_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": MEDIA_NAMESPACE}
    for name, desc in MEDIA_TOOLS.items()
]
