# Spotify Taste Graph

A personal music-taste knowledge graph: an [Obsidian](https://obsidian.md) vault
of hand-curated artists, genres, concepts, and playlists, backed by a Python
pipeline that enriches it with real external data (Wikidata, Last.fm) and
computes graph structure — genre relationships, influence lineage, similarity,
and discovery frontiers — from actual Spotify listening history.

## Structure

```
research/taste-data/          Raw Spotify export + the original analysis spec
research/ml-research/         Background research/study material (backburnered)

exploration/music-knowledge-graph/   Hand-curated ground-truth graph
                                      (35 artists, 8 genres, 4 concepts, 30 edges)

exploration/obsidian-vault/    The live vault — open this in Obsidian
  Artists/, Genres/, Concepts/, Playlists/   one note per entity
  Taste Analysis/               generated/refreshed by the pipeline
  Home.md                       entry point

analysis/                     The Python pipeline — data enrichment + graph
                               computation (parsing, Wikidata/Last.fm enrichment,
                               influence & taste graphs, vault write-back)
```

There are two graphs in this project: the hand-curated one (ground truth,
never overwritten programmatically) and a computed graph derived from actual
listening data, with LLM-assisted edges clearly tagged by source and
confidence. See [`CLAUDE.md`](CLAUDE.md) for the full breakdown, ground rules,
and the two-graph bridging logic.

## Getting started

- Read [`CLAUDE.md`](CLAUDE.md) for project orientation and hard rules.
- Read [`PROJECT_STATE.md`](PROJECT_STATE.md) for exactly what's built and
  what's next.
- Read [`FLAVORGRAPH_PLAN.md`](FLAVORGRAPH_PLAN.md) before building anything
  music-graph-adjacent — it documents prior failed approaches so they aren't
  repeated.

### Running the pipeline

```bash
cd analysis
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Spotify + Last.fm credentials
```

Raw listening data and API credentials are kept out of this repo — see
`.gitignore` and `analysis/.gitignore`.
