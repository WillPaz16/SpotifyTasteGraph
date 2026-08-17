"""Phase 2 of the FlavorGraph reformulation (see FLAVORGRAPH_PLAN.md Part III).

Builds a heterogeneous artist/tag graph from the crawled universe
(data/universe/universe.json), trains metapath-constrained random walks
(A-A-A interleaved with A-T-A, the direct analog of FlavorGraph's
ingredient->compound->ingredient metapath) into a gensim Word2Vec skip-gram
model, and projects the resulting embeddings to 2D with UMAP.

Also runs the 5 falsifiable verification checks from the plan and reports
every number, including ones that don't flatter the result:
  1. Degree distribution power-law fit (KS goodness-of-fit via `powerlaw`)
  2. Held-out link prediction AUC vs a preferential-attachment baseline
  3. Known-lineage sanity check (Nick Drake / Bert Jansch / John Martyn /
     Tim Buckley should be mutual near-neighbours)
  4. Personal-coherence silhouette score (library artists vs random subset)
  5. Zero isolated nodes in the crawled A-A graph

Walk/embedding hyperparameters (WALKS_PER_NODE=8, WALK_LENGTH=40,
EMBED_DIM=128) are a practical CPU-minutes budget for ~15K nodes, not taken
from the metapath2vec paper's larger-corpus defaults.
"""
import json
import os
import random

import numpy as np
from gensim.models import Word2Vec
from sklearn.metrics import roc_auc_score, silhouette_score
import umap
import powerlaw

from parse import load_tracks

UNIVERSE_PATH = "data/universe/universe.json"
ARTIST_CACHE_PATH = "data/artists.json"
OUTPUT_DIR = "data/universe"

EMBED_DIM = 128
WALK_LENGTH = 40
WALKS_PER_NODE = 8
P_TAG_HOP = 0.4          # probability of an A-T-A hop at each step vs A-A
WINDOW = 5
MIN_COUNT = 1
NEGATIVE = 10
EPOCHS = 5
SEED = 42
HELD_OUT_FRACTION = 0.10
TOP_N_NEIGHBORS = 20      # for the lineage sanity check


def artist_tok(name):
    return f"artist::{name}"


def tag_tok(name):
    return f"tag::{name}"


def load_universe():
    with open(UNIVERSE_PATH) as f:
        return json.load(f)


def build_adjacency(universe, exclude_edges=None):
    """Undirected artist-artist adjacency (weighted by Last.fm match) and
    artist->tag / tag->artist bipartite indexes, restricted to the crawled
    universe (edges pointing outside the 15K-artist universe are dropped —
    we have no neighbor list for those, so they'd be walk dead-ends).

    exclude_edges: optional set of frozenset({a, b}) pairs to leave out of
    the artist-artist graph, used to build the held-out training graph for
    the link-prediction check.
    """
    exclude_edges = exclude_edges or set()
    names = set(universe.keys())
    adj = {n: {} for n in names}  # name -> {neighbor: weight}
    artist_tags = {}
    tag_artists = {}

    for name, entry in universe.items():
        artist_tags[name] = entry.get("tags", [])
        for tag in entry.get("tags", []):
            tag_artists.setdefault(tag, []).append(name)
        for sim in entry.get("similar", []):
            other = sim["name"]
            if other not in names or other == name:
                continue
            if frozenset((name, other)) in exclude_edges:
                continue
            w = sim["match"]
            # keep the max match if seen from both directions
            adj[name][other] = max(adj[name].get(other, 0), w)
            adj[other][name] = max(adj[other].get(name, 0), w)

    return adj, artist_tags, tag_artists


def all_edges(adj):
    """Deduplicated undirected edge list [(a, b, weight), ...]."""
    seen = set()
    edges = []
    for a, neighbors in adj.items():
        for b, w in neighbors.items():
            key = frozenset((a, b))
            if key in seen:
                continue
            seen.add(key)
            edges.append((a, b, w))
    return edges


def generate_walk(start, adj, artist_tags, tag_artists, rng):
    walk = [artist_tok(start)]
    current = start
    for _ in range(WALK_LENGTH - 1):
        took_tag_hop = False
        if rng.random() < P_TAG_HOP and artist_tags.get(current):
            tag = rng.choice(artist_tags[current])
            candidates = [a for a in tag_artists.get(tag, []) if a != current]
            if candidates:
                nxt = rng.choice(candidates)
                walk.append(tag_tok(tag))
                walk.append(artist_tok(nxt))
                current = nxt
                took_tag_hop = True
        if not took_tag_hop:
            neighbors = adj.get(current)
            if not neighbors:
                break
            items = list(neighbors.items())
            names_, weights_ = zip(*items)
            nxt = rng.choices(names_, weights=weights_, k=1)[0]
            walk.append(artist_tok(nxt))
            current = nxt
    return walk


def build_walk_corpus(adj, artist_tags, tag_artists, seed=SEED):
    rng = random.Random(seed)
    nodes = list(adj.keys())
    corpus = []
    for _ in range(WALKS_PER_NODE):
        rng.shuffle(nodes)
        for n in nodes:
            corpus.append(generate_walk(n, adj, artist_tags, tag_artists, rng))
    return corpus


