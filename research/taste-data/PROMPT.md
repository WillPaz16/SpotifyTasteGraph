# Spotify Taste Graph — Claude Code Prompt

## Context

You are building a personal music taste graph and analysis dashboard from Spotify listening data. The data is in `spotify_data.json` alongside this file. This is a data science project: the goal is to surface meaningful structure in listening behavior — not just pretty charts, but genuine insight into how genres, moods, artists, producers, and temporal patterns connect.

The data has three sections:
- `taste_profile` — Spotify's identity summary and top artist URIs
- `top_tracks` — all-time top played tracks ranked by `played_seconds` (a stronger engagement signal than play count), with per-track metadata: descriptors (genre/mood tags), producers, composers, release date, artist URIs
- `recent_tracks` — last 50 plays with timestamps and `played_seconds`

---

## Phase 1: Data Parsing & Feature Engineering

Parse `spotify_data.json`. For each track, extract and normalize:

- `track_uri`, `track_name`, `artist_names` (list), `artist_uris` (list)
- `descriptors` (list of genre/mood tags — these are the primary clustering signal)
- `producers` (list), `composers` (list)
- `release_year` (parse from `released_on`)
- `played_seconds` (engagement weight)
- `last_played_at` (ISO timestamp — parse to datetime)
- `decade` (derived from release_year)
- `is_recent` (flag: appears in recent_tracks)

Build a unified track DataFrame combining top and recent, deduplicating by URI. Tracks appearing in both datasets should have `played_seconds` from top_tracks (more reliable) and `last_played_at` from recent_tracks.

**URI normalization (run before deduplication):** Spotify assigns distinct URIs to different versions of the same song — originals, live recordings, remasters, radio edits, remixes, and deluxe pressings all get separate IDs. For the taste graph, these should collapse to a single canonical node, otherwise the co-occurrence matrix fragments and similarity scores degrade.

Normalization steps:
1. Strip version qualifiers from track names using regex: remove anything matching ` - (Live|Live From|Live At|Remaster(ed)?|Radio Edit|Remix|Acoustic|Deluxe|A COLORS SHOW|feat\..+)` (case-insensitive) to get a `canonical_name`.
2. Group by `(canonical_name, primary_artist_uri)` — this is the canonical track identity.
3. Within each group, prefer the URI whose raw track name has the fewest characters (shortest name = fewest qualifiers = most likely original). Assign this as `canonical_uri`.
4. Map all version URIs in the group to `canonical_uri` before building any graph edges or co-occurrence matrices.
5. Sum `played_seconds` across all versions in the group — if you played the live and studio version, both counts belong to the canonical track.
6. Add a `version_type` column to the DataFrame: `original`, `live`, `remaster`, `remix`, `radio_edit`, `acoustic`, `other`. Use this for optional version-aware analysis later (e.g. "do I engage differently with live recordings?").

Flag any track where normalization collapsed 2+ URIs — log these as `uri_collision` for review.

---

## Phase 2: Descriptor Vocabulary & Genre Taxonomy

Build a flat vocabulary of all unique descriptors across the corpus. Then group them into a two-level taxonomy:

**Level 1 — Macro genres** (suggested starting clusters, adjust from data):
- `country_americana`: country, country blues, americana, folk rock, honky tonk
- `hip_hop_rap`: hip hop, rap, pop rap, trap, trap latino
- `pop`: pop, bubblegum pop, easy listening
- `r_and_b_soul`: r&b, soul, soul funk, soulful, motown, jazz blues
- `indie_folk`: indie folk, folk, folk pop, indie pop, indie
- `alternative_rock`: alternative rock, rock, grunge, britpop, garage rock, new wave
- `latin`: latin, reggaeton, salsa, sierreño, merengue
- `electronic`: house, club, electronic, ibiza
- `classical_musicals`: musicals, classical
- `mood_tags`: sad, melancholy, slow, romantic, love, cozy, chill, calm, nostalgia, moody, sensual, classy, soulful, nature, acoustic

Each track gets a `macro_genre` (primary) and `mood_tags` (secondary, can be multiple). If a track has no descriptors, label it `unknown`.

