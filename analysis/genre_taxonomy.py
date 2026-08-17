"""Build a meta-genre taxonomy by walking Wikidata's genre subclass hierarchy (P279).

Replaces the hand-written MACRO_GENRE_MAP in parse.py with a data-derived tree:
every genre observed in the artist enrichment cache gets walked upward through
"subclass of" until it reaches a root (a genre with no further P279 parent, or
one of a small set of recognized top-level buckets). Roots become meta-genres;
the walked path becomes that genre's lineage.
"""
import json
import os
import time

import requests

from enrich import (
    CACHE_PATH, WIKIDATA_SEARCH_URL, WIKIDATA_SPARQL_URL, USER_AGENT,
    WIKIDATA_DELAY, _get_with_retry,
)

OUTPUT_PATH = "data/genre_taxonomy.json"

# "music genre" — used to filter out label-collision homonyms (e.g. a chemistry
# or physics entity that happens to share the string "funk" or "soul").
MUSIC_GENRE_QID = "Q188451"

# A handful of extremely broad Wikidata nodes that are technically reachable
# but useless as "meta-genres" (e.g. "music genre" itself, "art"). Walking
# stops here even if a P279 chain continues further.
STOP_NODES = {
    "music genre", "music", "art", "genre", "popular music", "entertainment",
}
MAX_DEPTH = 6


def _resolve_genre_qid(genre_label):
    """Find the QID for a genre label that is ACTUALLY a music genre — plain
    rdfs:label matching is ambiguous (e.g. "funk" also matches an unrelated
    chemistry/physics Wikidata item), so candidates are filtered by
    P31/P279* -> music genre before being accepted."""
    resp = _get_with_retry(WIKIDATA_SEARCH_URL, params={
        "action": "wbsearchentities", "search": genre_label, "language": "en",
        "format": "json", "limit": 5, "type": "item",
    }, headers={"User-Agent": USER_AGENT}, timeout=10)
    candidates = [r["id"] for r in resp.json().get("search", [])]
    time.sleep(WIKIDATA_DELAY)

    for qid in candidates:
        ask = f"ASK {{ wd:{qid} wdt:P31/wdt:P279* wd:{MUSIC_GENRE_QID} }}"
        resp = _get_with_retry(WIKIDATA_SPARQL_URL, params={"query": ask},
                                headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
                                timeout=15)
        time.sleep(WIKIDATA_DELAY)
        if resp.json().get("boolean"):
            return qid
    return None


def get_parents(genre_label, cache):
    """genre label -> list of P279 parent labels, using a persistent on-disk cache
    keyed by genre label (separate from the per-artist cache, since many artists
    share the same genre labels)."""
    if genre_label in cache:
        return cache[genre_label]

    try:
        qid = _resolve_genre_qid(genre_label)
        if qid is None:
            parents = []
        else:
            query = (
                f"SELECT ?parentLabel WHERE {{ wd:{qid} wdt:P279 ?parent . "
                f'SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }} LIMIT 10'
            )
            resp = _get_with_retry(WIKIDATA_SPARQL_URL, params={"query": query},
                                    headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
                                    timeout=15)
            rows = resp.json()["results"]["bindings"]
            parents = [r["parentLabel"]["value"] for r in rows]
    except requests.RequestException:
        parents = []

    cache[genre_label] = parents
    time.sleep(WIKIDATA_DELAY)
    return parents


def walk_to_root(genre_label, parent_cache, depth=0, path=None):
    path = path or [genre_label]
    if depth >= MAX_DEPTH:
        return path
    parents = get_parents(genre_label, parent_cache)
    parents = [p for p in parents if p not in STOP_NODES and p not in path]
    if not parents:
        return path
    # Follow the first parent — Wikidata genres are often multi-parented
    # (e.g. dance-pop -> pop music AND club/dance music); picking one keeps
    # the tree readable. The alternate parent is still recorded as a cross-link.
    return walk_to_root(parents[0], parent_cache, depth + 1, path + [parents[0]])


def collect_observed_genres():
    if not os.path.exists(CACHE_PATH):
        raise SystemExit(f"{CACHE_PATH} not found — run enrich.py first.")
    with open(CACHE_PATH) as f:
        artists = json.load(f)
    genres = set()
    for entry in artists.values():
        genres.update(entry.get("genres", []))
    return sorted(genres)


def main():
    genres = collect_observed_genres()
    print(f"Observed genres to place in taxonomy: {len(genres)}")

    parent_cache_path = "data/genre_parents_cache.json"
    parent_cache = {}
    if os.path.exists(parent_cache_path):
        with open(parent_cache_path) as f:
            parent_cache = json.load(f)

    taxonomy = {}
    for i, g in enumerate(genres, 1):
        path = walk_to_root(g, parent_cache)
        taxonomy[g] = {
            "path": path,
            "meta_genre": path[-1],
        }
        if i % 10 == 0 or i == len(genres):
            print(f"  {i}/{len(genres)} genres placed...")

    os.makedirs("data", exist_ok=True)
    with open(parent_cache_path, "w") as f:
        json.dump(parent_cache, f, indent=1, sort_keys=True)

    meta_genres = sorted({v["meta_genre"] for v in taxonomy.values()})
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"genres": taxonomy, "meta_genres": meta_genres}, f, indent=1, sort_keys=True)

    print(f"\nMeta-genres found ({len(meta_genres)}): {', '.join(meta_genres)}")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
