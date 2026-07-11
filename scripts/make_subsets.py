"""Nested fixed-seed real-data subsets for the §14 budget axis (EVAL_PROTOCOL §14.1, FROZEN).

`[LOCKED]` r in {10, 25, 50, 100}% of the train split, **NESTED** (10 subset-of 25 subset-of 50
subset-of 100), drawn at CROP level, with the subset seed recorded in the manifest.

Nesting is guaranteed structurally: shuffle the 25,742 train crops ONCE with a fixed seed, then
take PREFIXES. A prefix of a prefix is a subset by construction -- no set arithmetic to get wrong.
Nesting matters because it makes the budget axis a clean ablation: the r=10% model sees a strict
subset of what the r=25% model sees, so a difference between them is the ADDED labels, not a
different sample of them.
"""
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

SUBSET_SEED = 20260711     # recorded in every manifest
FRACTIONS = (10, 25, 50)   # r=100 is the full annotation_train.txt (reused: baseline A / leg run)
ROOT = "data/crops"


def main():
    src = os.path.join(ROOT, "annotation_train.txt")
    lines = [ln.rstrip("\n") for ln in open(src, encoding="utf-8") if ln.strip()]
    n = len(lines)

    order = list(range(n))
    random.Random(SUBSET_SEED).shuffle(order)     # ONE shuffle -> prefixes are nested

    manifest = dict(subset_seed=SUBSET_SEED, source=src, n_full=n, nested=True, subsets={})
    prev = None
    for r in FRACTIONS:
        k = round(n * r / 100)
        idx = order[:k]
        out = os.path.join(ROOT, f"annotation_train_r{r}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines[i] for i in idx) + "\n")
        # verify nesting against the previous (smaller) subset
        s = set(idx)
        if prev is not None:
            assert prev.issubset(s), f"NESTING BROKEN at r={r}"
        prev = s
        manifest["subsets"][f"r{r}"] = dict(fraction_pct=r, n_crops=k, annotation=out)
        print(f"r={r:3d}%  {k:6d} crops -> {out}")
    manifest["subsets"]["r100"] = dict(fraction_pct=100, n_crops=n,
                                       annotation=src, note="full train split (reused)")
    print(f"r=100%  {n:6d} crops -> {src} (reused)")

    mpath = os.path.join(ROOT, "budget_subsets_manifest.json")
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), indent=2)
    print(f"\nNESTING VERIFIED (10 subset-of 25 subset-of 50). seed={SUBSET_SEED} -> {mpath}")


if __name__ == "__main__":
    main()
