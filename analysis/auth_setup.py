"""One-time OAuth flow: opens the browser, you log in and consent, saves a cached token.

Requires SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET / SPOTIPY_REDIRECT_URI in .env
(copy .env.example -> .env and fill in your Spotify developer app credentials first:
https://developer.spotify.com/dashboard).
"""
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "user-top-read user-read-recently-played user-read-currently-playing"


def main():
    load_dotenv()
    required = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise SystemExit(
            f"Missing {', '.join(missing)} in .env — copy .env.example to .env and fill in "
            "your Spotify developer app credentials first: https://developer.spotify.com/dashboard"
        )

    auth_manager = SpotifyOAuth(scope=SCOPES, cache_path=".spotify_token_cache", open_browser=True)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    me = sp.current_user()
    print(f"Authenticated as: {me['display_name']} ({me['id']})")
    print("Token cached at .spotify_token_cache — spotify_live.py will reuse it and refresh automatically.")


if __name__ == "__main__":
    main()
