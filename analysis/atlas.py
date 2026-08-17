"""Phase 3 of the FlavorGraph reformulation (see FLAVORGRAPH_PLAN.md Part III):
the Epicure-style navigable map.

Every crawled artist is a point in the UMAP-projected embedding space from
embed.py; genre/style territories emerge from the layout and are labeled by
their dominant Last.fm tag. Your listening is overlaid — library artists are
sized by play time and drawn distinct from the surrounding possibility
space. Curated + LLM influence edges (data/influence_edges.json) are drawn
as lines across the map, so hand-curated lineage is visible against the
population-scale sound-space.

Honest implementation note: the plan describes "click: nearest neighbours."
This is a static HTML file with no backend, so instead each point's hover
tooltip lists its precomputed top-8 nearest neighbours directly — same
information, reached by hover rather than click.
"""
import json
import os
from collections import Counter, defaultdict

import numpy as np
import plotly.graph_objects as go

from parse import load_tracks

UNIVERSE_PATH = "data/universe/universe.json"
EMBEDDINGS_PATH = "data/universe/embeddings.npy"
NAMES_PATH = "data/universe/embedding_names.json"
COORDS_PATH = "data/universe/atlas_coords.json"
ARTIST_CACHE_PATH = "data/artists.json"
INFLUENCE_PATH = "data/influence_edges.json"
MUSIC_GRAPH_PATH = "../exploration/music-knowledge-graph/music_graph.json"
OUTPUT_PATH = "output/taste_atlas.html"

N_NEIGHBORS = 8
N_TAG_BUCKETS = 14
CHUNK = 1000

# Tags that describe the artist but not their genre/style — nationality,
# vocalist gender, decade, or a plain non-genre catch-all. Grounded by
# measuring the top 60 most frequent tags in the crawled universe: 479
# artists (3.2%) currently get bucketed by one of these as their PRIMARY
# tag, which dilutes the map's genre territories. compute_tag_buckets()
# skips these when picking an artist's primary tag, falling back to the
# next tag in their Last.fm-ranked list (only 18 of the 479 have no other
# usable tag and become "untagged").
NON_GENRE_TAG_DENYLIST = {
    "american", "usa", "united states", "british", "uk", "canadian",
    "male vocalists", "female vocalists",
    "80s", "70s", "60s", "90s", "00s", "2000s", "2010s",
    "all", "oldies",
}

TAG_PALETTE = [
    "#4C6EF5", "#F76707", "#37B24D", "#F03E3E", "#AE3EC9",
    "#1098AD", "#F59F00", "#5C7CFA", "#12B886", "#E64980",
    "#748FFC", "#FF922B", "#82C91E", "#FA5252",
]
OTHER_COLOR = "#3a3f4a"
LIBRARY_COLOR = "#FFD43B"


def load_all():
    with open(UNIVERSE_PATH) as f:
        universe = json.load(f)
    embeddings = np.load(EMBEDDINGS_PATH)
    with open(NAMES_PATH) as f:
        names = json.load(f)
    with open(COORDS_PATH) as f:
        coords = json.load(f)
    artist_cache = {}
    if os.path.exists(ARTIST_CACHE_PATH):
        with open(ARTIST_CACHE_PATH) as f:
            artist_cache = {e["name"]: e for e in json.load(f).values()}
    influence_edges = []
    if os.path.exists(INFLUENCE_PATH):
        with open(INFLUENCE_PATH) as f:
            influence_edges = json.load(f)
    curated = {}
    if os.path.exists(MUSIC_GRAPH_PATH):
        with open(MUSIC_GRAPH_PATH) as f:
            graph = json.load(f)
        for a in graph["nodes"]["artists"]:
            curated[a["name"]] = a
    return universe, embeddings, names, coords, artist_cache, influence_edges, curated


def compute_nearest_neighbors(embeddings, names):
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9
    normed = embeddings / norms
    n = len(names)
    neighbors = {}
    for start in range(0, n, CHUNK):
        end = min(start + CHUNK, n)
        sims = normed[start:end] @ normed.T  # (chunk, n)
        for i in range(end - start):
            row = sims[i]
            top = np.argpartition(-row, N_NEIGHBORS + 1)[:N_NEIGHBORS + 1]
            top = top[np.argsort(-row[top])]
            idx = start + i
            picked = [j for j in top if j != idx][:N_NEIGHBORS]
            neighbors[names[idx]] = [names[j] for j in picked]
    return neighbors


def pick_primary_tag(tags):
    """First tag in Last.fm's ranked order that isn't a non-genre denylisted
    tag (nationality/vocalist-gender/decade/generic) — falls back to
    'untagged' only if every tag is denylisted or there are no tags at all."""
    for t in tags:
        if t.lower() not in NON_GENRE_TAG_DENYLIST:
            return t
    return "untagged"


def compute_tag_buckets(universe, names):
    primary_tag = {}
    for name in names:
        tags = universe.get(name, {}).get("tags", [])
        primary_tag[name] = pick_primary_tag(tags)

    counts = Counter(primary_tag.values())
    top_tags = [t for t, _ in counts.most_common(N_TAG_BUCKETS)]
    color_of = {t: TAG_PALETTE[i % len(TAG_PALETTE)] for i, t in enumerate(top_tags)}

    bucket = {}
    color = {}
    for name, tag in primary_tag.items():
        b = tag if tag in color_of else "other"
        bucket[name] = b
        color[name] = color_of.get(tag, OTHER_COLOR)
    return bucket, color, top_tags


