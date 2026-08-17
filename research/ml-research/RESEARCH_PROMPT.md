# Music Recommendation Systems — Independent Research Guide

## About Me

I have a master's degree in mathematics and am pursuing a career in data science. I want to use music recommendation systems — specifically Spotify's publicly documented architecture — as a vehicle for deep, rigorous self-study. I'm comfortable with linear algebra, probability theory, and mathematical optimization. I want to go beyond surface-level tutorials and engage with the actual mathematics and research literature.

Help me build a structured research curriculum across the following topic areas. For each topic:
- Explain the mathematical foundations at a graduate level
- Point me to the key papers (with authors and approximate year so I can find them)
- Suggest concrete implementation exercises I can do in Python
- Identify open research questions I could pursue as independent projects

---

## Topic 1: Matrix Factorization & Implicit Feedback (Collaborative Filtering)

The foundation of Spotify's recommendation engine. The canonical paper is Hu, Koren & Volinsky (2008) — "Collaborative Filtering for Implicit Feedback Datasets."

Guide me through:
- The mathematical formulation of implicit ALS: the weighted least squares objective, confidence weights c_ui, the alternating optimization procedure
- Why implicit feedback (plays, skips) requires different treatment than explicit ratings — the missing data problem
- The closed-form ALS update equations and their derivation
- Computational complexity and why the user/item factor structure makes this tractable at Spotify scale (millions of users × millions of tracks)
- The connection to SVD and PCA — what does matrix factorization actually learn?
- Extensions: BPR (Bayesian Personalized Ranking), LightFM (hybrid MF with side features)

Implementation exercise: build implicit ALS from scratch in NumPy on the Last.fm or Million Song Dataset. Then use the `implicit` Python library to scale it. Compare learned embeddings against audio feature similarity.

---

## Topic 2: Word2Vec Applied to Music (Track2Vec / Playlist2Vec)

Spotify applied NLP embedding techniques to playlist co-occurrence data — treating playlists as "sentences" and tracks as "words." This was documented in their RecSys 2018 challenge work and internal engineering posts.

Guide me through:
- The Word2Vec objective (skip-gram with negative sampling) — the mathematical derivation of the noise-contrastive loss
- Why playlist co-occurrence is analogous to linguistic context windows
- The connection to pointwise mutual information (PMI) and why Word2Vec implicitly factorizes a shifted PMI matrix (Levy & Goldberg, 2014)
- How learned track embeddings encode cultural relatedness rather than acoustic similarity — and why that matters
- Extensions: Doc2Vec for playlist-level embeddings, fastText for handling new/rare tracks

Implementation exercise: train track embeddings on the Spotify Million Playlist Dataset (MPD). Visualize the embedding space with UMAP. Identify nearest neighbors for tracks across genres — does it recover meaningful structure?

---

## Topic 3: Audio-Based Representation Learning (Cold-Start)

For new tracks with no listening history, Spotify estimates collaborative filtering embeddings from raw audio. The architecture involves CNNs trained on mel spectrograms.

Guide me through:
- Mel spectrograms: the signal processing pipeline from raw audio → STFT → mel filterbank → log compression. The mathematics of the Fourier transform and why the mel scale maps to human perception.
- CNN architectures for audio: how 2D convolutions over time-frequency representations capture local spectral patterns
- The training objective: predicting the collaborative filtering embedding from audio features (regression on latent factors learned in Topic 1) — this is the "two-tower" or "content-cold-start" formulation
- Transfer learning: pre-trained audio models (VGGish, OpenL3, MusicFM) and when to use them vs. training from scratch
- The gap between acoustic similarity and cultural relatedness — why audio models alone underperform collaborative filtering

Implementation exercise: use `librosa` to extract mel spectrograms from audio clips (use the Free Music Archive or MagnaTagATune datasets). Train a small CNN to predict genre tags, then extend it to predict mock collaborative filtering embeddings.

---

## Topic 4: Contextual Bandits — BaRT (Exploration vs. Exploitation)

Spotify published their BaRT framework (Bandits for Recommendations as Treatments) for balancing showing users familiar content vs. exploring new recommendations. This is a core tension in any live recommendation system.

Guide me through:
- The multi-armed bandit formulation — regret minimization, the explore-exploit tradeoff
- Upper Confidence Bound (UCB) algorithms and their regret bounds
- Thompson Sampling — the Bayesian approach, posterior updates, and why it often outperforms UCB in practice
- Contextual bandits: LinUCB and its closed-form confidence ellipsoids. The linear algebra behind the update rule.
- The causal framing in BaRT: recommendations as interventions, counterfactual evaluation, inverse propensity scoring (IPS)
- Off-policy evaluation: how do you measure the quality of a new recommendation policy without deploying it?

