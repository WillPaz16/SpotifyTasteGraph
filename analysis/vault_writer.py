"""Write taste-analysis notes into the Obsidian vault (does not touch hand-curated notes)."""
import glob
import json
import os
import re

from parse import load_tracks
from taste_graph import load_artist_cache, load_influence_edges, load_taxonomy, build_graph, prune
from views import build_genre_tree, compute_discovery_frontier

VAULT_DIR = "../exploration/obsidian-vault"
TASTE_DIR = os.path.join(VAULT_DIR, "Taste Analysis")
ARTISTS_DIR = os.path.join(VAULT_DIR, "Artists")
SUMMARY_PATH = "output/summary.json"
INFLUENCE_PATH = "data/influence_edges.json"

# Soft mapping from computed macro-genres to existing hand-curated Genre notes,
# only where there's a real conceptual overlap — most macro-genres (pop, hip_hop_rap,
# alternative_rock, etc.) have no equivalent in the hand-curated exploration graph yet,
# and are intentionally left as plain text rather than a fabricated link.
GENRE_LINK_MAP = {
    "r_and_b_soul": "Neo-Soul",
}


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', "", name)


def fmt_seconds(s):
    hours = s / 3600
    if hours >= 1:
        return f"{hours:.1f} hrs"
    return f"{s / 60:.0f} min"


def write_genre_breakdown(summary):
    lines = ["---", "type: analysis", "tags: [taste-analysis]", "---", "", "# Genre Breakdown", "",
              "Computed from `analysis/taste_graph.py` against `spotify_data.json` "
              "(top_tracks + recent_tracks). Not the same taxonomy as the hand-curated "
              "`Genres/` notes — those track discovery lineage, this tracks actual play time.", ""]
    totals = sorted(summary["genre_totals"].items(), key=lambda x: -x[1])
    total_all = sum(v for _, v in totals) or 1
    lines.append("| Genre | Played | Share |")
    lines.append("|---|---|---|")
    for genre, seconds in totals:
        share = seconds / total_all * 100
        label = genre
        if genre in GENRE_LINK_MAP:
            label = f"{genre} → [[{GENRE_LINK_MAP[genre]}]]"
        lines.append(f"| {label} | {fmt_seconds(seconds)} | {share:.1f}% |")
    return "\n".join(lines) + "\n"


def write_bridge_artists(summary):
    lines = ["---", "type: analysis", "tags: [taste-analysis]", "---", "", "# Bridge Artists", "",
              "Artists with high betweenness centrality in the taste graph — they sit between "
              "genre clusters in your actual listening. Candidates for new `bridges_to`/"
              "`discovery_path` edges in the hand-curated knowledge graph if you want to "
              "formally connect them.", ""]
    for name, score in summary["top_bridges"]:
        lines.append(f"- **{name}** — betweenness {score:.4f}")
    return "\n".join(lines) + "\n"


def write_snapshot(summary, date_str):
    lines = ["---", "type: analysis", "tags: [taste-analysis, snapshot]", f'date: {date_str}', "---", "",
              f"# Taste Snapshot — {date_str}", "",
              f"- Artist nodes: {summary['num_artists']}",
              f"- Genre nodes: {summary['num_genres']}",
              f"- Communities detected: {summary['num_communities']}", "",
              "## Top artists by PageRank (overall taste importance)", ""]
    for name, score in summary["top_by_pagerank"]:
        lines.append(f"- {name} ({score:.4f})")
    lines.append("")
    lines.append("## Top bridge artists (span genres)")
    lines.append("")
    for name, score in summary["top_bridges"]:
        lines.append(f"- {name} ({score:.4f})")
    lines.append("")
    lines.append("See [[Genre Breakdown]] and [[Bridge Artists]] for the full current picture; "
                  "this note is a point-in-time snapshot and won't be overwritten by later runs.")
    return "\n".join(lines) + "\n"