def train_embeddings(corpus, seed=SEED):
    model = Word2Vec(
        sentences=corpus, vector_size=EMBED_DIM, window=WINDOW, min_count=MIN_COUNT,
        sg=1, negative=NEGATIVE, epochs=EPOCHS, workers=os.cpu_count() or 4, seed=seed,
    )
    return model


def artist_vectors(model):
    """name -> vector, for every artist:: token the model actually learned."""
    out = {}
    for tok in model.wv.index_to_key:
        if tok.startswith("artist::"):
            out[tok[len("artist::"):]] = model.wv[tok]
    return out


# --- verification checks -----------------------------------------------

def check_power_law(adj):
    degrees = [len(neighbors) for neighbors in adj.values() if neighbors]
    fit = powerlaw.Fit(degrees, discrete=True, verbose=False)
    R, p = fit.distribution_compare("power_law", "exponential")
    return {
        "alpha": fit.power_law.alpha,
        "xmin": fit.power_law.xmin,
        "ks_distance": fit.power_law.D,
        "loglikelihood_ratio_vs_exponential": R,
        "p_value_vs_exponential": p,
        "n_nodes_with_degree": len(degrees),
        "mean_degree": sum(degrees) / len(degrees) if degrees else 0,
    }


def check_link_prediction(universe):
    full_adj, _, _ = build_adjacency(universe)
    edges = all_edges(full_adj)
    rng = random.Random(SEED)
    rng.shuffle(edges)
    n_holdout = int(len(edges) * HELD_OUT_FRACTION)
    holdout = edges[:n_holdout]
    holdout_set = {frozenset((a, b)) for a, b, _ in holdout}

    train_adj, train_tags, train_tag_artists = build_adjacency(universe, exclude_edges=holdout_set)
    train_degree = {n: len(v) for n, v in train_adj.items()}

    corpus = build_walk_corpus(train_adj, train_tags, train_tag_artists, seed=SEED + 1)
    model = train_embeddings(corpus, seed=SEED + 1)
    vecs = artist_vectors(model)

    names_with_vecs = set(vecs.keys())
    holdout_pairs = [(a, b) for a, b in ((a, b) for a, b, _ in holdout)
                      if a in names_with_vecs and b in names_with_vecs]

    # negative sample: same count of random non-edge pairs, drawn from the
    # same node pool, that are neither a training edge nor a held-out edge
    train_edge_set = {frozenset((a, b)) for a in train_adj for b in train_adj[a]}
    pool = list(names_with_vecs)
    negatives = []
    seen_neg = set()
    while len(negatives) < len(holdout_pairs) and pool:
        a, b = rng.sample(pool, 2)
        key = frozenset((a, b))
        if key in train_edge_set or key in holdout_set or key in seen_neg:
            continue
        seen_neg.add(key)
        negatives.append((a, b))

    def cos_sim(a, b):
        va, vb = vecs[a], vecs[b]
        return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))

    y_true = [1] * len(holdout_pairs) + [0] * len(negatives)
    y_score_embed = [cos_sim(a, b) for a, b in holdout_pairs] + [cos_sim(a, b) for a, b in negatives]
    auc_embed = roc_auc_score(y_true, y_score_embed) if len(set(y_true)) > 1 else float("nan")

    # degree-preserving baseline: preferential attachment on the TRAINING graph
    def pref_attach(a, b):
        return train_degree.get(a, 0) * train_degree.get(b, 0)

    y_score_baseline = [pref_attach(a, b) for a, b in holdout_pairs] + [pref_attach(a, b) for a, b in negatives]
    auc_baseline = roc_auc_score(y_true, y_score_baseline) if len(set(y_true)) > 1 else float("nan")

    return {
        "n_holdout_edges": len(holdout_pairs),
        "n_negative_pairs": len(negatives),
        "auc_embedding": auc_embed,
        "auc_preferential_attachment_baseline": auc_baseline,
        "passes_0.7_threshold": bool(auc_embed >= 0.7) if auc_embed == auc_embed else False,
    }


def check_known_lineage(vecs):
    quartet = ["Nick Drake", "Bert Jansch", "John Martyn", "Tim Buckley"]
    present = [n for n in quartet if n in vecs]
    missing = [n for n in quartet if n not in vecs]
    if len(present) < 2:
        return {"present": present, "missing": missing, "note": "not enough of the quartet in the embedding to check"}

    names = list(vecs.keys())
    matrix = np.array([vecs[n] for n in names])
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
    normed = matrix / norms
    name_to_idx = {n: i for i, n in enumerate(names)}

    results = {}
    for n in present:
        sims = normed @ normed[name_to_idx[n]]
        order = np.argsort(-sims)
        ranked_names = [names[i] for i in order if names[i] != n][:TOP_N_NEIGHBORS]
        others_in_quartet = [o for o in present if o != n]
        ranks = {}
        for o in others_in_quartet:
            if o in ranked_names:
                ranks[o] = ranked_names.index(o) + 1
            else:
                ranks[o] = None  # not in top-N at all
        results[n] = {"rank_of_others_in_top_%d" % TOP_N_NEIGHBORS: ranks}

    all_mutual = all(
        v is not None
        for r in results.values()
        for v in r["rank_of_others_in_top_%d" % TOP_N_NEIGHBORS].values()
    )
    return {"present": present, "missing": missing, "neighbor_ranks": results, "all_mutual_top_%d" % TOP_N_NEIGHBORS: all_mutual}


