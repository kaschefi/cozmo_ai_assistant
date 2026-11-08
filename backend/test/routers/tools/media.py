# backend/test/routers/tools/media.py
"""
Namespace: media.*
Multimedia controls: Spotify music playback, YouTube streaming, media controls.
Synthetic tools for scaling experiments (14 tools).
"""

from typing import Dict, List

MEDIA_NAMESPACE = "media"

MEDIA_TOOLS: Dict[str, str] = {
    "spotify_play_playlist": (
        "Starts playback of a Spotify music playlist, curated mixtape, chill study music, or genre station. "
        "Use when user says put on my playlist, play chill instrumental study music, or start discover weekly playlist. "
        "Controls music playlists, not specific artists or YouTube videos."
    ),
    "spotify_resume_track": (
        "Resumes playback of the currently paused Spotify track or song. "
        "Use when user says resume the paused song on Spotify, unpause my music playback, or continue playing the track where I left off."
    ),
    "spotify_pause_playback": (
        "Pauses active Spotify music streaming or song playback. "
        "Use when user says pause the music on Spotify, stop playing the song for a minute, or pause playback on speakers."
    ),
    "youtube_play_video": (
        "Searches, pulls up, and plays an online video or video tutorial on YouTube on screen. "
        "Use when user says play the latest Veritasium video on YouTube, pull up a video tutorial on my screen, or watch a video trailer on YouTube."
    ),
    "spotify_next_track": (
        "Skips to the next track in the Spotify music queue. "
        "Use when user says next song, skip this track, next track, or skip ahead."
    ),
    "spotify_previous_track": (
        "Goes back to the previous track or replays current song on Spotify. "
        "Use when user says previous song, go back a track, replay the last track, or play that again."
    ),
    "spotify_set_volume": (
        "Adjusts music playback volume level inside the Spotify desktop application. "
        "Use when user says turn up the volume inside Spotify, set Spotify player volume to fifty percent, or make music softer in Spotify."
    ),
    "spotify_toggle_shuffle": (
        "Toggles Spotify shuffle mode or repeat playback mode on or off. "
        "Use when user says turn on shuffle mode for this playlist, disable shuffle, play in order, or repeat currently playing song."
    ),
    "spotify_like_song": (
        "Saves the currently playing Spotify song to Liked Songs or favorite library. "
        "Use when user says like this song on Spotify, save this track to my favorite songs library, or add to liked tracks."
    ),
    "spotify_play_artist": (
        "Plays songs by a specific musical artist, band, or album on Spotify. "
        "Use when user says play songs by Daft Punk on Spotify, put on some Coldplay music, shuffle tracks by Hans Zimmer, or play an artist."
    ),
    "spotify_add_to_queue": (
        "Enqueues an upcoming song into the Spotify play queue to play next after the current track. "
        "Use when user says add Bohemian Rhapsody to my Spotify queue, queue up this song, or play it after this one."
    ),
    "spotify_now_playing": (
        "Identifies and tells the currently playing song title, artist name, and album on Spotify. "
        "Use when user asks what song is currently playing on Spotify, who sings this track, or what album is playing."
    ),
    "play_podcast": (
        "Finds and streams an audio podcast show or latest podcast episode (e.g. Lex Fridman, Huberman Lab). "
        "Use when user says play the latest episode of a podcast, put on a podcast show, or stream tech podcast."
    ),
    "set_music_sleep_timer": (
        "Sets a sleep timer to automatically fade out and stop music playback after a specified duration. "
        "Use when user says stop playing music after forty-five minutes, set a thirty-minute sleep timer for Spotify, or fade out and turn off the music in an hour."
    ),
}

MEDIA_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": MEDIA_NAMESPACE}
    for name, desc in MEDIA_TOOLS.items()
]
