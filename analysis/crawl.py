"""BFS crawl outward from your library through Last.fm's similarity graph.

This is the "recipe co-occurrence" substitute described in the plan: rather
than trying to estimate co-occurrence from your ~6 playlists (mathematically
underdetermined — see plan Part I, Failure 2), we consume Last.fm's
population-scale similarity graph, already aggregated over its entire user
base, and crawl outward from your 96 seed artists.

Priority-ordered BFS (not plain BFS): the frontier is a priority queue keyed
by cumulative similarity-weight back to a seed, so the crawl deepens around
your actual taste regions rather than drifting uniformly outward into
unrelated territory (e.g. K-pop) at the same rate as everything else.

Checkpointed every CHECKPOINT_EVERY new artists to data/universe/ so a run
can be killed and resumed without re-fetching anything already cached.
"""
import heapq
import json
import os
import sys
import time

from dotenv import load_dotenv

from enrich import collect_artists, lastfm_similar, lastfm_tags
import requests

UNIVERSE_DIR = "data/universe"
UNIVERSE_PATH = os.path.join(UNIVERSE_DIR, "universe.json")
FRONTIER_PATH = os.path.join(UNIVERSE_DIR, "frontier.json")

MAX_ARTISTS = 15_000
CHECKPOINT_EVERY = 250
REQUEST_DELAY = 0.15  # ~3 req/s measured throughput, 2 calls/artist


def load_state():
    if os.path.exists(UNIVERSE_PATH):
        with open(UNIVERSE_PATH) as f:
            universe = json.load(f)
    else:
        universe = {}
    if os.path.exists(FRONTIER_PATH):
        with open(FRONTIER_PATH) as f:
            frontier_list = json.load(f)
    else:
        frontier_list = None
    return universe, frontier_list


def save_state(universe, frontier_heap):
    os.makedirs(UNIVERSE_DIR, exist_ok=True)
    with open(UNIVERSE_PATH, "w") as f:
        json.dump(universe, f)
    with open(FRONTIER_PATH, "w") as f:
        json.dump(frontier_heap, f)


def seed_frontier():
    """Your 96 library artists, each a depth-0 seed with max priority."""
    artists = collect_artists()
    heap = []
    for entry in artists.values():
        name = entry["name"]
        # heapq is a min-heap; negate priority so highest-similarity expands first
        heapq.heappush(heap, (-1.0, name, 0, name))  # (neg_priority, name, depth, discovered_via)
    return heap


def main():
    load_dotenv()
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        raise SystemExit("Missing LASTFM_API_KEY in .env")

    universe, saved_frontier = load_state()
    if saved_frontier is not None:
        frontier = [tuple(x) for x in saved_frontier]
        heapq.heapify(frontier)
        print(f"Resuming: {len(universe)} artists already crawled, "
              f"{len(frontier)} in frontier.")
    else:
        frontier = seed_frontier()
        print(f"Starting fresh crawl from {len(frontier)} seed artists.")

    since_checkpoint = 0
    consecutive_errors = 0
    total_errors = 0

    while frontier and len(universe) < MAX_ARTISTS:
        neg_priority, name, depth, via = heapq.heappop(frontier)
        if name in universe:
            continue

        try:
            similar = lastfm_similar(name, api_key, limit=30)
            time.sleep(REQUEST_DELAY)
            tags = lastfm_tags(name, api_key)
            time.sleep(REQUEST_DELAY)
        except requests.RequestException as e:
            print(f"  [error] {name}: {e}", file=sys.stderr)
            consecutive_errors += 1
            total_errors += 1
            if consecutive_errors > 50:
                print("Too many consecutive errors — stopping to avoid hammering the API.")
                break
            continue

        consecutive_errors = 0
        universe[name] = {
            "name": name,
            "depth": depth,
            "discovered_via": via,
            "similar": similar,
            "tags": tags,
        }

        for sim in similar:
            other = sim["name"]
            if other in universe:
                continue
            priority = -neg_priority * sim["match"] if depth > 0 else sim["match"]
            heapq.heappush(frontier, (-priority, other, depth + 1, name))

        since_checkpoint += 1
        if since_checkpoint >= CHECKPOINT_EVERY:
            save_state(universe, frontier)
            since_checkpoint = 0
            print(f"  checkpoint: {len(universe)}/{MAX_ARTISTS} artists crawled "
                  f"({len(frontier)} in frontier)")

    save_state(universe, frontier)
    print(f"\nCrawl complete (or capped): {len(universe)} artists.")
    print(f"Errors encountered: {total_errors}")

    depths = {}
    for v in universe.values():
        depths[v["depth"]] = depths.get(v["depth"], 0) + 1
    print(f"By depth: {dict(sorted(depths.items()))}")


if __name__ == "__main__":
    main()