def check_personal_coherence(vecs, library_names, n_random_trials=20):
    library_in_universe = sorted(n for n in library_names if n in vecs)
    if len(library_in_universe) < 4:
        return {"note": "too few library artists present in the universe to compute silhouette"}

    all_names = list(vecs.keys())
    matrix = np.array([vecs[n] for n in all_names])
    name_to_idx = {n: i for i, n in enumerate(all_names)}
    lib_idx = set(name_to_idx[n] for n in library_in_universe)

    labels = np.array([1 if i in lib_idx else 0 for i in range(len(all_names))])
    real_score = silhouette_score(matrix, labels, metric="cosine")

    rng = random.Random(SEED)
    random_scores = []
    k = len(library_in_universe)
    for _ in range(n_random_trials):
        sample_idx = set(rng.sample(range(len(all_names)), k))
        rand_labels = np.array([1 if i in sample_idx else 0 for i in range(len(all_names))])
        random_scores.append(silhouette_score(matrix, rand_labels, metric="cosine"))

    return {
        "library_artists_in_universe": k,
        "real_silhouette": float(real_score),
        "random_baseline_mean": float(np.mean(random_scores)),
        "random_baseline_std": float(np.std(random_scores)),
        "more_clustered_than_random": bool(real_score > np.mean(random_scores) + np.std(random_scores)),
    }


def check_isolated_nodes(adj):
    isolated = [n for n, neighbors in adj.items() if not neighbors]
    return {"n_isolated": len(isolated), "isolated_sample": isolated[:20]}


def get_library_names():
    if not os.path.exists(ARTIST_CACHE_PATH):
        return set()
    with open(ARTIST_CACHE_PATH) as f:
        cache = json.load(f)
    return {e["name"] for e in cache.values() if e.get("in_library")}


def main():
    print("Loading universe...")
    universe = load_universe()
    print(f"{len(universe)} artists in universe.")

    full_adj, artist_tags, tag_artists = build_adjacency(universe)

    print("\n--- Check 5: isolated nodes ---")
    iso = check_isolated_nodes(full_adj)
    print(json.dumps(iso, indent=2)[:500])

    print("\n--- Check 1: degree-distribution power-law fit ---")
    pl = check_power_law(full_adj)
    print(json.dumps(pl, indent=2))

    print("\nBuilding walk corpus on the full graph...")
    corpus = build_walk_corpus(full_adj, artist_tags, tag_artists)
    print(f"{len(corpus)} walks, {sum(len(w) for w in corpus)} total tokens.")

    print("Training Word2Vec...")
    model = train_embeddings(corpus)
    vecs = artist_vectors(model)
    print(f"Learned vectors for {len(vecs)}/{len(universe)} artists "
          f"(the rest never appeared in a walk, likely due to zero in-universe similarity edges).")

    print("\n--- Check 3: known-lineage sanity (Nick Drake / Bert Jansch / John Martyn / Tim Buckley) ---")
    lineage = check_known_lineage(vecs)
    print(json.dumps(lineage, indent=2, default=str))

    print("\n--- Check 4: personal coherence silhouette ---")
    library_names = get_library_names()
    coherence = check_personal_coherence(vecs, library_names)
    print(json.dumps(coherence, indent=2))

    print("\n--- Check 2: held-out link prediction AUC (this retrains a second embedding, takes a while) ---")
    link_pred = check_link_prediction(universe)
    print(json.dumps(link_pred, indent=2))

    print("\nProjecting to 2D with UMAP (cosine metric)...")
    names_ordered = list(vecs.keys())
    matrix = np.array([vecs[n] for n in names_ordered])
    reducer = umap.UMAP(metric="cosine", random_state=SEED)
    coords_2d = reducer.fit_transform(matrix)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    np.save(os.path.join(OUTPUT_DIR, "embeddings.npy"), matrix)
    with open(os.path.join(OUTPUT_DIR, "embedding_names.json"), "w") as f:
        json.dump(names_ordered, f)
    atlas_coords = {name: {"x": float(x), "y": float(y)} for name, (x, y) in zip(names_ordered, coords_2d)}
    with open(os.path.join(OUTPUT_DIR, "atlas_coords.json"), "w") as f:
        json.dump(atlas_coords, f)

    report = {
        "n_artists_in_universe": len(universe),
        "n_artists_embedded": len(vecs),
        "check_1_power_law": pl,
        "check_2_link_prediction": link_pred,
        "check_3_known_lineage": lineage,
        "check_4_personal_coherence": coherence,
        "check_5_isolated_nodes": iso,
    }
    with open(os.path.join(OUTPUT_DIR, "verification_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nWrote {OUTPUT_DIR}/embeddings.npy, embedding_names.json, atlas_coords.json, verification_report.json")


if __name__ == "__main__":
    main()
