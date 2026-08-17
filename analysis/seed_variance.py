"""Seed-sensitivity check for embed.py's two weaker verification results
(known-lineage mutuality, personal-coherence silhouette).

The shipped embedding (data/universe/embeddings.npy) is trained once at
SEED=42. Even a small universe change (the dedup pass) visibly moved the
Nick Drake / Bert Jansch / John Martyn / Tim Buckley neighbor ranks between
runs — reason enough to check whether these two checks are measuring real
structure or seed noise, before treating "Bert Jansch is the outlier" as a
settled finding.

This reuses embed.py's build_adjacency/build_walk_corpus/train_embeddings/
artist_vectors/check_known_lineage/check_personal_coherence directly — no
changes to embed.py. It deliberately skips the held-out link-prediction
retrain and the UMAP projection (not relevant to this question, and
expensive) to keep each seed's run to about 2 minutes instead of ~5.

Does not touch the shipped embeddings/atlas_coords — diagnostic only.
"""
import json
import time

from embed import (
    load_universe, build_adjacency, build_walk_corpus, train_embeddings,
    artist_vectors, check_known_lineage, check_personal_coherence, get_library_names,
    SEED,
)

SEEDS = [SEED, 1, 7, 13]
OUTPUT_PATH = "data/universe/seed_variance_report.json"
LINEAGE_QUARTET = ["Nick Drake", "Bert Jansch", "John Martyn", "Tim Buckley"]


def run_one_seed(seed, adj, artist_tags, tag_artists, library_names):
    t0 = time.time()
    corpus = build_walk_corpus(adj, artist_tags, tag_artists, seed=seed)
    model = train_embeddings(corpus, seed=seed)
    vecs = artist_vectors(model)
    lineage = check_known_lineage(vecs)
    coherence = check_personal_coherence(vecs, library_names)
    print(f"  seed={seed} done in {time.time()-t0:.0f}s — "
          f"all_mutual_top_20={lineage.get('all_mutual_top_20')}, "
          f"silhouette={coherence.get('real_silhouette')}")
    return lineage, coherence


def summarize_lineage(per_seed_lineage):
    """For each ordered pair in the quartet, how many of the N seeds put
    the second artist in the first's top-20 — a mutuality-consistency score."""
    pair_hits = {}
    n = len(per_seed_lineage)
    for a in LINEAGE_QUARTET:
        for b in LINEAGE_QUARTET:
            if a == b:
                continue
            hits = 0
            for lineage in per_seed_lineage:
                ranks = lineage.get("neighbor_ranks", {}).get(a, {})
                key = f"rank_of_others_in_top_20"
                if ranks.get(key, {}).get(b) is not None:
                    hits += 1
            pair_hits[f"{a} -> {b}"] = f"{hits}/{n}"
    return pair_hits


def main():
    print("Loading universe and building adjacency once (shared across all seeds)...")
    universe = load_universe()
    adj, artist_tags, tag_artists = build_adjacency(universe)
    library_names = get_library_names()

    per_seed_lineage = []
    per_seed_coherence = []
    print(f"Running {len(SEEDS)} seeds: {SEEDS}")
    for seed in SEEDS:
        lineage, coherence = run_one_seed(seed, adj, artist_tags, tag_artists, library_names)
        per_seed_lineage.append(lineage)
        per_seed_coherence.append(coherence)

    pair_hits = summarize_lineage(per_seed_lineage)
    silhouettes = [c.get("real_silhouette") for c in per_seed_coherence if c.get("real_silhouette") is not None]
    baselines = [c.get("random_baseline_mean") for c in per_seed_coherence if c.get("random_baseline_mean") is not None]

    print("\n--- Lineage pair consistency across seeds (how many of N seeds put B in A's top-20) ---")
    for pair, ratio in pair_hits.items():
        print(f"  {pair}: {ratio}")

    print("\n--- Coherence silhouette across seeds ---")
    print(f"  real: {silhouettes}")
    print(f"  baseline: {baselines}")
    if silhouettes:
        mean_sil = sum(silhouettes) / len(silhouettes)
        spread = max(silhouettes) - min(silhouettes)
        print(f"  mean={mean_sil:.5f}, spread={spread:.5f}")

    report = {
        "seeds": SEEDS,
        "lineage_pair_consistency": pair_hits,
        "per_seed_silhouette": silhouettes,
        "per_seed_baseline": baselines,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
