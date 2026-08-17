---
type: analysis
tags: [taste-analysis, atlas]
---

# Taste Atlas

A 14940-artist population-scale map, built by crawling Last.fm's similarity graph outward from your library and training a metapath-constrained (artist-similar-artist / artist-tag-artist) Word2Vec embedding, projected to 2D with UMAP. See `analysis/output/taste_atlas.html` for the interactive version — this note is the honest numeric record of whether it's trustworthy, per the falsifiable checks in `FLAVORGRAPH_PLAN.md`.

## Verification (falsifiable — reported as measured, not cherry-picked)

1. **Degree power-law fit**: alpha=2.96, KS distance=0.151. Compared against an exponential fit: log-likelihood ratio -1079.8 (p=0) — negative ratio means **exponential fits better than power-law**, so the crawled graph does NOT cleanly reproduce the flavor-network topology the plan hoped for. Reporting this plainly rather than only the alpha number, which alone would look closer to Ahn et al.'s ~2.3 than it is.

2. **Held-out link prediction AUC**: 0.994 vs a degree-preferential-attachment baseline of 0.668 (n=23285 held-out edges). **Passes** the 0.7 threshold — the embedding is capturing real structure well beyond what raw degree alone would predict.

3. **Known-lineage sanity** (Nick Drake / Bert Jansch / John Martyn / Tim Buckley): NOT all mutual near-neighbours in each other's top-20. Nick Drake and Tim Buckley land close together; Bert Jansch is the outlier — not in Nick Drake's or Tim Buckley's top-20 in either direction. Reported as a partial pass, not hidden.

4. **Personal coherence silhouette**: 0.0065 vs a random-subset baseline of 0.0001 (± 0.0021). More clustered than random, but both numbers are near zero in absolute terms — your library artists are only weakly, not tightly, clustered against the full universe. A real but modest signal.

5. **Isolated nodes**: 1 (`Yusuf / Cat Stevens`) — likely a Last.fm/Spotify name-string mismatch (e.g. 'Yusuf / Cat Stevens' vs Last.fm's 'Cat Stevens'), not a crawl failure. Crawl resumability was also verified in practice — this crawl was killed and resumed from checkpoint multiple times during the actual run.

## Seed sensitivity (is check 3/4 reproducible, or noise?)

Checks 3 and 4 were only ever run once, at a fixed seed. Re-ran the embedding 4 times ([42, 1, 7, 13]) and recomputed both checks each time, since even the dedup pass alone visibly moved the quartet's neighbor ranks between runs. Result: **not noise**. Bert Jansch never has Nick Drake in its own top-20 across any seed (0/4), while Bert Jansch and John Martyn are mutual neighbours in every single seed (4/4 and 4/4) — the outlier finding is a reproducible property of the embedding space, not an artifact of one run. The coherence silhouette is also stable across seeds: ['0.0082', '0.0081', '0.0057', '0.0067'] — always positive, always above its own seed's random baseline, spread 0.0025. Full per-pair breakdown in `data/universe/seed_variance_report.json`.

## Named territories (dominant Last.fm tag per artist)

| Tag | Artists |
|---|---|
| pop | 1032 |
| folk | 571 |
| soul | 570 |
| rnb | 505 |
| country | 503 |
| rap | 499 |
| jazz | 478 |
| indie | 446 |
| indie rock | 402 |
| hip-hop | 386 |
| house | 325 |
| electronic | 292 |
| indie pop | 291 |
| singer-songwriter | 279 |
| other | 8361 |

## Geometric discovery frontier

Artists that sit as embedding-space nearest-neighbours of your library artists, not yet in your library — the 'empty regions adjacent to your territory' from the plan, made concrete. This is a different computation from `[[Discovery Frontier]]` (embedding-space proximity here, vs. raw Last.fm match-score summation there) — worth treating as two independent signals.

- [ ] **Hudson Westbrook** — near Chris Stapleton, Cody Johnson, Ella Langley, Megan Moroney
- [ ] **Luke Grimes** — near Chris Stapleton, The Red Clay Strays, Zach Bryan
- [ ] **Riley Green** — near Cody Johnson, Ella Langley, Jon Pardi
- [ ] **Tucker Wetmore** — near Cody Johnson, Ella Langley, Megan Moroney
- [ ] **Durand Jones** — near Aaron Frazer, Durand Jones & The Indications, Leon Bridges
- [ ] **Drayton Farley** — near Tyler Childers, Zach Bryan
- [ ] **Ole 60** — near Chris Stapleton, The Red Clay Strays
- [ ] **Bryan Martin** — near Chris Stapleton, The Red Clay Strays
- [ ] **Anderson East** — near Leon Bridges, St. Paul & The Broken Bones
- [ ] **The Dip** — near Leon Bridges, St. Paul & The Broken Bones
- [ ] **Lee Fields & The Expressions** — near Durand Jones & The Indications, St. Paul & The Broken Bones
- [ ] **Black Pumas** — near Leon Bridges, St. Paul & The Broken Bones
- [ ] **Shabazz Pbg** — near Gunna, Lil Uzi Vert
- [ ] **Drugdealer & Weyes Blood** — near Drugdealer, Marlon Funaki
- [ ] **Paul Cherry** — near Drugdealer, Marlon Funaki
- [ ] **Temples** — near Drugdealer, Marlon Funaki
- [ ] **Alicia Keys** — near Adele, Amy Winehouse
- [ ] **Hajaj** — near Aaron Frazer, Leon Bridges
- [ ] **Curtis Harding** — near Durand Jones & The Indications, Leon Bridges
- [ ] **Justin Timberlake** — near Bruno Mars, Rihanna
