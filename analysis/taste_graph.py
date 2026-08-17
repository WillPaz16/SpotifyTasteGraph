"""Build the multi-layer taste graph:

- listening   artist <-> descriptor-genre / mood, weight = played_seconds
- similarity  artist <-> artist, weight = Last.fm match (0-1), library-internal only
- influence   artist <-> artist/concept, curated (ground truth) + LLM-generated (labeled)
- collab      artist <-> artist, co-appearance on a track
- production  artist <-> artist, shared producer across tracks

Every artist on a track is credited (not just the primary), and edges are
built in full then pruned — so a low-weight edge never leaves an orphaned
node the way the old pre-add gate did.
"""
import json
import os
from collections import defaultdict
from itertools import combinations

import networkx as nx
import community as community_louvain
from pyvis.network import Network

from parse import load_tracks, classify

OUTPUT_DIR = "output"
ARTIST_CACHE_PATH = "data/artists.json"
INFLUENCE_PATH = "data/influence_edges.json"
TAXONOMY_PATH = "data/genre_taxonomy.json"

MIN_LISTENING_WEIGHT = 60   # seconds — real prune, applied after building
MIN_SIMILARITY_MATCH = 0.15  # Last.fm match score floor, to cut noise

FULL_EXPORT_GLOB = "StreamingHistory_music_*.json"


def has_full_export():
    import glob
    return bool(glob.glob(FULL_EXPORT_GLOB))


def load_artist_cache():
    if not os.path.exists(ARTIST_CACHE_PATH):
        return {}
    with open(ARTIST_CACHE_PATH) as f:
        by_uri = json.load(f)
    return {entry["name"]: entry for entry in by_uri.values()}


def load_influence_edges():
    if not os.path.exists(INFLUENCE_PATH):
        return []
    with open(INFLUENCE_PATH) as f:
        return json.load(f)


def load_taxonomy():
    if not os.path.exists(TAXONOMY_PATH):
        return {}
    with open(TAXONOMY_PATH) as f:
        return json.load(f).get("genres", {})


def artist_node(name):
    return f"artist::{name}"


def genre_node(name):
    return f"genre::{name}"


def mood_node(name):
    return f"mood::{name}"


def concept_node(name):
    return f"concept::{name}"


