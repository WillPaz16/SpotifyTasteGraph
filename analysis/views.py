"""Build the two supplementary views: genre structure (sunburst) and discovery map.

taste_map.html (the main network view) is built directly by taste_graph.py's
export_pyvis — this module builds the other two outputs described in the plan:
  - output/genre_tree.html   Wikidata meta-genre hierarchy, weighted by play time
  - output/discovery.html    bridge artists, curated discovery paths, and the
                             adjacent-unheard frontier (a real recommendation
                             surface derived from graph structure)
"""
import json
import os
from collections import defaultdict

import plotly.graph_objects as go

from parse import load_tracks, classify
from taste_graph import (
    load_artist_cache, load_influence_edges, load_taxonomy,
    build_graph, prune, compute_metrics, artist_node,
)

OUTPUT_DIR = "output"
MUSIC_GRAPH_PATH = "../exploration/music-knowledge-graph/music_graph.json"

# will_response values treated as "you love this" for weighting the discovery frontier
LOVED_RESPONSES = {"seed_artist", "highlight", "loved", "anchor", "currently_listening"}


def build_genre_tree(artist_cache, taxonomy):
    """meta_genre -> genre -> weighted play time, split evenly across an
    artist's genre memberships so multi-genre artists don't inflate totals."""
    tracks, _ = load_tracks()
    artist_seconds = defaultdict(int)
    for t in tracks:
        for name in t["artist_names"]:
            artist_seconds[name] += t["played_seconds"]

    genre_value = defaultdict(float)
    meta_of_genre = {}
    for name, seconds in artist_seconds.items():
        entry = artist_cache.get(name)
        if not entry:
            continue
        genres = entry.get("genres", [])
        genres_in_taxonomy = [g for g in genres if g in taxonomy]
        if not genres_in_taxonomy:
            continue
        share = seconds / len(genres_in_taxonomy)
        for g in genres_in_taxonomy:
            genre_value[g] += share
            meta_of_genre[g] = taxonomy[g]["meta_genre"]

    meta_value = defaultdict(float)
    for g, v in genre_value.items():
        meta_value[meta_of_genre[g]] += v

    ids, labels, parents, values = ["Taste"], ["Taste"], [""], [sum(meta_value.values()) or 1]
    for meta, v in sorted(meta_value.items(), key=lambda kv: -kv[1]):
        ids.append(f"meta::{meta}")
        labels.append(meta)
        parents.append("Taste")
        values.append(v)
    for g, v in sorted(genre_value.items(), key=lambda kv: -kv[1]):
        ids.append(f"genre::{g}")
        labels.append(g)
        parents.append(f"meta::{meta_of_genre[g]}")
        values.append(v)

    return ids, labels, parents, values


def export_genre_tree(artist_cache, taxonomy, path):
    if not taxonomy:
        print("No genre_taxonomy.json found — run genre_taxonomy.py first. Skipping genre tree.")
        return
    ids, labels, parents, values = build_genre_tree(artist_cache, taxonomy)
    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>played: %{value:.0f}s<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=30, l=0, r=0, b=0),
        paper_bgcolor="#111318", font_color="#eee",
        title="Meta-Genre Structure (weighted by play time)",
    )
    fig.write_html(path)
    print(f"Wrote {path}")


def compute_bridge_artists(G, betweenness, top_n=15):
    return sorted(
        ((G.nodes[n]["label"], betweenness[n]) for n in G.nodes if G.nodes[n].get("kind") == "artist"),
        key=lambda x: -x[1],
    )[:top_n]


def load_discovery_paths():
    if not os.path.exists(MUSIC_GRAPH_PATH):
        return []
    with open(MUSIC_GRAPH_PATH) as f:
        graph = json.load(f)
    id_to_name = {a["id"]: a["name"] for a in graph["nodes"]["artists"]}
    for g in graph["nodes"]["genres"]:
        id_to_name[g["id"]] = g["name"]
    for c in graph["nodes"]["concepts"]:
        id_to_name[c["id"]] = c["name"]
    paths = []
    for e in graph["edges"]:
        if e["type"] == "discovery_path":
            paths.append({
                "from": id_to_name.get(e["from"], e["from"]),
                "to": id_to_name.get(e["to"], e["to"]),
                "note": e.get("note", ""),
            })
    return paths