def write_meta_genre_map(artist_cache, taxonomy):
    if not taxonomy:
        return None
    ids, labels, parents, values = build_genre_tree(artist_cache, taxonomy)
    # ids[0] is the "Taste" root; walk meta -> genre pairs from the parents array
    meta_children = {}
    value_by_id = dict(zip(ids, values))
    for i, pid in enumerate(ids):
        if pid == "" or pid == "Taste":
            continue
        parent = parents[i]
        if parent == "Taste":
            meta_children.setdefault(ids[i], [])
        else:
            meta_children.setdefault(parent, []).append(ids[i])

    lines = ["---", "type: analysis", "tags: [taste-analysis]", "---", "", "# Meta-Genre Map", "",
              "Built from Wikidata's genre subclass hierarchy (`analysis/genre_taxonomy.py`), "
              "weighted by your actual play time — a data-derived structure, not a hand-written guess.", ""]
    metas = sorted(
        (mid for mid in ids if mid.startswith("meta::")),
        key=lambda mid: -value_by_id.get(mid, 0),
    )
    for meta_id in metas:
        meta_label = meta_id.replace("meta::", "")
        lines.append(f"## {meta_label} — {fmt_seconds(value_by_id[meta_id])}")
        children = sorted(meta_children.get(meta_id, []), key=lambda gid: -value_by_id.get(gid, 0))
        for gid in children:
            genre_label = gid.replace("genre::", "")
            link = GENRE_LINK_MAP.get(genre_label)
            display = f"{genre_label} → [[{link}]]" if link else genre_label
            lines.append(f"- {display} — {fmt_seconds(value_by_id[gid])}")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_discovery_frontier(frontier):
    lines = ["---", "type: analysis", "tags: [taste-analysis, discovery]", "---", "", "# Discovery Frontier", "",
              "Artists similar to ones you love, not yet in your library — ranked by summed "
              "Last.fm similarity from your listening graph. Check off ones you've tried; "
              "this feeds the same spirit as [[Next Directions]] but is computed, not hand-flagged.", ""]
    for f in frontier:
        via = ", ".join(f["via"])
        lines.append(f"- [ ] **{f['name']}** (score {f['score']:.2f}) — similar to {via}")
    return "\n".join(lines) + "\n"


def write_influence_lineage():
    if not os.path.exists(INFLUENCE_PATH):
        return None
    with open(INFLUENCE_PATH) as f:
        edges = json.load(f)
    curated = [e for e in edges if e["source"] == "curated"]
    llm = [e for e in edges if e["source"] == "llm"]

    lines = ["---", "type: analysis", "tags: [taste-analysis, influence]", "---", "", "# Influence Lineage", "",
              "Curated edges are ground truth from your hand-built knowledge graph. LLM-generated "
              "edges are my own music knowledge, clearly marked — correct or delete any that are wrong; "
              "re-runs never overwrite entries you've edited in `analysis/data/influence_edges.json`.", "",
              "## Curated (ground truth)", ""]
    for e in curated:
        note = f" — {e['note']}" if e.get("note") else ""
        lines.append(f"- **{e['from']}** {e['type']} **{e['to']}**{note}")
    lines.append("")
    lines.append("## LLM-generated (labeled, correctable)")
    lines.append("")
    for e in llm:
        note = f" — {e['note']}" if e.get("note") else ""
        lines.append(f"- **{e['from']}** {e['type']} **{e['to']}** *(confidence: {e['confidence']})*{note}")
    return "\n".join(lines) + "\n"


def update_artist_frontmatter(path, meta_genres, lastfm_tags):
    """Append/replace ONLY the meta_genres/lastfm_tags frontmatter keys —
    every other line (including the full hand-written body) is untouched."""
    with open(path) as f:
        text = f.read()
    if not text.startswith("---"):
        return False
    end = text.index("---", 3)
    fm = text[3:end]
    rest = text[end:]  # starts with the closing "---"

    lines = [l for l in fm.strip("\n").split("\n")
              if not l.startswith("meta_genres:") and not l.startswith("lastfm_tags:")]
    if meta_genres:
        lines.append("meta_genres: [" + ", ".join(meta_genres) + "]")
    if lastfm_tags:
        lines.append("lastfm_tags: [" + ", ".join(lastfm_tags) + "]")

    new_text = "---\n" + "\n".join(lines) + "\n" + rest
    if new_text == text:
        return False
    with open(path, "w") as f:
        f.write(new_text)
    return True