def build_graph(tracks, artist_cache, influence_edges, taxonomy):
    G = nx.Graph()

    artist_seconds = defaultdict(int)
    artist_track_count = defaultdict(int)
    artist_top_track = {}
    genre_seconds = defaultdict(int)
    genre_artist_count = defaultdict(set)
    mood_seconds = defaultdict(int)
    mood_artist_count = defaultdict(set)
    producer_to_artists = defaultdict(set)

    def add_weighted_edge(u, v, w, edge_type):
        if G.has_edge(u, v):
            G[u][v]["weight"] += w
        else:
            G.add_edge(u, v, weight=w, type=edge_type)

    for t in tracks:
        macros, moods = classify(t)
        seconds = t["played_seconds"]
        names = t["artist_names"]
        if not names:
            continue

        for name in names:
            node = artist_node(name)
            if not G.has_node(node):
                G.add_node(node, kind="artist", label=name)
            # Every credited artist gets full credit for the track's play time —
            # a feature isn't "half a listen," it's a full one for that artist too.
            artist_seconds[name] += seconds
            artist_track_count[name] += 1
            if name not in artist_top_track or seconds > artist_top_track[name][1]:
                artist_top_track[name] = (t["track_name"], seconds)

            if seconds >= 1:  # build first, prune by MIN_LISTENING_WEIGHT later
                for macro in macros:
                    gnode = genre_node(macro)
                    if not G.has_node(gnode):
                        G.add_node(gnode, kind="genre", label=macro)
                    add_weighted_edge(node, gnode, seconds, "listening")
                    genre_seconds[macro] += seconds
                    genre_artist_count[macro].add(name)
                for mood in moods:
                    mnode = mood_node(mood)
                    if not G.has_node(mnode):
                        G.add_node(mnode, kind="mood", label=mood)
                    add_weighted_edge(node, mnode, seconds, "listening")
                    mood_seconds[mood] += seconds
                    mood_artist_count[mood].add(name)

        # collab layer: every pair of co-credited artists on this track
        for a, b in combinations(sorted(set(names)), 2):
            add_weighted_edge(artist_node(a), artist_node(b), 1, "collab")

        # production layer: artists sharing a producer (across the whole library)
        for producer in t["producers"]:
            producer_to_artists[producer].update(names)

    for producer, names in producer_to_artists.items():
        for a, b in combinations(sorted(set(names)), 2):
            add_weighted_edge(artist_node(a), artist_node(b), 1, "production")

    # similarity layer: Last.fm similar-artist edges, library-internal only
    library_names = set(artist_seconds.keys())
    for name in library_names:
        entry = artist_cache.get(name)
        if not entry:
            continue
        for sim in entry.get("similar", []):
            other = sim["name"]
            if other not in library_names or other == name:
                continue
            if sim["match"] < MIN_SIMILARITY_MATCH:
                continue
            u, v = artist_node(name), artist_node(other)
            if G.has_edge(u, v) and G[u][v]["type"] == "similarity":
                continue  # avoid double-adding from both directions
            add_weighted_edge(u, v, sim["match"], "similarity")

    # influence layer: curated (ground truth) + LLM-generated (labeled)
    for e in influence_edges:
        u_name, v_name = e["from"], e["to"]
        u = artist_node(u_name) if artist_node(u_name) in G else concept_node(u_name)
        v = artist_node(v_name) if artist_node(v_name) in G else concept_node(v_name)
        if not G.has_node(u):
            G.add_node(u, kind="concept" if u.startswith("concept::") else "artist", label=u_name)
        if not G.has_node(v):
            G.add_node(v, kind="concept" if v.startswith("concept::") else "artist", label=v_name)
        # influence edges are meaningful even at "weight 1" — don't dedupe-sum,
        # just add (parallel influence claims between the same pair are rare
        # and each is informative on its own).
        key = (u, v) if (u, v) not in G.edges else (u, v)
        if G.has_edge(u, v) and G[u][v].get("type") == "influence":
            continue  # keep the first (curated edges are loaded before LLM ones)
        G.add_edge(u, v, weight=1, type="influence",
                   subtype=e["type"], source=e["source"], confidence=e["confidence"], note=e.get("note", ""))

    # --- attach node attributes ---
    for name, seconds in artist_seconds.items():
        node = artist_node(name)
        G.nodes[node]["total_played_seconds"] = seconds
        G.nodes[node]["track_count"] = artist_track_count[name]
        G.nodes[node]["top_track"] = artist_top_track[name][0]
        entry = artist_cache.get(name, {})
        wikidata_genres = entry.get("genres", [])
        meta_genres = sorted({taxonomy[g]["meta_genre"] for g in wikidata_genres if g in taxonomy})
        G.nodes[node]["wikidata_genres"] = wikidata_genres
        G.nodes[node]["meta_genres"] = meta_genres
        G.nodes[node]["lastfm_tags"] = entry.get("lastfm_tags", [])
        G.nodes[node]["in_library"] = True

    for macro, seconds in genre_seconds.items():
        node = genre_node(macro)
        if G.has_node(node):
            G.nodes[node]["total_played_seconds"] = seconds
            G.nodes[node]["artist_count"] = len(genre_artist_count[macro])

    for mood, seconds in mood_seconds.items():
        node = mood_node(mood)
        if G.has_node(node):
            G.nodes[node]["total_played_seconds"] = seconds
            G.nodes[node]["artist_count"] = len(mood_artist_count[mood])

    return G


def prune(G):
    """Real prune: drop low-weight listening/similarity edges, then drop any
    node left with degree 0 as a result. This is what actually fixes the
    'floating dots' problem — the old code gated edge *creation*, which still
    left the node behind with nothing attached to it."""
    to_remove = []
    for u, v, data in G.edges(data=True):
        if data["type"] == "listening" and data["weight"] < MIN_LISTENING_WEIGHT:
            to_remove.append((u, v))
    G.remove_edges_from(to_remove)

    isolated = list(nx.isolates(G))
    G.remove_nodes_from(isolated)
    return G, len(to_remove), len(isolated)