Key papers: Li et al. (2010) "A Contextual-Bandit Approach to Personalized News Article Recommendation," Swaminathan & Joachims (2015) on counterfactual risk minimization.

Implementation exercise: implement LinUCB on a simulated music recommendation environment. Use logged data from the MIND or Yahoo! R6B dataset to practice off-policy evaluation. Compare Thompson Sampling vs. UCB regret curves.

---

## Topic 5: Graph Neural Networks for Music (Emerging Direction)

The natural extension of track2vec and collaborative filtering is to model the full user-track-artist-playlist graph with GNNs. This is where the research frontier is moving.

Guide me through:
- Graph representation of the Spotify data model: users, tracks, artists, playlists as nodes; plays, follows, co-occurrence as edges
- Message passing neural networks (MPNN) — the mathematical aggregation framework
- GraphSAGE, GAT (Graph Attention Networks), and LightGCN — compare their inductive biases and computational costs
- PinSage (Pinterest / relevant to Spotify scale): random-walk sampling for mini-batch GNN training on billion-node graphs
- How GNNs unify collaborative filtering (structure) and content features (node attributes) in one model
- Cold-start in GNNs: how graph structure helps new nodes bootstrap embeddings faster than pure CF

Key papers: Hamilton et al. (2017) GraphSAGE, Velickovic et al. (2018) GAT, He et al. (2020) LightGCN, Ying et al. (2018) PinSage.

Implementation exercise: build a bipartite user-track graph from your own Spotify data (exported in spotify_data.json). Use PyTorch Geometric to train a LightGCN model for link prediction — predicting which tracks a user will play next. Evaluate with NDCG@10.

---

## Topic 6: Evaluation Metrics — The Mathematics of "Good" Recommendations

Understanding how to measure recommendation quality rigorously is often overlooked but mathematically rich.

Guide me through:
- Precision@K, Recall@K, F1@K — and why they are insufficient for ranked lists
- NDCG (Normalized Discounted Cumulative Gain) — the logarithmic discount derivation and why it captures position sensitivity
- Mean Average Precision (MAP) — the area-under-precision-recall-curve interpretation
- Beyond accuracy: diversity, novelty, serendipity — formal definitions and why Spotify cares about them (the filter bubble problem)
- A/B testing at scale: statistical power, multiple testing correction, network effects in social recommendation systems
- The feedback loop problem: how optimizing for engagement metrics can degrade long-term user satisfaction

Implementation exercise: implement NDCG@K, MAP, and a diversity metric (intra-list distance using track embeddings) from scratch. Apply them to evaluate the output of your ALS and track2vec models from Topics 1 and 2.

---

## Suggested Study Order

1. Topic 1 (ALS) — the mathematical core, most foundational
2. Topic 2 (Track2Vec) — connects NLP literature to music, fast to implement
3. Topic 6 (Evaluation) — do this early so you can measure everything you build
4. Topic 3 (Audio CNNs) — requires signal processing background, more implementation-heavy
5. Topic 4 (Bandits) — excellent for understanding production system design
6. Topic 5 (GNNs) — most mathematically demanding, best tackled last

---

## Datasets to Use

- **Spotify Million Playlist Dataset (MPD)** — 1M playlists, 66M track-playlist pairs. Best for Topics 1 and 2.
- **Free Music Archive (FMA)** — audio files with metadata. Best for Topic 3.
- **Last.fm Dataset** — user listening histories. Good for Topics 1 and 6.
- **MIND Dataset (Microsoft News)** — good for bandit evaluation (Topic 4) in absence of a music equivalent.
- **Your own Spotify data** (`spotify_data.json`) — use for Topic 5 GNN exercise as a small personal graph.

---

## Independent Research Angles

These are genuine open problems worth pursuing:

1. **Cross-genre embedding alignment**: do track embeddings learned from playlist co-occurrence align with embeddings learned from audio features? When do they agree, when do they diverge, and what does that tell you about cultural vs. acoustic taste?

2. **Temporal drift in taste**: collaborative filtering assumes static preferences. How do you model taste as a time series? Extensions: recurrent CF, time-aware BPR, Hawkes process models of listening events.

3. **Fairness in music recommendation**: do popularity-biased systems systematically under-recommend independent artists? Can you formalize and measure this with your own data?

4. **Cold-start with LLMs**: can you use a track's lyrics, artist biography, or press text — embedded with a language model — to bootstrap CF embeddings better than audio CNNs alone?

Each of these is small enough to be a rigorous independent project, publishable at a workshop level if executed well.