---

## Phase 3: Taste Network Graph

Use `networkx`. Build a weighted undirected graph where:

**Nodes** — three types:
- Artist nodes: `artist_uri`, label = artist name
- Genre nodes: macro genre labels
- Mood nodes: mood tag labels

**Edges**:
- Artist → Genre: weight = sum of `played_seconds` for tracks by that artist in that genre
- Artist → Mood: weight = sum of `played_seconds` for tracks by that artist with that mood tag
- Artist → Artist: weight = number of shared tracks (collabs), or shared producers/composers (production kinship)
- Genre → Genre: weight = number of tracks that span both genres (multi-descriptor tracks)

**Node attributes**:
- Artists: `total_played_seconds`, `track_count`, `avg_release_year`, `top_track`
- Genres/Moods: `total_played_seconds`, `artist_count`, `track_count`

Store the graph. Compute and attach as node attributes:
- Degree centrality
- Betweenness centrality (identifies genre bridge artists)
- PageRank (overall taste importance)
- Community detection via Louvain algorithm (`python-louvain` / `community` package)

---

## Phase 4: Temporal Analysis

Using `last_played_at` from recent_tracks and the full top_tracks corpus:

- **Listening heatmap**: hour-of-day × day-of-week matrix, colored by `played_seconds`. Show which time slots have the most engagement.
- **Genre-by-time**: for recent tracks, group by hour bucket (morning 6–12, afternoon 12–17, evening 17–22, night 22–6) and show macro_genre distribution per bucket as a stacked bar.
- **Release decade distribution**: bar chart of `played_seconds` by decade — shows how much the user reaches into the past vs. listens to new releases.
- **Recency curve**: plot `played_seconds` vs. `release_year` to see if engagement decays for older music or spikes for specific eras.

---

## Phase 5: Producer & Composer Network

Build a bipartite graph: producers/composers → tracks → artists.

Identify:
- **Power producers**: producers who appear across multiple macro_genres (cross-genre taste-makers)
- **Production clusters**: sets of tracks sharing a producer — often explains why disparate artists feel sonically linked
- **Composer lineage**: tracks sharing a composer (covers, samples, re-recordings)

Output a ranked table: producer name, genres spanned, total played_seconds across their tracks, top track.

---

## Phase 6: Similarity & Discovery Engine

Build a track-level feature matrix for similarity:

Features per track:
- One-hot encoded descriptors (all unique tags)
- `played_seconds` (log-normalized)
- `release_year` (normalized 0–1)
- Macro genre (one-hot)

Compute cosine similarity between all track pairs. Store as a sparse matrix.

Build two outputs:
1. **"More like this"**: given a track URI, return top 10 most similar tracks from the corpus with similarity scores.
2. **Taste gap detector**: find tracks with high similarity to the user's top tracks that are NOT already in the corpus — this requires enriching with external data, so flag this as a stub with a note on how to wire in the Spotify Web API's recommendations endpoint using audio features.

---

## Phase 7: Interactive Dashboard

Build a single-file HTML dashboard (or Dash/Streamlit app — your choice based on portability preference). It should have these views, switchable via tabs or sidebar:

### 7a. Taste Network (primary view)
Interactive graph using `pyvis` or `d3.js` (via pyvis export). Nodes sized by PageRank, colored by community/macro_genre. Hovering a node shows: name, total played seconds, top track, top mood. Clicking an artist node highlights their genre and mood connections.

### 7b. Genre Breakdown
Donut chart: macro_genre share by played_seconds. Below it: a table of top 5 tracks per genre sorted by played_seconds.

### 7c. Temporal Heatmap
Hour × day heatmap. Toggle between: all tracks / country_americana / hip_hop_rap / r_and_b_soul.

### 7d. Producer Intelligence
Table: producer → genres → tracks → total engagement. Sortable. Clicking a producer row highlights all their tracks in the network view if possible.

### 7e. Discovery (Similarity)
Input: paste a track URI or pick from a dropdown of top tracks. Output: top 10 similar tracks from corpus, displayed as cards with descriptor tags and similarity score.