def normalize_weights(G):
    """Add a 0-1 'norm_weight' per edge, normalized WITHIN its type — mixing
    raw seconds (can be thousands) with Last.fm match (0-1) or collab counts
    (small ints) in one PageRank would let the listening layer dominate
    entirely. Metrics use norm_weight; visuals can still use raw weight/type
    for line thickness per layer."""
    by_type = defaultdict(list)
    for u, v, data in G.edges(data=True):
        by_type[data["type"]].append((u, v, data["weight"]))

    for etype, edges in by_type.items():
        max_w = max(w for _, _, w in edges) or 1
        for u, v, w in edges:
            G[u][v]["norm_weight"] = w / max_w


def compute_metrics(G):
    normalize_weights(G)
    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, weight="norm_weight")
    pagerank = nx.pagerank(G, weight="norm_weight")
    partition = community_louvain.best_partition(G, weight="norm_weight")

    for node in G.nodes:
        G.nodes[node]["degree_centrality"] = degree[node]
        G.nodes[node]["betweenness_centrality"] = betweenness[node]
        G.nodes[node]["pagerank"] = pagerank[node]
        G.nodes[node]["community"] = partition[node]

    return degree, betweenness, pagerank, partition


def export_graphml(G, path):
    H = G.copy()
    for _, data in H.nodes(data=True):
        for k, v in list(data.items()):
            if v is None:
                data[k] = ""
            elif isinstance(v, list):
                data[k] = ", ".join(str(x) for x in v)
    for _, _, data in H.edges(data=True):
        for k, v in list(data.items()):
            if v is None:
                data[k] = ""
    nx.write_graphml(H, path)


COMMUNITY_COLORS = [
    "#4C6EF5", "#F76707", "#37B24D", "#F03E3E", "#AE3EC9",
    "#1098AD", "#F59F00", "#5C7CFA", "#12B886", "#E64980",
]
EDGE_STYLE = {
    "listening": {"color": "#555b66"},
    "similarity": {"color": "#37B24D", "dashes": False},
    "collab": {"color": "#F59F00", "dashes": False},
    "production": {"color": "#1098AD", "dashes": [2, 2]},
}


def edge_style_for(data):
    if data["type"] == "influence":
        color = "#F03E3E" if data.get("source") == "curated" else "#F76707"
        dashes = data.get("source") != "curated"
        return {"color": color, "dashes": dashes}
    return EDGE_STYLE.get(data["type"], {"color": "#888"})


def export_pyvis(G, path):
    net = Network(height="900px", width="100%", bgcolor="#111318", font_color="#eee", notebook=False)
    net.barnes_hut(gravity=-4000, spring_length=140)

    max_pr = max((d.get("pagerank", 0) for _, d in G.nodes(data=True)), default=1) or 1

    for node, data in G.nodes(data=True):
        kind = data.get("kind", "artist")
        pr = data.get("pagerank", 0)
        size = 8 + (pr / max_pr) * 55
        community = data.get("community", 0)
        color = COMMUNITY_COLORS[community % len(COMMUNITY_COLORS)]
        shape = {"artist": "dot", "genre": "diamond", "mood": "triangle", "concept": "star"}.get(kind, "dot")
        title_bits = [f"<b>{data.get('label', node)}</b>", f"kind: {kind}"]
        if "total_played_seconds" in data:
            title_bits.append(f"played: {data['total_played_seconds']}s")
        if "top_track" in data:
            title_bits.append(f"top track: {data['top_track']}")
        if data.get("meta_genres"):
            title_bits.append(f"meta-genres: {', '.join(data['meta_genres'])}")
        title_bits.append(f"pagerank: {pr:.4f}")
        title_bits.append(f"betweenness: {data.get('betweenness_centrality', 0):.4f}")
        net.add_node(node, label=data.get("label", node), title="<br>".join(title_bits),
                     size=size, color=color, shape=shape)

    for u, v, data in G.edges(data=True):
        style = edge_style_for(data)
        title = f"{data['type']}"
        if data["type"] == "influence":
            title += f" ({data.get('subtype')}, {data.get('source')}, {data.get('confidence')})"
            if data.get("note"):
                title += f"<br>{data['note']}"
        net.add_edge(u, v, value=data.get("weight", 1), title=title, **style)

    net.set_options("""
    {
      "physics": {"stabilization": {"iterations": 200}},
      "interaction": {"hover": true, "tooltipDelay": 100}
    }
    """)
    net.write_html(path, open_browser=False)


