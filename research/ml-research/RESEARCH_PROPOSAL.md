# Research Proposal: Taste Has a Topology
## Formalizing a Music Analog to FlavorGraph and Cross-Domain Taste Graph Alignment

---

## Preliminary Literature Review

### What exists — and the gap

The research landscape splits into three adjacent bodies of work that have not been formally unified:

**Food flavor graphs**
FlavorGraph (Park et al., 2021, *Scientific Reports*) is the most rigorous existing work — a large-scale graph built from 1M+ recipes and chemical compound data, learning ingredient embeddings that capture both co-occurrence and molecular affinity. Epicure (2026) applies this to a consumer product. Earlier, Ahn et al. (2011) established the foundational "flavor network" hypothesis: that ingredients sharing flavor compounds are more likely to co-occur in Western cuisines. Both treat co-occurrence as intentional and curated.

**Music co-occurrence and session graphs**
Cano & Koppenberger (2004, arXiv) studied the topology of music recommendation networks and found small-world properties. More recently, unsupervised graph embeddings for session-based recommendation (arXiv, 2025) formalize item co-occurrence graphs from listening sessions as the basis for embedding learning. Track2Vec / playlist-based embeddings (Spotify, RecSys 2018) are the production-scale version. Critically, music session co-occurrence is behavioral and partly unintentional — the co-occurrence signal is noisier and differently structured than recipe co-occurrence.

**Cross-modal taste-music perception**
A separate body of psychoacoustics research — "sonic seasoning" — shows that music systematically shifts food perception: sweetness, bitterness, and valence interact across modalities (ScienceDirect, 2024). This is sensory science, not recommender systems, but it provides empirical grounding for the hypothesis that food and music taste are not independent.

**The gap**
Two distinct gaps, both open:

First, FlavorGraph's specific architectural design — fusing a chemical compound feature layer with a behavioral co-occurrence layer into unified embeddings — has not been formally replicated in music. Spotify Research has the components (audio features, session co-occurrence graphs) but has not combined them in the FlavorGraph formulation. This is the music-analog gap.

Second, no published work formally models the structural relationship between a food taste graph and a music taste graph at the individual user level, compares their topological properties, or attempts cross-domain embedding alignment between the two. The cross-modal perception literature and the recommender systems literature have not been connected. This is the cross-domain gap.

---

## Research Questions

**Primary (Contribution 1 — Music FlavorGraph):** Can FlavorGraph's fusion architecture — combining a ground-truth feature layer with behavioral co-occurrence — be formally replicated in music using audio features as the molecular analog, and does the resulting music taste graph share the topological properties (scale-free degree distribution, small-world clustering, meaningful community structure) observed in the food flavor network?

**Primary (Contribution 2 — Cross-Domain):** Are personal food and music taste graphs topologically similar at the individual level, and can a shared latent embedding space be learned that aligns the two?

**Secondary:** Do users with structurally adventurous food taste graphs (high cross-cultural co-occurrence, high ingredient diversity) exhibit correspondingly adventurous music taste graphs (high cross-genre co-occurrence, low descriptor concentration)?

---

## Motivation and Novelty

The novelty is two-layered, which makes this a stronger paper than either contribution alone:

**Contribution 1 — Music FlavorGraph formalization.** FlavorGraph's design is elegant: a bipartite graph of ingredients and flavor compounds, projected into a unipartite ingredient co-occurrence graph, with compound vectors as node features fused into the embedding. The music analog is: a bipartite graph of tracks and audio features (valence, energy, acousticness, danceability, tempo as "compound" equivalents), projected into a track co-occurrence graph from listening sessions, with audio feature vectors fused into the embedding. This has not been published as a formal replication/analog. Establishing it is Contribution 1 — modest but necessary groundwork.

**Contribution 2 — Cross-domain alignment.** Once both graphs exist in comparable embedding spaces, the cross-domain question becomes tractable: do they share topological structure, and can a user's position in one space predict their position in the other? The psychoacoustics "sonic seasoning" literature provides theoretical grounding (music and food perception are not independent modalities), but no computational formalization exists. This is the novel contribution.

---

## Methodology

### Phase 1 — Build Both Graphs

