"""
JARVIS Spotify Controller via Official Spotify Web API (Spotipy)
Provides rich playback control: search & play, pause, resume, next, previous, volume, and track status.
Falls back gracefully if credentials are not configured or device is offline.
"""

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import config
from core.logger import logger

# Cache token inside data/ directory
CACHE_DIR = config.BASE_DIR / "data"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / ".spotify_token_cache"

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "user-library-read",
]


class SpotifyClient:
    def __init__(self):
        self._sp = None
        self._auth_manager = None
        self._lock = threading.Lock()

    def is_configured(self) -> bool:
        """Checks if Spotify Client ID and Secret are provided in config or env."""
        cid = getattr(config, "SPOTIFY_CLIENT_ID", "").strip() or os.getenv("SPOTIFY_CLIENT_ID", "").strip()
        secret = getattr(config, "SPOTIFY_CLIENT_SECRET", "").strip() or os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
        return bool(cid and secret)

    def _init_client(self) -> bool:
        """Initializes Spotipy client with OAuth authentication."""
        if not self.is_configured():
            return False

        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            cid = getattr(config, "SPOTIFY_CLIENT_ID", "").strip() or os.getenv("SPOTIFY_CLIENT_ID", "").strip()
            secret = getattr(config, "SPOTIFY_CLIENT_SECRET", "").strip() or os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
            redirect_uri = getattr(config, "SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback").strip()

            self._auth_manager = SpotifyOAuth(
                client_id=cid,
                client_secret=secret,
                redirect_uri=redirect_uri,
                scope=" ".join(SCOPES),
                cache_path=str(CACHE_FILE),
                open_browser=True,
            )
            self._sp = spotipy.Spotify(auth_manager=self._auth_manager)
            return True
        except Exception as e:
            logger.log("ERROR", f"Failed to initialize Spotify client: {e}")
            return False

    def get_sp(self):
        """Returns the active Spotipy client, initializing if needed."""
        with self._lock:
            if self._sp is None:
                if not self._init_client():
                    return None
            return self._sp

    def _ensure_active_device(self, sp) -> Optional[str]:
        """Finds or wakes up an active Spotify device."""
        try:
            devices = sp.devices().get("devices", [])
            for d in devices:
                if d.get("is_active"):
                    return d.get("id")

            # If device exists but none active, use the first available device
            if devices:
                target_id = devices[0].get("id")
                try:
                    sp.transfer_playback(device_id=target_id, force_play=False)
                    time.sleep(0.5)
                except Exception:
                    pass
                return target_id

            # If no devices registered in Spotify API, try launching desktop Spotify app
            logger.log("ACTION", "No active Spotify device found. Launching desktop Spotify...")
            subprocess.Popen(["powershell", "-c", "Start-Process 'spotify:'"], shell=True)
            time.sleep(2.5)

            # Retry fetching devices
            devices = sp.devices().get("devices", [])
            if devices:
                return devices[0].get("id")
        except Exception as e:
            logger.log("DEBUG", f"Device resolution notice: {e}")

        return None

    def play(self, query: Optional[str] = None) -> str:
        """
        Plays a specific song/artist/album if query is provided, or resumes current playback.
        """
        sp = self.get_sp()
        if not sp:
            return "Spotify API credentials not configured."

        try:
            device_id = self._ensure_active_device(sp)

            if query:
                # Search for track
                logger.log("ACTION", f"Spotify API: Searching for '{query}'")
                results = sp.search(q=query, type="track,artist,album,playlist", limit=1)
                tracks = results.get("tracks", {}).get("items", [])

                if tracks:
                    track = tracks[0]
                    track_uri = track.get("uri")
                    track_name = track.get("name")
                    artist_name = track.get("artists", [{}])[0].get("name", "Unknown Artist")

                    sp.start_playback(device_id=device_id, uris=[track_uri])
                    logger.log("SUCCESS", f"Spotify API: Playing '{track_name}' by {artist_name}")
                    return f"Playing '{track_name}' by {artist_name} on Spotify."

                # Fallback to artist
                artists = results.get("artists", {}).get("items", [])
                if artists:
                    artist = artists[0]
                    sp.start_playback(device_id=device_id, context_uri=artist.get("uri"))
                    return f"Playing top tracks for {artist.get('name')} on Spotify."

                return f"No results found on Spotify for '{query}'."
            else:
                # Resume playback
                sp.start_playback(device_id=device_id)
                logger.log("SUCCESS", "Spotify API: Playback resumed.")
                return "Spotify playback resumed."

        except Exception as e:
            err_msg = str(e)
            logger.log("ERROR", f"Spotify play error: {err_msg}")
            if "NO_ACTIVE_DEVICE" in err_msg or "Device not found" in err_msg:
                # Launch Spotify app to register device
                search_q = query or ""
                subprocess.Popen(["powershell", "-c", f"Start-Process 'spotify:search:{search_q}'"], shell=True)
                return "Launched Spotify desktop app. Please start playback once so Spotify can link your session."
            return f"Spotify playback error: {err_msg}"

    def pause(self) -> str:
        """Pauses Spotify playback."""
        sp = self.get_sp()
        if not sp:
            return "Spotify API credentials not configured."

        try:
            sp.pause_playback()
            logger.log("SUCCESS", "Spotify API: Playback paused.")
            return "Spotify playback paused."
        except Exception as e:
            return f"Could not pause Spotify: {e}"

    def resume(self) -> str:
        """Resumes Spotify playback."""
        return self.play(query=None)

    def next_track(self) -> str:
        """Skips to the next track."""
        sp = self.get_sp()
        if not sp:
            return "Spotify API credentials not configured."

        try:
            sp.next_track()
            time.sleep(0.4)
            current = self.get_current_track()
            if current:
                return f"Skipped to next track: {current}."
            return "Skipped to next track on Spotify."
        except Exception as e:
            return f"Could not skip track: {e}"

    def previous_track(self) -> str:
        """Goes to the previous track."""
        sp = self.get_sp()
        if not sp:
            return "Spotify API credentials not configured."

        try:
            sp.previous_track()
            time.sleep(0.4)
            current = self.get_current_track()
            if current:
                return f"Playing previous track: {current}."
            return "Playing previous track on Spotify."
        except Exception as e:
            return f"Could not go to previous track: {e}"

    def set_volume(self, volume_percent: int) -> str:
        """Sets Spotify volume (0 - 100)."""
        sp = self.get_sp()
        if not sp:
            return "Spotify API credentials not configured."

        try:
            volume_percent = max(0, min(100, int(volume_percent)))
            sp.volume(volume_percent)
            logger.log("SUCCESS", f"Spotify API: Volume set to {volume_percent}%")
            return f"Spotify volume set to {volume_percent}%."
        except Exception as e:
            return f"Could not change Spotify volume: {e}"

    def get_current_track(self) -> Optional[str]:
        """Returns the currently playing song title and artist."""
        sp = self.get_sp()
        if not sp:
            return None

        try:
            current = sp.current_playback()
            if current and current.get("item"):
                item = current["item"]
                name = item.get("name", "Unknown")
                artist = item.get("artists", [{}])[0].get("name", "Unknown Artist")
                is_playing = current.get("is_playing", False)
                state = "Playing" if is_playing else "Paused"
                return f"{name} by {artist} ({state})"
        except Exception:
            pass
        return None


# Singleton instance
spotify_controller = SpotifyClient()