def compute_discovery_frontier(artist_cache, library_names, top_n=20):
    """Last.fm similar-artist edges from artists you love, pointing OUTSIDE
    your library, summed by weight — a genuine graph-derived recommendation
    surface rather than a generic 'you might like' list."""
    loved_names = set()
    if os.path.exists(MUSIC_GRAPH_PATH):
        with open(MUSIC_GRAPH_PATH) as f:
            graph = json.load(f)
        for a in graph["nodes"]["artists"]:
            if a.get("will_response") in LOVED_RESPONSES:
                loved_names.add(a["name"])

    scores = defaultdict(float)
    sourced_from = defaultdict(set)
    for name in library_names:
        weight_bonus = 1.5 if name in loved_names else 1.0
        entry = artist_cache.get(name)
        if not entry:
            continue
        for sim in entry.get("similar", []):
            other = sim["name"]
            if other in library_names:
                continue
            scores[other] += sim["match"] * weight_bonus
            sourced_from[other].add(name)

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:top_n]
    return [
        {"name": name, "score": score, "via": sorted(sourced_from[name])[:4]}
        for name, score in ranked
    ]


def render_discovery_html(bridges, discovery_paths, frontier, path):
    def esc(s):
        return str(s).replace("<", "&lt;").replace(">", "&gt;")

    bridge_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{score:.4f}</td></tr>" for name, score in bridges
    )
    path_rows = "".join(
        f"<li><b>{esc(p['from'])}</b> &rarr; <b>{esc(p['to'])}</b><br>"
        f"<span class='note'>{esc(p['note'])}</span></li>"
        for p in discovery_paths
    )
    frontier_rows = "".join(
        f"<tr><td>{esc(f['name'])}</td><td>{f['score']:.2f}</td>"
        f"<td>{esc(', '.join(f['via']))}</td></tr>"
        for f in frontier
    )

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Discovery Map</title>
<style>
  body {{ background:#111318; color:#eee; font-family: -apple-system, sans-serif; padding: 2rem; max-width: 900px; margin: 0 auto; }}
  h1, h2 {{ color: #fff; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
  td, th {{ padding: 6px 12px; border-bottom: 1px solid #333; text-align: left; }}
  th {{ color: #aaa; font-weight: 600; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 10px 0; border-bottom: 1px solid #222; }}
  .note {{ color: #999; font-size: 0.9em; }}
  section {{ margin-bottom: 3rem; }}
</style></head>
<body>
<h1>Discovery Map</h1>

<section>
<h2>Bridge Artists</h2>
<p class="note">High betweenness centrality — these artists sit between clusters in your actual listening graph.</p>
<table><tr><th>Artist</th><th>Betweenness</th></tr>{bridge_rows}</table>
</section>

<section>
<h2>Discovery Paths</h2>
<p class="note">The actual routes you took, from your hand-curated knowledge graph.</p>
<ul>{path_rows}</ul>
</section>

<section>
<h2>Discovery Frontier</h2>
<p class="note">Artists similar to ones you love, not yet in your library — ranked by summed Last.fm similarity. A recommendation surface derived from graph structure, not a generic suggestion list.</p>
<table><tr><th>Artist</th><th>Score</th><th>Similar to (in your library)</th></tr>{frontier_rows}</table>
</section>

</body></html>"""

    with open(path, "w") as f:
        f.write(html)
    print(f"Wrote {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    artist_cache = load_artist_cache()
    influence_edges = load_influence_edges()
    taxonomy = load_taxonomy()

    tracks, _ = load_tracks()
    G = build_graph(tracks, artist_cache, influence_edges, taxonomy)
    G, _, _ = prune(G)
    _, betweenness, _, _ = compute_metrics(G)

    library_names = {G.nodes[n]["label"] for n in G.nodes if G.nodes[n].get("kind") == "artist"}

    export_genre_tree(artist_cache, taxonomy, os.path.join(OUTPUT_DIR, "genre_tree.html"))

    bridges = compute_bridge_artists(G, betweenness)
    discovery_paths = load_discovery_paths()
    frontier = compute_discovery_frontier(artist_cache, library_names)
    render_discovery_html(bridges, discovery_paths, frontier, os.path.join(OUTPUT_DIR, "discovery.html"))


if __name__ == "__main__":
    main()