**Music taste graph**: constructed from personal Spotify streaming history (full export). Nodes = tracks + descriptors + artists. Edges = session co-occurrence (tracks appearing within 30-minute listening sessions), weighted by frequency and `seconds_played`. Node features = Spotify audio features (valence, energy, acousticness, danceability, tempo) + semantic descriptor tags.

**Food taste graph**: constructed from Epicure's FlavorGraph research data (open on GitHub) filtered to a personal preference subset, or from a user's recipe interaction history if available. Nodes = ingredients + flavor categories. Edges = recipe co-occurrence, weighted by frequency. Node features = chemical compound vectors from FlavorGraph.

### Phase 2 — Topological Comparison

For both graphs, compute:
- Degree distribution — does it follow a power law? (Ahn et al. found scale-free structure in flavor networks)
- Clustering coefficient — how tightly clustered are genre/flavor neighborhoods?
- Community structure — Louvain algorithm on both; compare number, size, and cohesion of communities
- Betweenness centrality — which nodes (tracks / ingredients) serve as bridges across communities? These are the "cross-domain taste connectors"
- Small-world coefficient — both networks are hypothesized to have small-world structure; measure and compare

Null hypothesis: the topological statistics of a personal food taste graph and a personal music taste graph are drawn from the same distribution. Reject or fail to reject using permutation testing.

### Phase 3 — Embedding Alignment

Independently train graph embeddings for both graphs (GraphSAGE or LightGCN). Then attempt alignment via:
- **Canonical Correlation Analysis (CCA)**: find linear projections of both embedding spaces that are maximally correlated. This is the simplest baseline.
- **Adversarial domain alignment**: train a discriminator to distinguish food embeddings from music embeddings; the generator learns a shared space where the two are indistinguishable (GAN-style, analogous to domain adaptation literature).
- **Contrastive alignment**: if the user has both food and music preferences, use pairs of (food item liked, music track liked) as positive pairs and train with a contrastive loss (SimCLR-style).

Evaluation: after alignment, does the position of a food node in the shared space predict nearby music nodes that the user actually engages with? Measure with Precision@K and NDCG@K.

### Phase 4 — Taste Compass Comparison

Operationalize the Epicure "flavour compass" (bright / aromatic / deep / sweet / umami) and construct a music equivalent using Spotify audio features + descriptors:
- **Bright** ↔ high valence + high energy
- **Aromatic** ↔ high acousticness + folk/indie descriptors
- **Deep** ↔ low tempo + melancholy/soul descriptors
- **Sweet** ↔ romantic/love descriptors + high danceability
- **Umami** ↔ genre-bridging tracks (high betweenness centrality in the music graph)

For a set of users (or a single user across time windows), plot both compasses and measure correlation between axes. Does high "umami" in food (ingredient bridging) predict high "umami" in music (cross-genre bridging)?

---

## Datasets

| Dataset | Use |
|---------|-----|
| Personal Spotify streaming history (full export) | Music taste graph construction |
| FlavorGraph (GitHub, open) | Food flavor graph and ingredient embeddings |
| Epicure ingredient co-occurrence (if accessible via MCP) | Food behavioral co-occurrence |
| Spotify Web API audio features | Node features for music graph |
| Million Playlist Dataset (optional) | Broader music co-occurrence baseline |

---

## Expected Contributions

1. **MusicGraph**: the first formal replication of FlavorGraph's fusion architecture in the music domain, using audio features as the molecular analog and listening sessions as the recipe analog
2. **Topological comparison**: empirical evidence for (or against) structural similarity between food and music taste graphs at the individual level
3. **Cross-domain alignment**: a methodology and baseline result for learning a shared embedding space across food and music taste
4. **Open framework**: reusable code for building personal taste graphs from Spotify streaming history export, open-sourced alongside the paper

---

## Scope and Limitations

This is an explicitly proof-of-concept study. The following limitations are acknowledged upfront and should be foregrounded in any submission rather than buried:

**Single-subject data.** The music taste graph is built from one user's Spotify streaming history. This is intentional for a proof-of-concept — the goal is to establish that the methodology is feasible and the graphs have meaningful structure, not to make population-level claims. Generalizability is deferred to future work. Any topological findings should be framed as "consistent with" rather than "demonstrating" broader patterns.

