"""Refresh top_tracks/recent_tracks in spotify_data.json from the Spotify Web API.

IMPORTANT LIMITATION (confirmed, not hypothetical): the Spotify Web API does not
expose producer/composer/lyricist credits, curated mood/genre descriptors, OR
artist genre tags for apps without extended access — `sp.artist(...)['genres']`
comes back empty/absent entirely (same Nov 2024 restriction as audio-features and
/recommendations). There is no live substitute for the rich descriptor data in the
existing spotify_data.json.

Because of that, this script MERGES rather than overwrites: any track URI that
already has real metadata (producers/composers/descriptors) keeps that metadata
untouched — only its play timestamp is refreshed. Only genuinely new URIs (not
already in the file) get a minimal packed entry with `Descriptors: unknown`, since
that's all the live API can offer for a brand-new track. This is what stops a
refresh from quietly degrading the richer dataset the way an earlier version of
this script did.

Requires auth_setup.py to have been run once first.
"""
import json
import os

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

DATA_PATH = "../research/taste-data/spotify_data.json"
SCOPES = "user-top-read user-read-recently-played user-read-currently-playing"


def get_client():
    load_dotenv()
    auth_manager = SpotifyOAuth(scope=SCOPES, cache_path=".spotify_token_cache", open_browser=False)
    return spotipy.Spotify(auth_manager=auth_manager)


def pack_minimal_track(track):
    """Build a packed entry for a URI we have no prior rich metadata for.
    No producer/composer/descriptors available live — flagged as unknown."""
    artist_bits = [f"\"{a['name']}\"(spotify:artist:{a['id']})" for a in track["artists"]]
    return (
        f"{track['uri']}\t# Track: \"{track['name']}\" by {' and '.join(artist_bits)}. "
        f"Released on {track['album']['release_date']}. Descriptors: unknown."
    )


def fetch_top_tracks(sp, limit=50):
    resp = sp.current_user_top_tracks(limit=limit, time_range="long_term")
    return [{"uri": t["uri"], "track": t, "last_played_at": None} for t in resp["items"]]


def fetch_recent_tracks(sp, limit=50):
    resp = sp.current_user_recently_played(limit=limit)
    return [{"uri": e["track"]["uri"], "track": e["track"], "last_played_at": e["played_at"]}
            for e in resp["items"]]


def merge(fetched, old_items_by_uri):
    """Keep existing rich metadata untouched for known URIs; only refresh timestamp.
    New URIs get a minimal entry since the live API has no descriptor data to offer."""
    merged = []
    for f in fetched:
        old = old_items_by_uri.get(f["uri"])
        if old:
            new_item = dict(old)
            if f["last_played_at"]:
                new_item["last_played_at"] = f["last_played_at"]
            merged.append(new_item)
        else:
            merged.append({
                "uri": f["uri"],
                "name": pack_minimal_track(f["track"]),
                "played_seconds": 0,
                "last_played_at": f["last_played_at"],
            })
    return merged


def main():
    sp = get_client()

    with open(DATA_PATH) as f:
        data = json.load(f)

    old_top = {i["uri"]: i for i in data.get("top_tracks", {}).get("items", [])}
    old_recent = {i["uri"]: i for i in data.get("recent_tracks", {}).get("items", [])}

    new_top = merge(fetch_top_tracks(sp), old_top)
    new_recent = merge(fetch_recent_tracks(sp), old_recent)

    unknown_count = sum(1 for i in new_top + new_recent if "Descriptors: unknown" in i["name"])

    data["top_tracks"] = {"items": new_top}
    data["recent_tracks"] = {"items": new_recent}
    import datetime
    data.setdefault("meta", {})["exported_at"] = datetime.date.today().isoformat()

    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=1)

    print(f"Refreshed {len(new_top)} top tracks, {len(new_recent)} recent tracks -> {DATA_PATH}")
    if unknown_count:
        print(f"{unknown_count} entries are new tracks with no prior metadata — "
              f"descriptors set to 'unknown' (live API can't supply them).")


if __name__ == "__main__":
    main()