---

## Implementation Notes

- Use `pandas`, `networkx`, `matplotlib`/`plotly`, `pyvis`, `scikit-learn` (cosine similarity), `python-louvain`.
- Parse all descriptor strings carefully — they are comma-separated and may be quoted (e.g. `"country blues"`, `"pop rap"`). Strip quotes and lowercase.
- `played_seconds` is the primary engagement signal throughout. Do not use play count.
- Artist URIs are the reliable unique identifier for artists — names can have minor variations across tracks.
- The `name` field in the raw data is a concatenated string containing the full track metadata. Parse it by splitting on `\t# Track:` — the right side is the human-readable metadata block. Write a robust parser for this format before doing anything else.
- Some tracks have no descriptors — handle gracefully, assign `unknown` and exclude from genre clustering but keep in temporal analysis.
- For the network graph, apply a minimum edge weight threshold (e.g. 60 seconds) to prune noise — listening to 10 seconds of a track is not a real signal.

---

## Deliverables

1. `parse.py` — data loading, cleaning, feature engineering. Outputs a clean `tracks.csv` and `artists.csv`.
2. `graph.py` — builds and serializes the taste network. Outputs `taste_graph.graphml` and `taste_graph.html` (pyvis).
3. `temporal.py` — temporal analysis and charts.
4. `producers.py` — producer/composer network and ranked table.
5. `similarity.py` — similarity matrix and "more like this" function.
6. `dashboard.py` — assembles everything into the interactive dashboard.
7. `README.md` — how to install deps and run each script.

Start with `parse.py`. Get the data clean and validated before building anything else. Print a summary at the end: total tracks, unique artists, unique descriptors, date range of recent plays, top 5 tracks by played_seconds.

---

## Phase 8: Full Streaming History Integration (Spotify Data Export)