**No personal food behavioral signal.** FlavorGraph is a population-level graph. There is no equivalent personal food streaming history. The cross-domain comparison therefore uses a population food graph filtered by personal affinity (ingredient preferences, cuisine preferences) as a proxy for a personal food taste graph. This is a known asymmetry — the music graph is behaviorally grounded while the food graph is preference-grounded. Acknowledge this explicitly and treat it as a limitation that motivates future work with richer food interaction data (e.g., recipe app logs, grocery purchase history).

**Audio features as approximate molecular analog.** Spotify's audio features (valence, energy, acousticness, danceability, tempo) are model outputs with known biases, not objective ground truth. They are used here as the best available approximation of an "objective" feature layer analogous to chemical compounds in FlavorGraph. A one-paragraph theoretical justification is included in the methodology — both are continuous feature vectors that capture latent properties of the item independent of user behavior — but this remains an approximation. Future work could use raw audio embeddings (VGGish, MusicFM) as a less model-dependent alternative.

**Evaluation is qualitative and structural.** For a proof-of-concept, evaluation focuses on whether the graphs have the expected topological properties (scale-free degree distribution, small-world clustering, meaningful community structure) rather than downstream recommendation performance. A minimal held-out evaluation is included (see Phase 2) but should not be over-interpreted given the single-subject data constraint.

---

## Evaluation (Proof-of-Concept Standard)

Given the single-subject, proof-of-concept scope, evaluation targets structural validity rather than production-quality recommendation performance:

**Contribution 1 (MusicGraph):**
- Degree distribution: fit a power law and report the exponent. Compare to Ahn et al.'s flavor network result (~2.3) and prior music network topology results.
- Community structure: run Louvain on MusicGraph. Do the resulting communities correspond to recognizable genre/mood clusters? Evaluate qualitatively by inspecting the top 5 tracks per community.
- Held-out track prediction: hold out the most recent 10% of streaming history by date. Does MusicGraph-based nearest-neighbor retrieval recover held-out tracks at a higher rate than a descriptor-only baseline? Report Precision@10.

**Contribution 2 (Cross-Domain):**
- Topological statistics: compute and report degree distribution, clustering coefficient, and average path length for both graphs. Are they in the same ballpark? Permutation test against a random graph null model.
- CCA alignment: report the top-5 canonical correlations between food and music embedding spaces. Are any statistically significant? This is the minimum viable cross-domain result.
- Qualitative inspection: for 5 food ingredient nodes, retrieve the nearest music track nodes in the aligned space. Do the retrieved tracks make intuitive sense given the ingredient's flavor profile? This is proof-of-concept evidence, not a rigorous metric.

---

## Ethics and Data

All music data used in this study is drawn from the author's own Spotify account via the official data export (GDPR-compliant, available at spotify.com/account/privacy). No third-party user data is collected or used. Food graph data is drawn from the publicly available FlavorGraph dataset (Park et al., 2021, MIT License). No human subjects research is involved beyond the author's own data. A brief ethics statement to this effect should be included in any submission.

---

## Positioning and Venue

**Primary venue**: ACM RecSys workshop (RecSys Cross-Domain Recommendation or RecSys Perspectives workshops). The personal-data framing and methodological novelty are well-suited to a workshop paper (8–10 pages) before a full venue submission.

**Secondary venue**: if the cross-modal alignment result is strong, the work could extend to SIGIR or WWW as a full paper under "cross-domain recommendation" or "user modeling."

**Framing to avoid**: do not frame this as "Spotify meets food" — that reads as novelty-for-novelty's-sake. Frame it as a rigorous study of whether taste is a domain-general latent structure that manifests in predictable graph topologies across modalities. The math-first framing will land better with reviewers given your background.

---

## Next Steps

1. Request full Spotify streaming history export (spotify.com/account/privacy — allow up to 30 days)
2. Clone FlavorGraph repository and inspect the ingredient embedding format
3. Run Phase 1 of the Claude Code taste graph project — this is already scaffolded in `PROMPT.md`
4. Once both graphs are built, run topological comparison (Phase 2) — this is the lowest-risk result and publishable on its own even if alignment fails
5. Draft a 2-page abstract for a RecSys workshop CFP

The topological comparison (Phase 2) alone — if it shows that personal taste graphs across food and music share structural properties — is a publishable finding. The alignment work (Phase 3) is the higher-risk, higher-reward contribution. Pursue both in parallel but treat Phase 2 as the minimum viable result.
