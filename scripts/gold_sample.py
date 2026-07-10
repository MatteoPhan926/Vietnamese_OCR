"""Stage 0.6 — the Gold reference set: stratified sample + transcription tooling.

EVAL_PROTOCOL §5: gold is defined in INSTANCES (~2,000-3,000), is a SUBSET of test-500, and
is STRATIFIED to over-sample the crops that actually fail (diacritic-dense / small / low-
contrast). Uniform sampling burns the verification budget on easy words that never fail.

THIS SCRIPT DOES NOT PRODUCE GOLD LABELS. The codepoint-by-codepoint double-pass is the
user's manual work (§5). This script only:
  1. measures each test-500 instance on the stratification features,
  2. draws the stratified sample with RECORDED INCLUSION PROBABILITIES,
  3. writes the crops + a transcription sheet for the human pass.

WHY THE INCLUSION PROBABILITIES MATTER (a subtlety §5 implies but does not spell out):
a stratified over-sample is NOT a uniform sample of test-500. The raw gold-vs-public
disagreement rate therefore estimates the noise floor of the *hard strata*, not of the
test set. Both quantities are wanted:
  * per-stratum disagreement  -> where labels are unreliable (a finding in itself);
  * Horvitz-Thompson reweighted disagreement (weight = 1/inclusion_prob)
                              -> an unbiased estimate of the WHOLE test set's noise floor.
Recording pi_incl per instance is what makes the second one computable at all. Without it
the stratification silently biases the very number the gold set exists to produce.
"""
import argparse
import json
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.crops import crop_quad  # noqa: E402
from scripts.scorer import decompose  # noqa: E402
from scripts.vintext import iter_instances  # noqa: E402

OUT = os.path.join("data", "gold")


def stacked_count(text):
    """chars carrying BOTH a letter-forming modifier AND a tone (ế ệ ữ ự ấ ộ ...)."""
    n = 0
    for ch in text:
        d = decompose(ch)
        if d.modifier != "none" and d.tone != "ngang":
            n += 1
    return n


def diacritic_count(text):
    return sum(1 for ch in text
               if decompose(ch).modifier != "none" or decompose(ch).tone != "ngang")


def michelson(gray):
    """Contrast robust to outliers: (p95 - p5) / (p95 + p5)."""
    p5, p95 = np.percentile(gray, 5), np.percentile(gray, 95)
    return float((p95 - p5) / (p95 + p5 + 1e-6))


def measure():
    """Feature-measure every scorable test-500 instance."""
    rows = []
    cache_path, img = None, None
    for inst in iter_instances("test", scorable_only=True):
        if inst.img_path != cache_path:
            img = cv2.imread(inst.img_path)
            cache_path = inst.img_path
        c = crop_quad(img, inst.poly)
        if c is None:
            h = w = 0
            contrast = 0.0
        else:
            h, w = c.shape[0], c.shape[1]
            contrast = michelson(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY))
        rows.append(dict(
            img_id=inst.img_id, poly=list(inst.poly), text=inst.text,
            height=h, width=w, contrast=round(contrast, 4),
            n_chars=len(inst.text),
            n_stacked=stacked_count(inst.text),
            n_diac=diacritic_count(inst.text),
        ))
    return rows


