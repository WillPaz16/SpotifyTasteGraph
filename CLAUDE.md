# Music Second Brain — Project Guide

This directory is Will Paz's personal music-taste project: an Obsidian knowledge
graph of his listening + discovery, backed by a Python analysis pipeline that
enriches it with real external data (Wikidata, Last.fm) and computes graph
structure (genres, influence, similarity, discovery).

**If you are picking this up in a new session/account: read this file first,
then [`PROJECT_STATE.md`](PROJECT_STATE.md) for exactly what's built and what's
next, then [`FLAVORGRAPH_PLAN.md`](FLAVORGRAPH_PLAN.md) for the deepest, most
recent piece of work (an honest failure/reformulation analysis — read it before
building anything music-graph-adjacent so you don't repeat solved problems).**

---

## Directory map

```
research/taste-data/          Raw Spotify export + the original ambitious analysis spec
  spotify_data.json             top_tracks + recent_tracks, RICH descriptors/producer/composer data
  top_tracks.json               pristine standalone backup of top_tracks (see "known incident" below)
  recent_tracks.json            pristine standalone backup of recent_tracks
  PROMPT.md                    the original (unbuilt-beyond-Phase-3) full analytics spec

research/ml-research/         Personal study material — Spotify recsys curriculum + a research
                               proposal that seeded the FlavorGraph idea. Backburnered per Will.

exploration/music-knowledge-graph/   The ORIGINAL hand-curated graph (pre-Obsidian)
  music_graph.json              35 artists, 8 genres, 4 concepts, 30 edges, 6 playlists — ground truth
  MUSIC_GRAPH.md                human-readable version of the same
  INSTRUCTIONS.md               update protocol for this graph (written by a "Kit" assistant persona)

exploration/obsidian-vault/    THE LIVE VAULT — open this folder directly in Obsidian.
  Artists/, Genres/, Concepts/, Playlists/    generated from music_graph.json, one note per entity
  Taste Analysis/               generated/refreshed by analysis/vault_writer.py — see below
  Home.md                       entry point, links to everything including Taste Analysis
  Next Directions.md            checklist of flagged listens
  README.md                     vault's own front-door note (says it's now the primary source of truth)

analysis/                     THE PYTHON PIPELINE — all data enrichment + graph computation lives here
  (see PROJECT_STATE.md for the full file-by-file rundown, this is just orientation)
```

## The two-graph situation (important, easy to get wrong)

There are **two music graphs** in this project and they are NOT the same namespace:

1. **`exploration/music-knowledge-graph/music_graph.json`** — hand-curated by
   Will through conversation with an assistant ("Kit"). Snake_case ids
   (`nick_drake`), rich prose, `will_response` field. **This is ground truth**
   — never overwrite it programmatically.
2. **The computed taste graph** (built by `analysis/taste_graph.py`) — derived
   from actual Spotify listening data + Last.fm/Wikidata enrichment. Keyed by
   artist display name. Includes artists Will has *listened to* that may not
   yet be in the curated graph at all (these are largely disjoint sets —
   measured overlap was only ~6 of 96 listening-graph artists also appearing
   in the 35-artist curated graph).

`analysis/influence.py` is what bridges them: it imports the 30 curated edges
as ground truth, then adds LLM-generated edges for everything else, clearly
tagged `source: "curated"` vs `source: "llm"` so the two are never confused.

## Hard rules for working in this project

- **Never overwrite `music_graph.json`, `MUSIC_GRAPH.md`, or the hand-written
  prose bodies of `exploration/obsidian-vault/Artists|Genres|Concepts|Playlists/*.md`.**
  These are Will's own curation. `vault_writer.py`'s `enrich_artist_notes()`
  demonstrates the correct pattern: patch ONLY specific frontmatter keys
  (`meta_genres`, `lastfm_tags`), leave everything else byte-identical.
- **Never fabricate confident-sounding facts as if they were sourced.**
  `influence.py` is the model to follow: every LLM-generated claim carries
  `source: "llm"` and a `confidence` level, and artists with no reliable
  knowledge are logged as skipped rather than guessed at (see
  `SKIPPED_INSUFFICIENT_KNOWLEDGE` in that file).
- **`analysis/.env` holds real API credentials (Spotify + Last.fm). Never
  read, print, or paste its contents into chat** — this was established
  explicitly with Will as a hard boundary, not just a style preference.
- **Verify data-source claims before building on them.** Multiple past
  mistakes in this project came from assuming an API/dataset worked without
  testing it live (stats.fm's nonexistent public API, Spotify's deprecated
  audio-features, Wikidata's ambiguous label matching). See
  `FLAVORGRAPH_PLAN.md` Part I for the full accounting — it's a template for
  the level of verification this project now expects.

## Known data incident (already resolved, but know the history)

An early version of `analysis/spotify_live.py` overwrote `spotify_data.json`'s
rich `top_tracks`/`recent_tracks` (producer/composer/descriptors) with
genre-less live-API data, because Spotify's Web API doesn't expose that
metadata at all for apps without extended access. It was recovered from the
untouched standalone `top_tracks.json`/`recent_tracks.json` backups — **those
two files are the recovery source and should never be deleted.**
`spotify_live.py` was then rewritten to merge (preserve existing rich rows,
only add genuinely new tracks) rather than overwrite. Do not reintroduce the
overwrite behavior.

## Environment

- `analysis/.venv/` — Python venv with all deps (networkx, pyvis, gensim,
  umap-learn, spotipy, requests, plotly, python-louvain, powerlaw, etc.) See
  `analysis/requirements.txt` for the full pinned list.
- `analysis/.env` — Spotify (`SPOTIPY_CLIENT_ID/SECRET/REDIRECT_URI`) and
  `LASTFM_API_KEY` credentials, already configured and working (Will set
  these up himself; do not ask him to re-paste them into chat).
- No git repository in this project (confirmed at session start). No commit
  history to consult — this file and `PROJECT_STATE.md` are the memory.