def compute_library_play_seconds():
    tracks, _ = load_tracks()
    seconds = defaultdict(int)
    for t in tracks:
        for name in t["artist_names"]:
            seconds[name] += t["played_seconds"]
    return seconds


def esc(s):
    return str(s).replace("<", "&lt;").replace(">", "&gt;")


def build_figure(universe, names, coords, bucket, color, top_tags, neighbors,
                  library_seconds, curated, influence_edges):
    fig = go.Figure()

    library_names = set(library_seconds.keys()) & set(names)
    background_names = [n for n in names if n not in library_names]

    # --- background: the full crawled universe, colored by dominant tag ---
    for tag in top_tags + ["other"]:
        group = [n for n in background_names if bucket.get(n) == tag]
        if not group:
            continue
        xs = [coords[n]["x"] for n in group]
        ys = [coords[n]["y"] for n in group]
        hover = [
            f"<b>{esc(n)}</b><br>tag: {esc(universe.get(n, {}).get('tags', ['?'])[0] if universe.get(n, {}).get('tags') else '?')}"
            f"<br>discovered via: {esc(universe.get(n, {}).get('discovered_via', '?'))} (depth {universe.get(n, {}).get('depth', '?')})"
            f"<br>nearest: {esc(', '.join(neighbors.get(n, [])[:5]))}"
            for n in group
        ]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name=tag,
            marker=dict(size=5, color=color[group[0]], opacity=0.55, line=dict(width=0)),
            text=hover, hoverinfo="text",
        ))

    # --- influence edges drawn as lines across the map ---
    curated_x, curated_y, llm_x, llm_y = [], [], [], []
    for e in influence_edges:
        a, b = e["from"], e["to"]
        if a not in coords or b not in coords:
            continue
        xs = [coords[a]["x"], coords[b]["x"], None]
        ys = [coords[a]["y"], coords[b]["y"], None]
        if e.get("source") == "curated":
            curated_x += xs
            curated_y += ys
        else:
            llm_x += xs
            llm_y += ys
    if llm_x:
        fig.add_trace(go.Scatter(
            x=llm_x, y=llm_y, mode="lines", name="LLM influence",
            line=dict(color="#F76707", width=1, dash="dot"), opacity=0.5, hoverinfo="skip",
        ))
    if curated_x:
        fig.add_trace(go.Scatter(
            x=curated_x, y=curated_y, mode="lines", name="Curated influence",
            line=dict(color="#F03E3E", width=1.5), opacity=0.7, hoverinfo="skip",
        ))

    # --- your library, overlaid and sized by play time ---
    if library_names:
        lib_list = sorted(library_names)
        max_sec = max(library_seconds[n] for n in lib_list) or 1
        xs = [coords[n]["x"] for n in lib_list]
        ys = [coords[n]["y"] for n in lib_list]
        sizes = [8 + (library_seconds[n] / max_sec) * 32 for n in lib_list]
        hover = []
        for n in lib_list:
            c = curated.get(n)
            bits = [f"<b>{esc(n)}</b> (in your library)",
                    f"played: {library_seconds[n]}s",
                    f"tags: {esc(', '.join(universe.get(n, {}).get('tags', [])[:5]))}",
                    f"nearest: {esc(', '.join(neighbors.get(n, [])[:5]))}"]
            if c:
                bits.append(f"your response: {esc(c.get('will_response', ''))}")
            hover.append("<br>".join(bits))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name="Your library",
            marker=dict(size=sizes, color=LIBRARY_COLOR, opacity=0.95,
                        line=dict(width=1, color="#111318")),
            text=hover, hoverinfo="text",
        ))

    fig.update_layout(
        title="Taste Atlas — %d-artist Last.fm similarity universe, your listening overlaid" % len(names),
        paper_bgcolor="#111318", plot_bgcolor="#111318", font_color="#eee",
        legend=dict(bgcolor="#181b21", font=dict(size=10)),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
        margin=dict(t=60, l=10, r=10, b=10),
        height=900,
    )
    return fig


def main():
    print("Loading atlas inputs...")
    universe, embeddings, names, coords, artist_cache, influence_edges, curated = load_all()
    print(f"{len(names)} artists with embeddings/coordinates.")

    print("Computing nearest neighbors (chunked cosine sim)...")
    neighbors = compute_nearest_neighbors(embeddings, names)

    print("Bucketing by dominant tag...")
    bucket, color, top_tags = compute_tag_buckets(universe, names)
    print(f"Top tags: {top_tags}")

    print("Computing library play-time overlay...")
    library_seconds = compute_library_play_seconds()
    print(f"{len(set(library_seconds) & set(names))} library artists present in the universe.")

    print("Building figure...")
    fig = build_figure(universe, names, coords, bucket, color, top_tags, neighbors,
                        library_seconds, curated, influence_edges)

    os.makedirs("output", exist_ok=True)
    fig.write_html(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
