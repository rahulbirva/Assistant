"""
Diagnostic & Verification Tool for JARVIS Spotify API Integration
Run: python test_spotify.py
"""

import sys
import config
from core.spotify_client import spotify_controller

def test_spotify():
    print("=" * 65)
    print("  JARVIS SPOTIFY API INTEGRATION DIAGNOSTIC")
    print("=" * 65)
    print()

    # 1. Check Configuration
    cid = config.SPOTIFY_CLIENT_ID
    secret = config.SPOTIFY_CLIENT_SECRET
    redirect = config.SPOTIFY_REDIRECT_URI

    print(f"Client ID      : {'[CONFIGURED: ' + cid[:6] + '...' + cid[-4:] + ']' if cid else '[MISSING - NOT SET]'}")
    print(f"Client Secret  : {'[CONFIGURED: **********]' if secret else '[MISSING - NOT SET]'}")
    print(f"Redirect URI   : {redirect}")
    print()

    if not spotify_controller.is_configured():
        print("[-] Spotify API is NOT configured yet.")
        print()
        print("To enable full background Spotify control:")
        print("  1. Go to: https://developer.spotify.com/dashboard")
        print("  2. Log in with your Spotify account and click 'Create app'")
        print("  3. Set 'Redirect URI' to: http://localhost:8888/callback")
        print("  4. Copy your Client ID and Client Secret into 'config.py' (or a '.env' file):")
        print("       SPOTIFY_CLIENT_ID = 'your_client_id_here'")
        print("       SPOTIFY_CLIENT_SECRET = 'your_client_secret_here'")
        print()
        print("[+] Until configured, JARVIS will continue using fallback desktop media control.")
        print("=" * 65)
        return

    print("[+] Credentials detected! Connecting to Spotify Web API...")
    sp = spotify_controller.get_sp()

    if not sp:
        print("[-] Failed to create Spotify client session.")
        return

    try:
        user = sp.current_user()
        name = user.get("display_name", "User")
        country = user.get("country", "")
        product = user.get("product", "free/premium")
        print(f"[SUCCESS] Authenticated as Spotify User: {name} ({product}, {country})")

        devices = sp.devices().get("devices", [])
        print(f"\nDetected Devices ({len(devices)}):")
        if devices:
            for d in devices:
                active_flag = " [ACTIVE]" if d.get("is_active") else ""
                print(f"  * {d.get('name')} ({d.get('type')}) - Volume: {d.get('volume_percent')}%{active_flag}")
        else:
            print("  * No active devices currently detected. Launch your Spotify app to link.")

        current = spotify_controller.get_current_track()
        if current:
            print(f"\nCurrently Playing:\n  * {current}")
        else:
            print("\nNo track is currently playing.")

        print()
        print("=" * 65)
        print("  SPOTIFY API IS FULLY READY & CONNECTED TO JARVIS!")
        print("=" * 65)

    except Exception as e:
        print(f"[-] Spotify connection error: {e}")

if __name__ == "__main__":
    test_spotify()
