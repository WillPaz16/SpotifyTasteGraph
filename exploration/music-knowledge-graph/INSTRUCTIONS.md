# Music Knowledge Graph — Instructions & Requirements

*Governing document for MUSIC_GRAPH.md and music_graph.json*
*Written August 2026. Update this file whenever requirements change.*

---

## Purpose

This knowledge graph exists to do five things:

1. **Drive playlist creation** — Kit uses it to make better picks. When building a playlist, Kit checks this graph first: what artists has Will responded to, what's in the single-listen category, what edges exist between the requested vibe and known artists, what's been overplayed.
2. **Track next listening directions** — every conversation produces leads. This graph captures them with priority and context so they don't get lost across sessions.
3. **Carry story and context** — so Kit doesn't have to re-explain who Tim Buckley is, or that Will already knows Caetano Veloso is powerful but not for repeat. Context persists here, not in conversation memory alone.
4. **Feed Claude Code** — the JSON file is designed to be dropped into the same Claude Code project as `spotify_data.json`. It becomes the semantic and historical layer that listening data alone can't provide.
5. **Be updated conversationally** — Will tells Kit something new, Kit updates both files in the same response. No separate step required.

---

## Update Protocol

### When to update

Kit updates the graph whenever any of the following happen in conversation:
- Will gives feedback on a track, artist, or playlist ("I loved X", "single-listen for Y", "Z didn't land")
- A new artist, album, or genre is introduced and discussed
- A new playlist is created
- A new next direction is identified or prioritized
- A cultural connection is made ("I connected Diablo Rojo to Marlboro Rojo")
- Will asks for a refresh, correction, or addition

### What to update

Both files, always. `MUSIC_GRAPH.md` and `music_graph.json` must stay in sync. Never update one without the other.

### How to update

- **New artist**: add a full node to both files — genres, era, nationality, key tracks, key albums, will_response, playlists, story, connections
- **New response signal**: update `will_response` on the relevant artist node. Use consistent vocabulary (see below).
- **New playlist**: add to the playlist registry in both files with Spotify URI and artist nodes
- **New next direction**: add to `next_directions` in JSON and `## Next Directions` in Markdown with priority and context note
- **New edge**: add to `edges` array in JSON and the `Connections` section of the relevant artist in Markdown
- **New genre or concept**: add a full node with description, era, key artists, will_response

### Will response vocabulary (use consistently)

| Label | Meaning |
|-------|---------|
| `seed_artist` | The artist that started an entire thread of exploration |
| `highlight` | Explicit favorite — Will called it out as a standout |
| `loved` | Strong positive response, clearly enjoyed |
| `liked` | Positive, enjoyed it, no specific callout |
| `currently_listening` | Actively in rotation right now |
| `anchor` | Key track in a playlist, structural importance |
| `appreciated` | Noticed and valued, not necessarily emotional |
| `single-listen` | Powerful but not for repeat — intellectually interesting more than emotionally |
| `interested` | Wants to explore further, hasn't heard yet |
| `next_step` | Specifically flagged as the next thing to listen to |
| `not_yet_heard` | On the radar but not yet listened to |
| `did_not_land` | Tried it, didn't connect |

---

## Playlist Creation Rules

When Kit uses this graph to build a playlist, the following apply:

### Must check before sourcing tracks
- `will_response` on all candidate artists — never put a `single-listen` or `did_not_land` artist in a playlist without flagging it
- `next_directions` — if the playlist theme overlaps with a next direction, use that as an anchor artist
- `playlists` field on artists — don't over-rotate the same artist across multiple playlists unless the request is specifically about them

### Graph-informed curation
- Use `edges` to find adjacent artists the graph already knows — prefer known-good adjacency over cold search results
- Use `bridges_to` edges to sequence genre transitions within a playlist
- Use `sounds_like` edges to find safe adjacent picks when a core artist has limited Spotify catalog

### Discovery blend target
- Roughly 60% artists already in the graph with `liked` or better response
- Roughly 40% new artists not yet in the graph — these become candidates for new nodes after Will hears them

### After every playlist is built
- Add the new playlist to the registry in both files
- Note which artists appeared — these are data points for future `will_response` updates once Will has heard it

---

## Claude Code Integration

The `music_graph.json` file is designed to be dropped into the same Claude Code project as `spotify_data.json`. Instructions for integration:

### What the JSON provides that `spotify_data.json` does not
- Semantic relationships between artists (influenced_by, sounds_like, collaborated_with)
- Cultural and historical context (story fields)
- Will's personal response signals (`will_response`) beyond raw play counts
- Genre and concept nodes with descriptions
- Discovery path edges — how Will got to each artist
- Next directions with priority

### Suggested Claude Code use cases
- **Graph visualization**: render the `edges` array as a network graph — nodes colored by `will_response`, edges styled by type
- **Playlist scoring**: weight candidate tracks by graph distance from `highlight` and `loved` nodes
- **Discovery gap analysis**: find high-play artists in `spotify_data.json` with no node in `music_graph.json` — these are known artists without semantic context yet
- **Lineage tracing**: follow `influenced_by` chains to surface ancestors of artists Will already loves
- **Next directions prioritization**: combine `next_directions` priority with play count data from `spotify_data.json` to rank what to explore next

### Schema notes
- `nodes.artists[].spotify_uri` — verified Spotify URIs for direct catalog lookup
- `edges[].type` — valid types: `influenced_by`, `influenced`, `sounds_like`, `collaborated_with`, `bridges_to`, `part_of`, `discovery_path`, `family_connection`
- `playlists[].spotify_uri` — verified Spotify playlist URIs
- `next_directions[].priority` — values: `high`, `medium`, `low`

---

## What This Graph Is Not

- **Not a comprehensive music database** — it only contains artists Will has encountered or expressed interest in. Gaps are intentional.
- **Not a replacement for conversation** — the graph is a memory aid and a data layer, not a substitute for the back-and-forth that makes playlist creation good. Kit still asks questions, still pitches ideas, still tells stories.
- **Not static** — it should grow every session. If a conversation adds no new nodes or edges, something is being missed.
- **Not prescriptive** — `next_directions` are leads, not a queue. Will listens when he wants, to what he wants.

---

## File Locations

```
/artifacts/music-knowledge-graph/
├── INSTRUCTIONS.md       ← this file
├── MUSIC_GRAPH.md        ← human-readable graph with stories and context
└── music_graph.json      ← machine-readable graph for Claude Code
```

All three files travel together. If you copy the directory to another project, copy all three.
