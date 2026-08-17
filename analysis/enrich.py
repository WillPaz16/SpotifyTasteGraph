"""Build the artist enrichment cache: Wikidata genres + Last.fm similarity/tags.

Keyed by Spotify artist URI (the join key across listening data, enrichment,
and the hand-curated vault). Cached to data/artists.json so re-runs are free
unless --force is passed; only unresolved/missing artists are (re)fetched.
"""
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

from parse import load_tracks

CACHE_PATH = "data/artists.json"
MUSIC_GRAPH_PATH = "../exploration/music-knowledge-graph/music_graph.json"

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"
USER_AGENT = "PersonalTasteGraph/0.1 (local script, non-commercial)"

REQUEST_DELAY = 0.25  # seconds, be polite to free/shared endpoints
WIKIDATA_DELAY = 1.0  # Wikidata's anonymous rate limit is much stricter — 429s at 0.25s
MAX_RETRIES = 4


def _get_with_retry(url, **kwargs):
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, **kwargs)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        time.sleep(delay)
        delay *= 2
    resp.raise_for_status()
    return resp


def collect_artists():
    """Union of every artist from listening data + the hand-curated graph,
    keyed by Spotify URI. Falls back to a synthetic key for the rare artist
    with no resolvable URI so it isn't silently dropped."""
    artists = {}

    tracks, _ = load_tracks()
    for t in tracks:
        for name, uri in zip(t["artist_names"], t["artist_uris"] or [None] * len(t["artist_names"])):
            key = uri or f"name::{name}"
            artists.setdefault(key, {"name": name, "spotify_uri": uri, "in_library": True, "curated_id": None})

    if os.path.exists(MUSIC_GRAPH_PATH):
        with open(MUSIC_GRAPH_PATH) as f:
            graph = json.load(f)
        for a in graph["nodes"]["artists"]:
            uri = a.get("spotify_uri")
            key = uri or f"name::{a['name']}"
            entry = artists.setdefault(key, {"name": a["name"], "spotify_uri": uri, "in_library": True, "curated_id": None})
            entry["curated_id"] = a["id"]
            entry["in_library"] = True

    return artists


def wikidata_lookup(name):
    """name -> (qid, genres[]) via wbsearchentities + a P136 SPARQL query."""
    resp = _get_with_retry(WIKIDATA_SEARCH_URL, params={
        "action": "wbsearchentities", "search": name, "language": "en",
        "format": "json", "limit": 1, "type": "item",
    }, headers={"User-Agent": USER_AGENT}, timeout=10)
    results = resp.json().get("search", [])
    if not results:
        return None, []
    qid = results[0]["id"]

    time.sleep(WIKIDATA_DELAY)

    query = (
        f"SELECT ?gLabel WHERE {{ wd:{qid} wdt:P136 ?g . "
        f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}'
    )
    resp = _get_with_retry(WIKIDATA_SPARQL_URL, params={"query": query},
                            headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
                            timeout=15)
    rows = resp.json()["results"]["bindings"]
    genres = [r["gLabel"]["value"] for r in rows]
    return qid, genres


def lastfm_similar(name, api_key, limit=20):
    resp = _get_with_retry(LASTFM_URL, params={
        "method": "artist.getsimilar", "artist": name, "api_key": api_key,
        "format": "json", "limit": limit,
    }, timeout=10)
    data = resp.json()
    if "error" in data:
        return []
    artists = data.get("similarartists", {}).get("artist", [])
    return [{"name": a["name"], "match": float(a["match"])} for a in artists]


def lastfm_tags(name, api_key, limit=10):
    resp = _get_with_retry(LASTFM_URL, params={
        "method": "artist.gettoptags", "artist": name, "api_key": api_key, "format": "json",
    }, timeout=10)
    data = resp.json()
    if "error" in data:
        return []
    tags = data.get("toptags", {}).get("tag", [])[:limit]
    return [t["name"].lower() for t in tags if int(t.get("count", 0)) > 0]


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=1, sort_keys=True)


def main():
    load_dotenv()
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        raise SystemExit("Missing LASTFM_API_KEY in .env")

    force = "--force" in sys.argv

    artists = collect_artists()
    cache = load_cache()

    resolved_wikidata = 0
    resolved_lastfm = 0
    unresolved = []

    total = len(artists)
    for i, (uri, meta) in enumerate(sorted(artists.items(), key=lambda kv: kv[1]["name"]), 1):
        name = meta["name"]
        entry = cache.get(uri, {})
        # Retry if never attempted OR the previous attempt came back empty
        # (a null qid / empty similar list usually means a rate-limit failure,
        # not a genuine "no data exists" — genuine misses just get retried
        # again harmlessly on the next run).
        needs_wikidata = force or not entry.get("wikidata_qid")
        needs_lastfm = force or not entry.get("similar")

        if needs_wikidata:
            try:
                qid, genres = wikidata_lookup(name)
                time.sleep(WIKIDATA_DELAY)
            except requests.RequestException as e:
                qid, genres = None, []
                print(f"  [wikidata error] {name}: {e}", file=sys.stderr)
            entry["wikidata_qid"] = qid
            entry["genres"] = genres
            if qid:
                resolved_wikidata += 1

        if needs_lastfm:
            try:
                similar = lastfm_similar(name, api_key)
                time.sleep(REQUEST_DELAY)
                tags = lastfm_tags(name, api_key)
                time.sleep(REQUEST_DELAY)
            except requests.RequestException as e:
                similar, tags = [], []
                print(f"  [lastfm error] {name}: {e}", file=sys.stderr)
            entry["similar"] = similar
            entry["lastfm_tags"] = tags
            if similar or tags:
                resolved_lastfm += 1

        entry["name"] = name
        entry["spotify_uri"] = meta["spotify_uri"]
        entry["in_library"] = meta["in_library"]
        entry["curated_id"] = meta["curated_id"]
        cache[uri] = entry

        if not entry.get("wikidata_qid") and not entry.get("similar"):
            unresolved.append(name)

        if i % 10 == 0 or i == total:
            print(f"  {i}/{total} processed...")

    save_cache(cache)

    print(f"\nArtists processed: {total}")
    print(f"Resolved on Wikidata: {resolved_wikidata}")
    print(f"Resolved on Last.fm: {resolved_lastfm}")
    if unresolved:
        print(f"Unresolved on both sources ({len(unresolved)}): {', '.join(unresolved)}")
    print(f"\nWrote {CACHE_PATH}")


if __name__ == "__main__":
    main()
