# Project State — exact inventory as of 2026-08-16

Read [`CLAUDE.md`](CLAUDE.md) first for orientation. This file is the detailed
"what's actually built, what's verified, what's next" record.

## Timeline of what happened this session (chronological, so the "why" is clear)

1. Read through the existing folder (Spotify export, hand-curated knowledge
   graph, research proposals) — nothing built yet, just data + docs.
2. Converted the hand-curated `music_graph.json`/`MUSIC_GRAPH.md` into a real
   Obsidian vault (`exploration/obsidian-vault/`) — one note per artist/genre/
   concept/playlist, wikilinked. Verified zero broken links, correct counts
   (35/8/4/6). Vault is now the primary place Will edits going forward.
3. Investigated stats.fm as a data source — **dead end**, no public
   self-serve API, confirmed by testing.
4. Built a v1 taste-analysis pipeline (`analysis/`) against the existing
   `spotify_data.json`: parsing, a NetworkX graph, pyvis visualization, vault
   write-back. Set up Spotify Web API OAuth (`auth_setup.py`) and a live
   refresh script (`spotify_live.py`).
5. **Incident**: `spotify_live.py`'s first version overwrote the rich
   `spotify_data.json` with genre-less data (Spotify's API doesn't return
   artist genres for apps without extended access — confirmed by direct
   testing, `sp.artist(...)['genres']` comes back `None`). Recovered from
   `top_tracks.json`/`recent_tracks.json` backups. Rewrote `spotify_live.py`
   to merge instead of overwrite.
6. Will noticed the taste graph was "highly disconnected." Diagnosed root
   causes via a full code audit (not guessing): a descriptor-parsing bug
   losing 91.5% of genre tags, `classify()` keeping only the first genre per
   track, a pre-add edge-weight gate that left low-play artists as orphaned
   nodes, and no shared join key between the curated graph and the computed
   one.
7. Full rebuild: verified three real external data sources live
   (Wikidata genres — dense; Wikidata influence — confirmed dead for
   musicians; Last.fm similarity/tags — dense, free, no OAuth). Built
   `enrich.py`, `genre_taxonomy.py`, `influence.py`, rewrote `taste_graph.py`
   with 5 real edge layers, built `views.py` (3 visual outputs), extended
   `vault_writer.py`. **Caught and fixed two more bugs mid-build**: a
   Wikidata rate-limit/caching bug (failed attempts were cached as
   "resolved", silently skipping retries) and a Wikidata label-collision bug
   (`"funk"` matched an unrelated non-music entity before a `P31/P279*`
   music-genre filter was added). All verified against live API responses,
   not assumed.
8. Will asked for a music-domain FlavorGraph (population-scale, ingredient-
   style graph with a "molecular layer"). Rather than build it speculatively,
   ran a measured feasibility check first — see `FLAVORGRAPH_PLAN.md`. Found
   3 real failure modes (one permanent), reformulated around what's actually
   viable, and started building (`crawl.py` written + smoke-tested at small
   scale). **The full-scale crawl (~15K artists, ~3hrs) was started then
   stopped early at Will's request** (usage-limit caution + wanting this
   documentation first) — see "Exact state of unfinished work" below.

## Exact state of unfinished work (the FlavorGraph reformulation)

Per `FLAVORGRAPH_PLAN.md`, approved and partially executed:

- ✅ `analysis/crawl.py` — written, smoke-tested at `MAX_ARTISTS=30` (96 seeds
  → 30 crawled across depths 0–2, checkpointing logic exercised, zero
  errors). **Not yet run at full scale.**
- ❌ `analysis/data/universe/` — **does not exist**. The full crawl was
  started (`nohup ./.venv/bin/python crawl.py`) then killed via `pkill -f
  crawl.py` before its first checkpoint (every 250 artists), at Will's
  request. No partial universe data was saved — restarting `crawl.py` will
  start completely fresh from the 96 library seeds, not resume anything.