This phase upgrades the project from cumulative totals to a true longitudinal taste model — adding real time to the x-axis. It requires your full Spotify streaming history, which you can request from [spotify.com/account/privacy](https://www.spotify.com/account/privacy). The export arrives as one or more JSON files named `StreamingHistory_music_0.json`, `StreamingHistory_music_1.json`, etc.

### 8a. Parse the Export

Each entry in the streaming history has this shape:
```json
{
  "ts": "2024-03-15T14:22:11Z",
  "ms_played": 187432,
  "master_metadata_track_name": "Oklahoma Smokeshow",
  "master_metadata_album_artist_name": "Zach Bryan",
  "master_metadata_album_album_name": "American Heartbreak",
  "spotify_track_uri": "spotify:track:0OWhKvvsHptt6vnnNUSM9a",
  "reason_start": "trackdone",
  "reason_end": "trackdone",
  "shuffle": false,
  "skipped": false
}
```

Load all `StreamingHistory_music_*.json` files and concatenate into a single DataFrame. Key engineering steps:

- Parse `ts` as a timezone-aware datetime
- Derive: `year`, `month`, `week`, `day_of_week`, `hour`, `date`
- Convert `ms_played` to `seconds_played`
- Flag **skip events**: `skipped == true` OR `seconds_played < 30` — these are negative engagement signals
- Flag **deep listens**: `seconds_played > 0.8 * track_duration` — requires enriching with track duration from `spotify_data.json` where available
- Join on `spotify_track_uri` to attach descriptor/mood/producer metadata from `spotify_data.json` for any matching tracks

### 8b. Longitudinal Taste Model

With exact timestamps, you can reconstruct taste as a time series rather than a static snapshot.

**Yearly genre fingerprint**: for each calendar year, compute the share of `seconds_played` per `macro_genre`. Plot as a stacked area chart — this shows how your taste has shifted year over year. Normalize within each year so the chart shows proportion, not volume.

**Taste drift vector**: represent each month as a genre distribution vector (length = number of macro genres, values = share of seconds_played). Compute cosine distance between consecutive months. High distance = taste shift; low distance = stable period. Plot the drift curve over time — spikes indicate when your listening changed significantly.

**Artist lifecycle**: for each artist in your top tracks, plot their monthly `seconds_played` over time. Classify into patterns:
- *Discovery spike*: sharp increase followed by gradual decay (normal new-artist behavior)
- *Perennial*: consistent play across years
- *Revival*: gap in listening followed by a return
- *One-season*: heavy play in one period, then absent

**Seasonal patterns**: aggregate by month across all years. Do you listen to more melancholy music in winter? More country in summer? Group by `macro_genre` × `month` and look for seasonal clustering.

### 8c. Epicure-Style Taste Topology

Inspired by Epicure's flavour graph approach — mapping relationships into navigable space rather than simple rankings — build a taste topology from your streaming history:

**Listening session reconstruction**: group consecutive plays within a 30-minute window into "sessions." Sessions are the equivalent of Epicure's recipes — the unit in which your tracks co-occur. Two tracks in the same session are "paired."

**Track co-occurrence matrix**: build a weighted matrix where `M[i][j]` = number of sessions in which track i and track j both appeared. This is your playlist co-occurrence graph, analogous to how Epicure uses recipe co-occurrence for ingredients.

**Session embedding**: represent each session as the average of its constituent track descriptor vectors. Cluster sessions with k-means or HDBSCAN — these are your "listening modes" (e.g., late-night melancholy, high-energy country, focused rap).

**UMAP projection**: reduce the track embedding space to 3D using UMAP (or 2D for simpler visualization). Plot with `plotly` — colored by `macro_genre`, sized by total `seconds_played`, labeled on hover with track name and top descriptor. This is your personal ingredient atlas equivalent: a navigable map of your musical possibility space.

**Taste compass**: for each listening session cluster, compute the centroid descriptor vector and visualize as a radar/spider chart with axes for: energy (inferred from descriptors like "club", "electronic", "trap" vs. "calm", "acoustic", "cozy"), mood valence (positive: "romantic", "love" vs. negative: "sad", "melancholy"), era (modern vs. classic), and genre spread (how many macro genres appear). This is the music equivalent of Epicure's flavour direction compass.

### 8d. Discovery Engine (History-Grounded)

With full history, the "more like this" engine becomes much stronger:

**Anti-recommendation filter**: tracks you've played heavily and then stopped playing (high historical `seconds_played`, zero plays in last 6 months) signal taste drift. Exclude these from recommendations even if they score high on similarity to current taste.

**Gap detector with history**: identify descriptor clusters that appear in your current listening but have no historical depth — these are genuine emerging interests worth exploring. Flag them as high-priority discovery targets.

**Mood-time matching**: given a time of day and day of week, look up your historical listening patterns for that slot, identify the dominant mood cluster, and surface tracks matching that mood that you haven't played recently. This is the music equivalent of Epicure's context-aware pairing: the right track for the moment, not just the abstract favorite.

### 8e. Updated Dashboard Tab

Add a **Taste Timeline** tab to the dashboard (Phase 7):

- Stacked area chart: genre share by year
- Drift curve: cosine distance between consecutive months
- Artist lifecycle viewer: pick an artist from a dropdown, see their play history plotted over time
- UMAP 3D projection: interactive, with session cluster coloring toggle
- Taste compass: radar chart for the currently selected session cluster

### Implementation Notes for Phase 8

- The streaming history can be large (100k+ rows for heavy listeners). Use chunked loading and avoid loading everything into memory at once if performance degrades.
- `reason_end: "endplay"` with high `ms_played` is your strongest positive signal. `reason_end: "fwdbtn"` (forward button) is the clearest skip signal — weight these differently in engagement scoring.
- Not all streaming history entries will have a matching URI in `spotify_data.json` — many historical tracks won't have descriptor metadata. Handle gracefully: use them for temporal/volume analysis but exclude from descriptor-based clustering.
- The session reconstruction window (30 minutes) is a parameter worth tuning — try 20 and 45 minutes and compare the resulting session clusters.
- UMAP requires `umap-learn` (`pip install umap-learn`). For the 3D plot, use `plotly.express.scatter_3d` with `hover_data` set to track name, artist, and top descriptor.