def summarize(tracks, G, betweenness, pagerank, partition):
    artists = {n for n, d in G.nodes(data=True) if d.get("kind") == "artist"}
    genres = {n for n, d in G.nodes(data=True) if d.get("kind") == "genre"}
    communities = set(partition.values())

    edge_type_counts = defaultdict(int)
    for _, _, data in G.edges(data=True):
        edge_type_counts[data["type"]] += 1

    top_by_pagerank = sorted(
        ((n, pagerank[n]) for n in G.nodes if G.nodes[n].get("kind") == "artist"),
        key=lambda x: -x[1],
    )[:10]
    top_bridges = sorted(
        ((n, betweenness[n]) for n in G.nodes if G.nodes[n].get("kind") == "artist"),
        key=lambda x: -x[1],
    )[:10]

    print(f"Tracks parsed: {len(tracks)}")
    print(f"Artist nodes: {len(artists)}, Genre nodes: {len(genres)}")
    print(f"Communities found: {len(communities)}")
    print(f"Edges by layer: {dict(edge_type_counts)}")
    print("\nTop artists by PageRank (overall taste importance):")
    for n, score in top_by_pagerank:
        print(f"  {G.nodes[n]['label']:30s} {score:.4f}")
    print("\nTop bridge artists (betweenness centrality — span genres):")
    for n, score in top_bridges:
        print(f"  {G.nodes[n]['label']:30s} {score:.4f}")

    return {
        "top_by_pagerank": [(G.nodes[n]["label"], score) for n, score in top_by_pagerank],
        "top_bridges": [(G.nodes[n]["label"], score) for n, score in top_bridges],
        "num_artists": len(artists),
        "num_genres": len(genres),
        "num_communities": len(communities),
        "edge_type_counts": dict(edge_type_counts),
        "genre_totals": {
            G.nodes[n]["label"]: G.nodes[n].get("total_played_seconds", 0)
            for n in genres
        },
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if has_full_export():
        print("Full streaming history export detected but Phase 8 longitudinal "
              "analysis is not yet implemented in this script — falling back to "
              "top_tracks/recent_tracks only. See PROMPT.md Phase 8 to extend this.")

    tracks, uri_collisions = load_tracks()
    artist_cache = load_artist_cache()
    influence_edges = load_influence_edges()
    taxonomy = load_taxonomy()

    G = build_graph(tracks, artist_cache, influence_edges, taxonomy)
    G, edges_pruned, nodes_pruned = prune(G)
    print(f"Pruned {edges_pruned} sub-threshold listening edges, "
          f"{nodes_pruned} nodes left isolated as a result.")

    degree, betweenness, pagerank, partition = compute_metrics(G)

    export_graphml(G, os.path.join(OUTPUT_DIR, "taste_graph.graphml"))
    export_pyvis(G, os.path.join(OUTPUT_DIR, "taste_map.html"))

    summary = summarize(tracks, G, betweenness, pagerank, partition)

    with open(os.path.join(OUTPUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    isolated_check = list(nx.isolates(G))
    assert not isolated_check, f"Isolated nodes remain: {isolated_check}"

    print(f"\nWrote {OUTPUT_DIR}/taste_graph.graphml, {OUTPUT_DIR}/taste_map.html, {OUTPUT_DIR}/summary.json")
    print("Zero isolated nodes confirmed.")


if __name__ == "__main__":
    main()