def assign_strata(rows, small_px, low_contrast):
    """Priority order: a row lands in the FIRST stratum it matches (disjoint strata)."""
    for r in rows:
        if r["n_stacked"] >= 1:
            r["stratum"] = "diacritic_dense"
        elif r["height"] < small_px:
            r["stratum"] = "small"
        elif r["contrast"] < low_contrast:
            r["stratum"] = "low_contrast"
        else:
            r["stratum"] = "plain"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=2400, help="gold instance budget (§5: 2000-3000)")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--write-crops", action="store_true")
    # sampling FRACTION per stratum. Chosen after inspecting the distribution (below) to
    # land near the middle of §5's 2000-3000 band while keeping diacritic_dense dominant.
    # Even the smallest stratum (~260) pins a ~3% disagreement rate to <1.1pp SE.
    ap.add_argument("--frac-dense", type=float, default=0.50)
    ap.add_argument("--frac-small", type=float, default=0.30)
    ap.add_argument("--frac-lowcontrast", type=float, default=0.30)
    ap.add_argument("--frac-plain", type=float, default=0.06)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    rows = measure()
    print(f"measured {len(rows)} scorable test-500 instances\n")

    # thresholds from the data, not the armchair
    heights = np.array([r["height"] for r in rows if r["height"] > 0])
    contrasts = np.array([r["contrast"] for r in rows])
    small_px = int(np.percentile(heights, 25))
    low_contrast = float(np.percentile(contrasts, 25))
    print(f"small-text threshold  = height < {small_px}px   (25th pct of crop heights)")
    print(f"low-contrast threshold= michelson < {low_contrast:.4f} (25th pct)\n")

    rows = assign_strata(rows, small_px, low_contrast)

    # §5: over-sample what fails. Sampling FRACTION per stratum (not counts) so the
    # inclusion probability is explicit and constant within a stratum.
    frac = {"diacritic_dense": args.frac_dense, "small": args.frac_small,
            "low_contrast": args.frac_lowcontrast, "plain": args.frac_plain}

    by = {}
    for r in rows:
        by.setdefault(r["stratum"], []).append(r)

    rng = random.Random(args.seed)
    gold = []
    print(f"{'stratum':18s} {'population':>10s} {'frac':>6s} {'sampled':>8s} {'pi_incl':>8s}")
    for s, pop in by.items():
        k = int(round(len(pop) * frac[s]))
        pi = k / len(pop)
        pick = rng.sample(pop, k)
        for r in pick:
            r["pi_incl"] = round(pi, 6)
            r["ht_weight"] = round(1.0 / pi, 4)  # Horvitz-Thompson weight
        gold.extend(pick)
        print(f"{s:18s} {len(pop):10d} {frac[s]:6.2f} {k:8d} {pi:8.4f}")

    print(f"\nGOLD TOTAL = {len(gold)} instances  (target {args.target}, §5 band 2000-3000)")
    # measured: no test instance carries >=2 stacked chars (dist is exactly {0:7726, 1:2342}).
    # Vietnamese orthographic words are monosyllabic and VinText boxes are per-word, so a
    # word has at most one modifier+tone nucleus. So instances == stacked chars here.
    g_st = sum(r["n_stacked"] for r in gold)
    a_st = sum(r["n_stacked"] for r in rows)
    print(f"  stacked-diacritic chars captured: {g_st} of {a_st} in test-500 "
          f"({100*g_st/max(1,a_st):.1f}% coverage)")
    print(f"  gold diacritic-bearing chars: {sum(r['n_diac'] for r in gold)}")

    gold.sort(key=lambda r: (r["img_id"], r["poly"]))
    meta = dict(
        n_gold=len(gold), target=args.target, seed=args.seed,
        thresholds=dict(small_px=small_px, low_contrast_michelson=low_contrast),
        strata_fractions=frac,
        strata_population={s: len(p) for s, p in by.items()},
        parent_set="VinText test-500 (unseen_test_images), scorable instances only",
        parent_n=len(rows),
        note=("pi_incl / ht_weight recorded per instance: the raw gold-vs-public "
              "disagreement rate estimates the HARD STRATA's noise floor; the "
              "Horvitz-Thompson reweighted rate estimates the whole test-500's."),
    )
    with open(f"{OUT}/gold_manifest.json", "w", encoding="utf-8") as f:
        json.dump(dict(meta=meta, instances=gold), f, ensure_ascii=False, indent=1)

    # the human transcription sheet -- PUBLIC LABEL LEFT IN A SEPARATE COLUMN so the
    # transcriber can be blinded to it if desired; gold column starts EMPTY.
    with open(f"{OUT}/transcription_sheet.tsv", "w", encoding="utf-8") as f:
        f.write("idx\tcrop_file\timg_id\tstratum\tpublic_label\tgold_pass1\tgold_pass2\n")
        for i, r in enumerate(gold):
            f.write(f"{i}\tcrops/{i:05d}.png\t{r['img_id']}\t{r['stratum']}\t{r['text']}\t\t\n")

    if args.write_crops:
        cd = f"{OUT}/crops"
        os.makedirs(cd, exist_ok=True)
        cache_path, img = None, None
        for i, r in enumerate(gold):
            p = os.path.join("data", "vietnamese", "unseen_test_images", f"im{r['img_id']:04d}.jpg")
            if p != cache_path:
                img = cv2.imread(p)
                cache_path = p
            c = crop_quad(img, tuple(r["poly"]))
            if c is None:  # degenerate: upscale so a human can even see it
                x = np.array(r["poly"]).reshape(4, 2)
                x0, y0, x1, y1 = x[:, 0].min(), x[:, 1].min(), x[:, 0].max(), x[:, 1].max()
                c = img[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2]
            if c.size:
                s = max(1, int(64 / max(1, c.shape[0])))
                c = cv2.resize(c, (c.shape[1] * s, c.shape[0] * s), interpolation=cv2.INTER_CUBIC)
            cv2.imwrite(f"{cd}/{i:05d}.png", c)
        print(f"\nwrote {len(gold)} crops -> {cd}/")

    print(f"\nwrote {OUT}/gold_manifest.json  and  {OUT}/transcription_sheet.tsv")
    print("\nGOLD LABELS ARE NOT GENERATED HERE. The double-pass is manual (EVAL_PROTOCOL §5).")


if __name__ == "__main__":
    main()