def enrich_artist_notes(G):
    if not os.path.isdir(ARTISTS_DIR):
        return 0
    name_to_attrs = {
        G.nodes[n]["label"]: G.nodes[n]
        for n in G.nodes if G.nodes[n].get("kind") == "artist"
    }
    updated = 0
    for path in glob.glob(os.path.join(ARTISTS_DIR, "*.md")):
        stem = os.path.splitext(os.path.basename(path))[0]
        # match by filename stem against known artist labels (safe() strips
        # characters that also get stripped from filenames, so this is a
        # reliable enough join without needing a stored id in every note)
        match = next((name for name in name_to_attrs if safe(name) == stem), None)
        if not match:
            continue
        attrs = name_to_attrs[match]
        if update_artist_frontmatter(path, attrs.get("meta_genres", []), attrs.get("lastfm_tags", [])):
            updated += 1
    return updated


def ensure_home_link():
    home_path = os.path.join(VAULT_DIR, "Home.md")
    if not os.path.exists(home_path):
        return
    with open(home_path) as f:
        content = f.read()
    # Replace a prior "## Taste Analysis" section entirely (rather than skip)
    # so link lists added in later runs actually show up.
    content = re.sub(r"\n## Taste Analysis\n.*$", "", content, flags=re.S).rstrip("\n")
    content = content + "\n\n## Taste Analysis\n\n" \
        "- [[Genre Breakdown]] — computed play-time genre share\n" \
        "- [[Bridge Artists]] — genre-spanning artists by betweenness centrality\n" \
        "- [[Meta-Genre Map]] — Wikidata-derived genre hierarchy, weighted by play time\n" \
        "- [[Discovery Frontier]] — computed adjacent-unheard recommendations\n" \
        "- [[Influence Lineage]] — curated + LLM-generated influence edges\n" \
        "- `Taste Analysis/` folder — dated snapshots over time\n"
    with open(home_path, "w") as f:
        f.write(content)


def main():
    with open(SUMMARY_PATH) as f:
        summary = json.load(f)

    artist_cache = load_artist_cache()
    influence_edges = load_influence_edges()
    taxonomy = load_taxonomy()
    tracks, _ = load_tracks()
    G = build_graph(tracks, artist_cache, influence_edges, taxonomy)
    G, _, _ = prune(G)
    library_names = {G.nodes[n]["label"] for n in G.nodes if G.nodes[n].get("kind") == "artist"}

    os.makedirs(TASTE_DIR, exist_ok=True)

    with open(os.path.join(TASTE_DIR, "Genre Breakdown.md"), "w") as f:
        f.write(write_genre_breakdown(summary))

    with open(os.path.join(TASTE_DIR, "Bridge Artists.md"), "w") as f:
        f.write(write_bridge_artists(summary))

    meta_genre_md = write_meta_genre_map(artist_cache, taxonomy)
    if meta_genre_md:
        with open(os.path.join(TASTE_DIR, "Meta-Genre Map.md"), "w") as f:
            f.write(meta_genre_md)

    frontier = compute_discovery_frontier(artist_cache, library_names)
    with open(os.path.join(TASTE_DIR, "Discovery Frontier.md"), "w") as f:
        f.write(write_discovery_frontier(frontier))

    influence_md = write_influence_lineage()
    if influence_md:
        with open(os.path.join(TASTE_DIR, "Influence Lineage.md"), "w") as f:
            f.write(influence_md)

    updated_notes = enrich_artist_notes(G)

    import datetime
    date_str = os.environ.get("TASTE_SNAPSHOT_DATE") or datetime.date.today().isoformat()
    snapshot_name = f"Taste Snapshot — {date_str}.md"
    with open(os.path.join(TASTE_DIR, snapshot_name), "w") as f:
        f.write(write_snapshot(summary, date_str))

    ensure_home_link()

    print(f"Wrote {TASTE_DIR}/Genre Breakdown.md, {TASTE_DIR}/Bridge Artists.md, "
          f"{TASTE_DIR}/Meta-Genre Map.md, {TASTE_DIR}/Discovery Frontier.md, "
          f"{TASTE_DIR}/Influence Lineage.md, {TASTE_DIR}/{snapshot_name}")
    print(f"Enriched frontmatter on {updated_notes} existing artist notes (bodies untouched).")


if __name__ == "__main__":
    main()