- ❌ `analysis/embed.py` — not started (metapath2vec-style walks + gensim
  Word2Vec + UMAP projection, per the plan's Phase 2).
- ❌ `analysis/atlas.py` — not started (the navigable HTML map, per Phase 3).
- ❌ Vault `Taste Atlas.md` — not started (Phase 4).
- ❌ The 5 falsifiable verification checks in the plan (power-law fit,
  held-out link prediction AUC, known-lineage sanity check, personal
  coherence silhouette score, isolated-node check) — none run yet since
  there's no crawled universe to check.

**To resume**: run `cd analysis && ./.venv/bin/python crawl.py` in the
background (it's a ~3 hour job at measured ~3 req/s Last.fm throughput,
2 calls/artist, capped at 15,000 artists, checkpointing every 250 to
`data/universe/universe.json` + `frontier.json` so it's killable/resumable
from that point forward). Then build `embed.py` and `atlas.py` per the plan.

## Everything that IS built, working, and verified right now

### `exploration/obsidian-vault/` (Obsidian vault — open this folder directly)

- 35 Artist notes, 8 Genre notes, 4 Concept notes, 6 Playlist notes — generated
  from `music_graph.json`, wikilinked, zero broken links (checked with a
  `comm` diff between linked-to names and existing filenames).
- `Taste Analysis/` folder (generated/refreshed by `vault_writer.py`):
  - `Genre Breakdown.md` — play-time share by macro-genre
  - `Bridge Artists.md` — top betweenness-centrality artists
  - `Meta-Genre Map.md` — Wikidata-derived genre hierarchy weighted by play time
  - `Discovery Frontier.md` — Last.fm-similarity-derived "not yet in your
    library" recommendations, as a checkbox list
  - `Influence Lineage.md` — curated (ground truth) + LLM-generated
    (labeled, with confidence) influence edges
  - `Taste Snapshot — <date>.md` — one per pipeline run, never overwritten
- 6 of the 35 hand-curated Artist notes have enriched frontmatter
  (`meta_genres`, `lastfm_tags`) added — only those 6 overlap with the
  listening-graph artist set; **verified their prose bodies are byte-identical
  to before** (spot-checked `Al Green.md`).
- `Home.md` links to all of the above.

### `analysis/` pipeline (all verified working end-to-end on real data)

| File | Purpose | Verified state |
|---|---|---|
| `parse.py` | Parses `spotify_data.json`'s packed metadata strings; dedupes track versions; classifies genre/mood | Fixed descriptor-splitting bug (was losing 91.5% of tags) and artist-name-splitting bug (`"and Sampha"`). Verified zero garbage tokens remain. `classify()` now returns ALL matched genres, not just the first. |
| `enrich.py` | Builds `data/artists.json` — per-artist Wikidata genres + Last.fm similarity/tags, keyed by Spotify URI | 88/96 artists resolved on Wikidata, 95/96 on Last.fm (measured, logged unresolved ones by name rather than dropping silently). Rate-limit retry/backoff added after hitting real 429s. |
| `genre_taxonomy.py` | Walks Wikidata's P279 ("subclass of") hierarchy to build a real meta-genre tree | 115 observed genres → 28 meta-genre roots. Fixed a label-collision bug (verified via direct SPARQL `ASK` queries before and after the fix). |
| `influence.py` | Builds `data/influence_edges.json` — imports the 30 curated edges as ground truth, adds 40 LLM-generated edges (each with `source`/`confidence`/`note`), explicitly skips 6 artists with insufficient reliable knowledge | Run and verified: 30 curated + 40 LLM = 70 total edges. |
| `taste_graph.py` | Builds the multi-layer NetworkX graph (listening/similarity/influence/collab/production edges), computes centrality/PageRank/Louvain communities, exports graphml + `taste_map.html` | Rewrote edge-pruning to be a real post-hoc prune (not a pre-add gate) — **assert-verified zero isolated nodes** on every run. |
| `views.py` | Builds `genre_tree.html` (Wikidata hierarchy sunburst, play-time weighted) and `discovery.html` (bridge artists + curated discovery paths + the adjacent-unheard frontier) | Both render; discovery frontier spot-checked and produces sensible real recommendations (e.g. Riley Green, Luke Combs, RAYE — not fabricated, derived from actual Last.fm similarity to loved artists). |
| `vault_writer.py` | Writes all `Taste Analysis/` notes + non-destructively enriches existing Artist note frontmatter | Verified: zero broken wikilinks after write, hand-written note bodies unchanged. |
| `spotify_live.py` | Refreshes `spotify_data.json` from the Spotify Web API | Rewritten after the overwrite incident (see timeline #5) to merge, not overwrite. Documents the real limitation (no producer/composer/descriptor/genre data available live). |
| `auth_setup.py` | One-time Spotify OAuth flow | Run successfully; token cached at `.spotify_token_cache`. |
| `crawl.py` | BFS crawl of Last.fm similarity graph outward from the 96 library artists | Written, smoke-tested only (see "unfinished work" above). |

### Data files that exist right now

- `analysis/data/artists.json` — 96-artist enrichment cache
- `analysis/data/genre_taxonomy.json` + `genre_parents_cache.json` — 115-genre taxonomy
- `analysis/data/influence_edges.json` — 70 influence edges
- `analysis/output/` — `taste_graph.graphml`, `taste_map.html`, `genre_tree.html`,
  `discovery.html`, `summary.json`
- `analysis/data/universe/` — **does not exist yet** (see above)

## Measured facts worth remembering (so they aren't re-derived from scratch)

- Will's listening library: 72 unique tracks after dedup, ~95 unique artists.
- Overlap between the hand-curated 35-artist graph and the 96-artist
  listening graph: only ~6 artists. They are largely different sets — the
  curated graph is discovery-focused (folk/flamenco/soul lineage), the
  listening graph is dominated by country/pop/hip-hop.
- Spotify `/audio-features` and `preview_url`: both dead for any app created
  after Nov 27, 2024 (confirmed — this project's Spotify app is one such app).
- AcousticBrainz: frozen since June 2022, live API returns 200 but almost all
  lookups 404. Measured join rate on Will's top 12 tracks by MusicBrainz
  recording MBID: **3/12 = 25%**, and the misses are exactly the post-2022
  releases (47% of his tracks, 45% of his listening time).
- Last.fm measured throughput: ~3.1 req/s unthrottled, 2 calls needed per
  artist (similar + tags) for the crawl.
- stats.fm: no public self-serve developer API exists (confirmed by
  searching + reading their GitHub org — only unofficial reverse-engineered
  SDKs, and full history import requires stats.fm Plus).

## If picking this up fresh, recommended next action

Re-read `FLAVORGRAPH_PLAN.md` in full before touching `crawl.py`/`embed.py`/
`atlas.py` — it contains the reasoning for why the project is scoped the way
it is (population-scale artist graph via Last.fm, NOT a track-level or
audio-feature-based graph) and the falsifiable checks that should gate
whether the embedding is worth trusting. Then just run the crawl.
