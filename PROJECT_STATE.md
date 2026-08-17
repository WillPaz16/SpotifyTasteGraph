# Project State — exact inventory as of 2026-08-17

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
9. Picked the crawl back up. A requested review of the whole project first
   found two real bugs blocking a safe full-scale run: `enrich.py`'s
   `lastfm_similar`/`lastfm_tags` had no 429 retry/backoff (unlike the
   Wikidata calls), risking either a crash or a rate-limited artist silently
   cached as "zero similar artists" forever; and `crawl.py`'s error-abort
   counter was cumulative rather than consecutive, risking an early abort on
   sporadic transient errors over the ~3hr run. Fixed both before resuming.
10. Ran the full crawl. It was killed twice by the harness's background-task
    teardown between conversational turns before switching to a
    `nohup ... & disown`-detached process that survived independently of the
    session — completed cleanly at **15,000/15,000 artists, 0 errors**,
    checked in on a 15-minute cadence per Will's request throughout.
11. Built the remaining three phases of `FLAVORGRAPH_PLAN.md`: `embed.py`
    (metapath-constrained walks → Word2Vec → UMAP), `atlas.py` (the
    interactive HTML map), and the vault's `Taste Atlas.md` + `Next
    Directions.md` frontier section. Ran and reported all 5 falsifiable
    verification checks honestly, including where they didn't fully pass
    (power-law fit rejected in favor of exponential, known-lineage only
    partially mutual, personal coherence a real-but-weak signal).
12. Will's Chrome reported "WebGL is disabled" when opening
    `taste_atlas.html` — `atlas.py` was using WebGL-accelerated `Scattergl`
    traces; switched to plain SVG `Scatter` traces so the map no longer
    depends on hardware acceleration at all, and regenerated.
13. Will asked to fix the artist-name duplicate issue flagged during the
    build. Wrote `analysis/dedupe_universe.py`: merged 9 apostrophe/case
    duplicate groups (data-driven canonical-spelling tiebreak by which
    variant more other crawled artists already point to) and dropped 29
    "compound-junk" nodes where Last.fm returned a multi-artist credit
    string as if it were one artist. Universe 15,000 → 14,962; re-ran
    `embed.py`/`atlas.py`/`vault_writer.py` and verified the numbers held
    steady.
14. Asked to step back and critically analyze the whole build — a measured
    (not guessed) pass surfaced 4 concrete, numbered gaps: the dedup was
    incomplete (~51 more candidate groups existed), the two weaker
    verification checks had only ever run once, territory coloring was
    diluted by non-genre tags (479 artists, 3.2%), and the influence-edge
    layer covered only 0.47% of the universe. Planned this as a "next
    version" (plan mode, user-approved) and executed all 4 — see the
    section immediately below for the full writeup, including a genuine
    false-positive risk found and fixed mid-implementation (naive
    punctuation-stripped deduping would have wrongly merged real artists
    like "Liv.e"/"Live").

## FlavorGraph reformulation — now fully built (2026-08-17)

Per `FLAVORGRAPH_PLAN.md`, all four phases are done and verified:

- ✅ `analysis/crawl.py` — run to completion. Fixed two real bugs first
  (found in code review, not guessed at): `enrich.py`'s `lastfm_similar`/
  `lastfm_tags` had no 429 retry/backoff (unlike the Wikidata calls),
  risking either a crash or a rate-limited artist silently cached as
  "zero similar artists" forever; and `crawl.py`'s error-abort counter was
  cumulative instead of consecutive, risking an early abort on sporadic
  transient errors over the ~3hr run. Both fixed (Last.fm calls now go
  through `_get_with_retry`; `consecutive_errors` resets on every success,
  `total_errors` is separate and only used for the summary print).
  The full crawl was killed and resumed from checkpoint three separate
  times in practice (twice by an environment issue, once intentionally) —
  **this is a live demonstration that the checkpoint/resume design works**,
  satisfying the plan's own "kill and restart mid-run" verification bullet.
  Final run: **15,000/15,000 artists, 0 errors.**
- ✅ `analysis/data/universe/universe.json` + `frontier.json` — the full
  crawled universe. Depth distribution peaks around depth 5 (2,212
  artists), tails out to depth 18 (5 artists), from 90 depth-0 seeds.
- ✅ `analysis/embed.py` — built and run. Heterogeneous artist-similar-artist
  (weighted) + artist-tagged-tag (bipartite) graph; metapath-constrained
  walks (`P_TAG_HOP=0.4`, `WALK_LENGTH=40`, `WALKS_PER_NODE=8` — a practical
  CPU-minutes budget, not the metapath2vec paper's larger defaults); gensim
  Word2Vec (skip-gram, 128-dim, negative sampling) trained on 120,000 walks
  / 6.57M tokens (~1 min); UMAP (cosine) projection to 2D. Outputs:
  `data/universe/embeddings.npy`, `embedding_names.json`, `atlas_coords.json`.
- ✅ `analysis/atlas.py` — built and run. `output/taste_atlas.html`
  (8.8MB Plotly scatter): every crawled artist as a point, colored by
  dominant Last.fm tag (14 named territories + "other"), your library
  overlaid and sized by play time, curated + LLM influence edges drawn as
  lines across the map. Honest deviation from the plan: "click: nearest
  neighbours" is implemented as hover (top-8 precomputed neighbours in the
  tooltip) since this is a static file with no backend — noted directly in
  the module docstring, not silently substituted.
- ✅ Vault `Taste Analysis/Taste Atlas.md` — written by
  `vault_writer.py`'s new `write_taste_atlas()`. Reports all 5 falsifiable
  checks with their actual numbers, including the ones that don't flatter
  the result (see below). Also appended a non-destructive "## Taste Atlas
  Frontier" section to `Next Directions.md` (Will's own hand-added entries
  above it are untouched — same append-only pattern as `ensure_home_link()`).

### The 5 falsifiable verification checks — reported as measured

1. **Degree power-law fit**: alpha=2.96, KS=0.150, but an exponential fits
   significantly better than a power law (log-likelihood ratio -1073.6,
   p≈0) — **the crawled graph does NOT cleanly reproduce flavor-network
   topology**, contrary to what the plan hoped for. Said so plainly rather
   than reporting only the alpha number, which alone would look closer to
   Ahn et al.'s ~2.3 than the fit comparison supports.
2. **Held-out link prediction AUC**: 0.994 vs a degree-preferential-attachment
   baseline of 0.670 (n=23,349 held-out edges, 10% holdout, retrained embedding).
   **Passes** the 0.7 threshold clearly — the embedding captures real
   structure well beyond raw degree.
3. **Known-lineage sanity** (Nick Drake / Bert Jansch / John Martyn /
   Tim Buckley): **NOT all mutual near-neighbours.** Nick Drake and Tim
   Buckley land close together; Bert Jansch is the outlier, absent from
   either's top-20 in both directions. Partial pass, reported honestly.
4. **Personal coherence silhouette**: 0.0083 (real) vs 0.0002±0.0022 (random
   baseline, 20 trials) — technically "more clustered than random" but both
   numbers are near zero in absolute terms. A real but modest signal, not
   a strong one.
5. **Isolated nodes**: 1 (`Yusuf / Cat Stevens`) — almost certainly a
   Last.fm/Spotify name-string mismatch (Last.fm likely lists him as plain
   "Cat Stevens"), not a crawl defect.

**Net read**: the embedding is structurally sound (check 2 passes clearly)
and personally meaningful (check 4, weakly), but two of the plan's more
ambitious claims — flavor-network-like topology (check 1) and clean mutual
lineage clustering (check 3) — did not fully hold up. This matches the
plan's own stated epistemic stance going in: a real, useful map, not the
"predicts unheard-of connections from an independent modality" claim that
Part I explicitly said this project can't make.

**Name-string duplicate issue — fixed 2026-08-17** via `analysis/dedupe_universe.py`,
run once against the raw crawl output:
- Merged 9 apostrophe/case duplicate groups (e.g. "DON WEST" vs "Don West",
  "Lil Wayne" vs "Lil' Wayne") — canonical spelling per group picked by
  which variant more OTHER crawled artists already point to in their
  `similar` lists, a data-driven tiebreak using the crawl's own evidence.
- Dropped 29 "compound-junk" nodes — Last.fm sometimes returns a
  multi-artist collaboration credit string (e.g. "Miles Davis, John
  Coltrane, Bill Evans") as if it were a single artist; detected as any
  name whose comma-split parts are ALL themselves separately-existing real
  artist nodes, and redirected any edge pointing at the junk node to each
  real component instead.
- Universe went from 15,000 → 14,962 artists (38 redundant/junk nodes
  removed, zero real artists lost). `embed.py`, `atlas.py`, and
  `vault_writer.py` were all re-run afterward against the cleaned graph —
  verification numbers are essentially unchanged (AUC still 0.994, alpha
  still ~2.96), confirming the dedup didn't distort the embedding.
- Same class of version/name-collapsing issue flagged elsewhere in this
  project (see the known Spotify URI incident below, and
  `FLAVORGRAPH_PLAN.md` Failure 1's MusicBrainz fragmentation note).
- Caveat: `data/universe/frontier.json` is now stale relative to the
  cleaned `universe.json` (still queues the old duplicate/junk name
  strings). This is harmless as-is since the crawl already hit its 15,000
  cap and won't resume — but if `crawl.py` is ever rerun to top off a
  future larger cap, it could reintroduce a few of these via the stale
  frontier. `dedupe_universe.py` is idempotent and cheap to re-run after
  any future crawl session if that happens.
- Some ambiguous compound-looking names remain untouched on purpose (e.g.
  "Kendrick Lamar, Tanna Leone") — the detector only merges/drops a name
  when ALL of its comma-split parts independently exist as separate real
  nodes elsewhere in the universe, to avoid false-positive merges of
  genuinely single-billed collab acts.

## FlavorGraph "next version" — dedup completion, seed variance, tag quality, influence expansion (2026-08-17)

A step-back analysis after the first build surfaced four concrete, measured gaps (not just
"could be better" — specific numbers). All four closed this session, in a planned order, each
verified against live data:

1. **Dedup completion** — extended `analysis/dedupe_universe.py` with two more passes beyond
   the original apostrophe/case/compound-junk logic:
   - A **safe auto-merge** pass unifying `" & "` / `", "` as equivalent list joiners (catches
     e.g. the many *Hamilton*-cast-credit string variants) — verified safe by inspection, zero
     false positives across the real examples found.
   - A **gated** pass for period-stripped near-duplicates (`JID`/`J.I.D`, `H.E.R.`/`Her`-style).
     Important finding: blind period-stripping has real false-positive risk — it would have
     wrongly merged `Liv.e`/`Live`, `Mike`/`M.I.K.E.`, `Wet`/`W.E.T.`, `Act`/`A.C.T`,
     `sports.`/`Sports`, all confirmed genuinely different artists by near-zero Last.fm tag-set
     overlap. So this pass only auto-merges when both variants have tags AND Jaccard similarity
     ≥ 0.25; everything else is logged to `data/universe/dedupe_review.json` (7 candidates
     logged this run, e.g. `Bobby V`/`Bobby V.` at 0.17 — plausible but not confident enough to
     auto-merge) rather than guessed at either direction.
   - Result: 20 more duplicate groups merged, 2 more punctuation-gated merges, universe went
     14,962 → 14,940. `data/universe/universe.json.bak` backups were made and removed after
     verification each time, same pattern as the first dedup pass.
   - Known residual gap: `"F. J. McMahon"` vs `"F.J. McMahon"` still exist as separate nodes —
     the internal-whitespace difference around the initials produces different normalized keys
     even after stripping periods. Not fixed; a real but minor limitation of the current
     normalization.
2. **Seed-variance check** — new `analysis/seed_variance.py`, re-running the embedding at 4
   seeds (42, 1, 7, 13) and recomputing the known-lineage and personal-coherence checks each
   time (skips the expensive link-prediction retrain and UMAP projection — not needed to answer
   this question). **Finding: not seed noise.** Bert Jansch never has Nick Drake in its own
   top-20 across any of the 4 seeds (0/4), while Bert Jansch and John Martyn are mutual
   neighbours in every seed (4/4 both directions) — a reproducible property of the embedding
   space. The coherence silhouette is also stable across seeds (0.0057–0.0082, always positive,
   always above that seed's own random baseline). Full breakdown in
   `data/universe/seed_variance_report.json`; summary now in the vault's `Taste Atlas.md` under
   "Seed sensitivity."
3. **Tag-quality denylist** — `atlas.py` was bucketing territories by each artist's raw first
   Last.fm tag with no filtering. Measured 479 artists (3.2% of the universe) had a non-genre
   tag (nationality, vocalist-gender, decade, or generic) as their primary tag. Added
   `NON_GENRE_TAG_DENYLIST` (16 tags: `american`/`usa`/`british`/etc., `male vocalists`/
   `female vocalists`, decade tags, `all`/`oldies`) and changed `compute_tag_buckets()` to fall
   through to the next usable tag; only 18 of the 479 have no other usable tag and become
   `"untagged"`. Visible effect: `singer-songwriter` now appears in the top-14 territories,
   previously buried under nationality-tag noise.
4. **Scoped influence-edge expansion** — full-universe LLM-edge coverage was explicitly ruled
   out (would mean fabricating confident-sounding claims for artists with no real basis,
   violating this project's hard rule). Instead scoped to artists the pipeline itself already
   surfaced as relevant: the atlas's geometric discovery frontier and the computed bridge
   artists. Added 16 new `LLM_EDGES` entries with real, statable connections (e.g. Ne-Yo wrote
   Mario's "Let Me Love You"; Gary Lucas co-wrote "Grace" with Jeff Buckley; Riley Green/Ella
   Langley's 2024 duet), and extended `SKIPPED_INSUFFICIENT_KNOWLEDGE` with 12 more artists
   (newer/niche country and indie acts) rather than guessing. Coverage moved from 70/14,962
   (0.47%) to 86/14,940 (0.58%) artists with any influence edge — a real but deliberately modest
   improvement, not an attempt at exhaustive coverage.

Full regeneration cascade run afterward: `atlas.py` → `taste_graph.py` → `vault_writer.py`
(`embed.py` was NOT re-run for steps 3–4 since neither the tag denylist nor the influence edges
affect the embedding itself, only downstream visualization/graph layers — re-running it would
have been redundant work for an identical result). Verified: zero broken vault wikilinks,
protected files (`music_graph.json`, `Artists/`, `Genres/`, `Concepts/`, `Playlists/`) untouched,
`output/taste_atlas.html` spot-checked live in a browser after each regeneration.

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
- `analysis/data/influence_edges.json` — 86 influence edges (30 curated + 56 LLM-generated)
- `analysis/output/` — `taste_graph.graphml`, `taste_map.html`, `genre_tree.html`,
  `discovery.html`, `summary.json`, `taste_atlas.html` (8.8MB)
- `analysis/data/universe/` — `universe.json` (14,940 artists post-dedup), `frontier.json`
  (stale, see caveat above), `embeddings.npy` (128-dim, 14,940 artists), `embedding_names.json`,
  `atlas_coords.json` (2D UMAP projection), `verification_report.json`,
  `dedupe_review.json` (7 low-confidence merge candidates logged, not auto-merged),
  `seed_variance_report.json` (4-seed reproducibility check on checks 3/4)

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

The FlavorGraph reformulation (crawl → embed → atlas → vault, all 4 phases
of `FLAVORGRAPH_PLAN.md`) is now built and verified — see the section above
for the honest per-check results. It does not need to be re-run; the outputs
in `analysis/data/universe/`, `analysis/output/taste_atlas.html`, and the
vault's `Taste Analysis/Taste Atlas.md` are current as of 2026-08-17.

Open follow-ups, none started:
- The name-string duplicate issue flagged above (e.g. "Lil' Wayne" vs
  "Lil Wayne" as separate universe nodes) — would need a normalization pass
  before re-crawling or re-embedding to fix cleanly.
- `analysis/crawl.log` exists from the nohup-detached run; not committed to
  version control by `.gitignore`, safe to delete if it gets noisy.
- If you want to re-run `embed.py`/`atlas.py` after a future re-crawl,
  re-read `FLAVORGRAPH_PLAN.md` Part III first for the metapath-walk
  rationale and the verification checks' pass/fail thresholds.
