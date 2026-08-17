"""One-off cleanup pass over the crawled Last.fm universe (data/universe/universe.json).

Three real duplicate-node problems were found by inspection after the crawl,
handled by three passes with different confidence levels:

1. Apostrophe/case/joiner duplicates (SAFE, auto-merged) — Last.fm returns
   the same real artist, or the same multi-artist credit, under slightly
   different strings depending on which page/lookup you hit it from (e.g.
   "DON WEST" vs "Don West", "Lil Wayne" vs "Lil' Wayne", or
   "...Leslie Odom, Jr., Original Broadway Cast of Hamilton" vs
   "...Leslie Odom, Jr. & Original Broadway Cast Of Hamilton" — the same
   ordered credit list with "&" and "," used interchangeably as the final
   joiner). Found by grouping names on a loose key (Unicode-normalized,
   apostrophes stripped, "&"/"," joiners unified, whitespace collapsed,
   casefolded). Verified safe by inspection: unifying interchangeable
   separator punctuation between two otherwise character-identical ordered
   name lists produced zero false positives across the real examples found.
   The canonical spelling per group is picked by which variant more OTHER
   crawled artists already point to in their `similar` lists — a
   data-driven tiebreak using the crawl's own evidence — falling back to
   the non-ALL-CAPS form on a tie.

2. Punctuation-stripped duplicates (GATED, not blindly auto-merged) —
   stripping periods additionally catches real duplicates like "JID" vs
   "J.I.D" or "H.E.R." vs "Her". But this pass has a confirmed
   false-positive risk: blind period-stripping would also incorrectly
   merge genuinely different artists that happen to share a punctuation-
   stylized short name — "Liv.e" vs "Live", "Mike" vs "M.I.K.E.", "Wet" vs
   "W.E.T.", "Act" vs "A.C.T", "sports." vs "Sports" were all confirmed
   different real artists by near-zero Last.fm tag-set overlap. So this
   pass only auto-merges a candidate pair when BOTH have non-empty `tags`
   and their Jaccard similarity is >= PUNCT_JACCARD_THRESHOLD; everything
   else is written to `data/universe/dedupe_review.json` for manual review
   rather than silently merged or silently ignored.

3. Compound-junk nodes (SAFE, auto-dropped) — Last.fm sometimes returns a
   multi-artist collaboration credit string (e.g. "Miles Davis, John
   Coltrane, Bill Evans") as if it were a single artist. Detected as any
   name containing a comma whose comma-split parts are ALL themselves
   existing real artist nodes elsewhere in the universe. Their own crawled
   tags/similar data describes the ensemble, not any one member, so it's
   discarded; any OTHER artist's edge pointing at the junk node is
   redirected to point at each of the real components instead, at the same
   match weight.

Run this once against the raw crawl output. Afterwards, embed.py, atlas.py,
and vault_writer.py must be re-run to regenerate the embeddings/atlas/vault
notes from the cleaned graph — this script only touches universe.json.
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict

UNIVERSE_PATH = "data/universe/universe.json"
REVIEW_LOG_PATH = "data/universe/dedupe_review.json"
PUNCT_JACCARD_THRESHOLD = 0.25


def normalize_loose(name):
    s = unicodedata.normalize("NFKC", name)
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("'", "")
    s = s.replace(" & ", ", ")  # unify "&" and "," as equivalent list joiners
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def normalize_punct_stripped(name):
    return normalize_loose(name).replace(".", "")


def find_duplicate_groups(names, key_fn):
    groups = defaultdict(list)
    for n in names:
        groups[key_fn(n)].append(n)
    return {k: v for k, v in groups.items() if len(v) > 1}


def tag_jaccard(tags_a, tags_b):
    a, b = set(tags_a), set(tags_b)
    if not a or not b:
        return None  # insufficient evidence either way — not a "0", genuinely unknown
    return len(a & b) / len(a | b)


def find_compound_junk(names):
    name_set = set(names)
    junk = []
    for n in names:
        if "," not in n:
            continue
        parts = [p.strip() for p in n.split(",")]
        if len(parts) >= 2 and all(p in name_set and p != n for p in parts):
            junk.append((n, parts))
    return junk


def in_degree_counts(universe):
    counts = Counter()
    for entry in universe.values():
        for sim in entry.get("similar", []):
            counts[sim["name"]] += 1
    return counts


def choose_canonical(variants, indeg):
    def sort_key(v):
        return (-indeg.get(v, 0), v.isupper(), v)
    return sorted(variants, key=sort_key)[0]


def merge_entries(winner, loser_entries, variant_set):
    """winner: dict (mutated in place). loser_entries: list of dicts folded
    in. variant_set: every raw name string in this duplicate group, so a
    similar-artist edge from one spelling to another spelling of the SAME
    artist is dropped as a self-reference rather than kept as a real edge."""
    tags = list(winner.get("tags", []))
    tag_set = set(tags)
    sims_by_name = {
        s["name"]: s["match"] for s in winner.get("similar", []) if s["name"] not in variant_set
    }
    for entry in loser_entries:
        for t in entry.get("tags", []):
            if t not in tag_set:
                tags.append(t)
                tag_set.add(t)
        for s in entry.get("similar", []):
            if s["name"] in variant_set:
                continue
            sims_by_name[s["name"]] = max(sims_by_name.get(s["name"], 0), s["match"])
        winner["depth"] = min(winner.get("depth", 999), entry.get("depth", 999))
    winner["tags"] = tags
    winner["similar"] = sorted(
        ({"name": n, "match": m} for n, m in sims_by_name.items()),
        key=lambda s: -s["match"],
    )
    return winner


def rewrite_references(universe, rename_map, junk_to_components):
    for name, entry in universe.items():
        new_sims = {}
        for sim in entry.get("similar", []):
            target = sim["name"]
            if target in rename_map:
                targets = [rename_map[target]]
            elif target in junk_to_components:
                targets = junk_to_components[target]
            else:
                targets = [target]
            for t in targets:
                if t == name:
                    continue  # drop self-loops created by renaming/redirecting
                new_sims[t] = max(new_sims.get(t, 0), sim["match"])
        entry["similar"] = sorted(
            ({"name": n, "match": m} for n, m in new_sims.items()),
            key=lambda s: -s["match"],
        )


def main():
    with open(UNIVERSE_PATH) as f:
        universe = json.load(f)

    names = list(universe.keys())
    print(f"Starting universe: {len(names)} artists.")

    indeg = in_degree_counts(universe)

    # --- Step 1: merge apostrophe/case/joiner duplicates (safe) ---
    dup_groups = find_duplicate_groups(names, normalize_loose)
    rename_map = {}
    for key, variants in dup_groups.items():
        canonical = choose_canonical(variants, indeg)
        losers = [v for v in variants if v != canonical]
        merge_entries(universe[canonical], [universe[l] for l in losers], set(variants))
        for l in losers:
            rename_map[l] = canonical
            del universe[l]

    print(f"\nMerged {len(dup_groups)} duplicate groups ({len(rename_map)} redundant nodes removed):")
    for l, w in sorted(rename_map.items()):
        print(f"  {l!r} -> {w!r}")

    # --- Step 1b: gated punctuation-stripped pass — only merge with tag evidence ---
    punct_names = list(universe.keys())
    punct_groups = find_duplicate_groups(punct_names, normalize_punct_stripped)
    review_log = []
    punct_merged = 0
    for key, variants in punct_groups.items():
        canonical = choose_canonical(variants, indeg)
        for v in variants:
            if v == canonical or v not in universe:
                continue
            jac = tag_jaccard(universe[canonical].get("tags", []), universe[v].get("tags", []))
            if jac is not None and jac >= PUNCT_JACCARD_THRESHOLD:
                merge_entries(universe[canonical], [universe[v]], {canonical, v})
                rename_map[v] = canonical
                del universe[v]
                punct_merged += 1
            else:
                review_log.append({
                    "a": canonical, "a_tags": universe[canonical].get("tags", []),
                    "b": v, "b_tags": universe[v].get("tags", []),
                    "jaccard": jac,
                })

    print(f"\nPunctuation-stripped pass: merged {punct_merged} pairs with tag-Jaccard >= "
          f"{PUNCT_JACCARD_THRESHOLD} evidence; logged {len(review_log)} lower-confidence "
          f"candidates to {REVIEW_LOG_PATH} for manual review instead of guessing.")
    with open(REVIEW_LOG_PATH, "w") as f:
        json.dump(review_log, f, indent=1)

    # --- Step 2: drop compound-junk nodes, map to their real components ---
    remaining_names = set(universe.keys())
    junk = find_compound_junk(remaining_names)
    junk_to_components = {}
    for junk_name, parts in junk:
        real_parts = [p for p in parts if p in universe and p != junk_name]
        if not real_parts:
            continue
        junk_to_components[junk_name] = real_parts
        del universe[junk_name]

    print(f"\nDropped {len(junk_to_components)} compound-junk nodes (Last.fm multi-artist credit strings):")
    for j, parts in sorted(junk_to_components.items()):
        print(f"  {j!r} -> {parts}")

    # --- Step 3: rewrite every remaining artist's `similar` list against the cleaned names ---
    rewrite_references(universe, rename_map, junk_to_components)

    print(f"\nFinal universe: {len(universe)} artists (was {len(names)}).")

    with open(UNIVERSE_PATH, "w") as f:
        json.dump(universe, f)
    print(f"Wrote {UNIVERSE_PATH}")


if __name__ == "__main__":
    main()
