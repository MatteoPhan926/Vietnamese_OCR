"""C4 — ERROR_ANALYSIS §8 before/after at the headline point (EVAL_PROTOCOL §14.2/§14.3).

The MECHANISM half of the flagship. SCALING §9: a curve without the per-axis before/after is an
outcome without a mechanism -- half a result.

BEFORE = real-only(r=10%), k=5 seeds {0..4}      (runs/budget_r10_real_seed*/predictions.tsv)
AFTER  = real(r=10%) + STRICT synth, k=5 seeds   (runs/budget_r10_strict_seed*/predictions.tsv)

Headline movement to be explained: CER 16.509 -> 13.726 (+2.783 pp), tone 89.463 -> 91.497 (+2.033).

THE QUESTION THE BRAIN ASKED (pre-stated, so the answer cannot be shopped):
  * If the gain concentrates on TONE and on SMALL / LOW-CONTRAST / TILTED crops -> the engine hit
    the strata DATA_ENGINE §12 measured as the failure drivers => MECHANISM CONFIRMED.
  * If the gain is UNIFORM across axes and strata -> the synthetic is acting as a generic prior /
    regularizer at a scarce budget, NOT as targeted domain transfer => report that instead. It is
    still a real gain; it is just a DIFFERENT mechanism, and the write-up must say so.
Both outcomes are reportable. Neither is the "right" answer.

Scope: rec-only, VinText test-500 real held-out, NFC (CER/WER) / NFD (axes), frozen denominator
10,068 instances / 37,254 chars. Base axis is CASE-INSENSITIVE (brain adjudication 2026-07-10).
"""
from __future__ import annotations

import json
import statistics as st
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.scorer import Score, score_pair  # noqa: E402
from scripts.stratify import features  # noqa: E402

SEEDS = (0, 1, 2, 3, 4)                       # k=5 (§14.2 C2)
T4 = 2.776445105198166                        # Student t, 4 dof, 95%
ARMS = {"before": "budget_r10_real", "after": "budget_r10_strict"}
N_INST, N_CHARS = 10068, 37254                # frozen denominator (EVAL_PROTOCOL §13)


def load_preds(run, seed):
    with open(f"runs/{run}_seed{seed}/predictions.tsv", encoding="utf-8") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip("\n")]
    return [(r[0], r[1] if len(r) > 1 else "") for r in rows]


def ci(vals):
    m = st.mean(vals)
    return m, (T4 * st.stdev(vals) / len(vals) ** 0.5 if len(vals) > 1 else float("nan"))


def score_idx(pairs, idx):
    sc = Score()
    for j in idx:
        gt, pr = pairs[j]
        score_pair(sc, gt, pr)
    return sc


def arm_stats(preds, idx):
    """Per-seed metrics over a subset of instances -> mean±CI over the k=5 seeds."""
    per = {m: [] for m in ("cer", "base", "mod", "tone")}
    err_chars = []                             # char-level edit distance (for the gain-share split)
    for s in SEEDS:
        sc = score_idx(preds[s], idx)
        per["cer"].append(sc.cer * 100)
        per["base"].append(sc.base_acc_ci * 100)
        per["mod"].append(sc.mod_acc * 100)
        per["tone"].append(sc.tone_acc * 100)
        err_chars.append(sc.cer * sc.char_ref)  # = edit distance in chars
    out = {m: ci(v) for m, v in per.items()}
    out["_err_chars"] = st.mean(err_chars)
    out["_chars"] = score_idx(preds[SEEDS[0]], idx).char_ref
    return out


def delta_ci(a, b):
    """b - a for accuracies (higher=better); a - b for CER (lower=better) is done by the caller.
    Unpaired 95% CI on the difference of two k=5 means (seeds are independent across arms)."""
    (am, ah), (bm, bh) = a, b
    # ah = t*se_a  ->  se_a = ah/t ; se_diff = sqrt(se_a^2 + se_b^2)
    se = ((ah / T4) ** 2 + (bh / T4) ** 2) ** 0.5
    return bm - am, T4 * se


def main():
    feats = features()
    preds = {arm: {s: load_preds(run, s) for s in SEEDS} for arm, run in ARMS.items()}
    for arm in ARMS:
        for s in SEEDS:
            assert len(preds[arm][s]) == len(feats) == N_INST, f"row misalignment: {arm} seed{s}"

    allidx = list(range(N_INST))
    before = arm_stats(preds["before"], allidx)
    after = arm_stats(preds["after"], allidx)

    print("=" * 100)
    print("C4 — ERROR_ANALYSIS §8 BEFORE/AFTER at the headline point r=10% (k=5, rec-only, test-500)")
    print("BEFORE = real-only(2,574 crops)   AFTER = + 10k STRICT-bank synthetic (§14.2 C1)")
    print("axes: NFD; base is CASE-INSENSITIVE. CER/WER: NFC. Frozen denom 10,068 inst / 37,254 chars.")
    print("=" * 100)

    print("\n### OVERALL (the movement to be explained)")
    print(f"{'metric':>10s} {'before':>16s} {'after':>16s} {'Δ (95% CI)':>22s}  clears noise?")
    for m, better_up in (("cer", False), ("base", True), ("mod", True), ("tone", True)):
        d, dh = delta_ci(before[m], after[m])
        shown = d if better_up else -d              # report as "improvement" (+ = better)
        sep = abs(shown) > dh
        print(f"{m.upper():>10s} {before[m][0]:9.3f}±{before[m][1]:5.3f} "
              f"{after[m][0]:9.3f}±{after[m][1]:5.3f} {shown:+11.3f} ± {dh:6.3f}  "
              f"{'YES' if sep else 'no (within noise)'}")

    total_gain_chars = before["_err_chars"] - after["_err_chars"]
    print(f"\ntotal character errors: {before['_err_chars']:.0f} -> {after['_err_chars']:.0f}  "
          f"({total_gain_chars:+.0f} chars fixed, mean over 5 seeds)")

    # ---------------------------------------------------------------- stratified before/after
    STRATA = [
        ("height", [0, 12, 16, 20, 24, 32, 48, 10 ** 9],
         ["<12px", "12-15", "16-19", "20-23", "24-31", "32-47", ">=48"],
         "resolution/blur (DATA_ENGINE §12 rank 3)"),
        ("contrast", [0, .2, .3, .4, .5, .65, 1.01],
         ["<0.20", "0.20-0.29", "0.30-0.39", "0.40-0.49", "0.50-0.64", ">=0.65"],
         "photometric (DATA_ENGINE §12 rank 2)"),
        ("tilt", [0, 5, 10, 20, 91],
         ["<5deg", "5-9", "10-19", ">=20"],
         "geometric (DATA_ENGINE §12 rank 1)"),
        ("length", [0, 2, 4, 6, 9, 13, 10 ** 9],
         ["1 char", "2-3", "4-5", "6-8", "9-12", ">=13"],
         "generation length distribution"),
    ]

    res = dict(overall=dict(
        before={m: before[m] for m in ("cer", "base", "mod", "tone")},
        after={m: after[m] for m in ("cer", "base", "mod", "tone")},
        chars_fixed=total_gain_chars), strata={})

    for key, edges, labels, knob in STRATA:
        print(f"\n### {key.upper()}  — knob: {knob}")
        print(f"{'bin':>11s} {'n':>5s} {'chars':>6s} | {'CER before':>10s} {'CER after':>9s} "
              f"{'ΔCER (95%CI)':>18s} | {'tone before':>11s} {'tone after':>10s} {'Δtone':>16s} | "
              f"{'share of':>8s}")
        print(f"{'':11s} {'':5s} {'':6s} | {'':10s} {'':9s} {'(+ = better)':>18s} | "
              f"{'':11s} {'':10s} {'(+ = better)':>16s} | {'the gain':>8s}")
        rows = []
        for i, lab in enumerate(labels):
            lo, hi = edges[i], edges[i + 1]
            idx = [j for j, f in enumerate(feats) if lo <= f[key] < hi]
            if not idx:
                continue
            b, a = arm_stats(preds["before"], idx), arm_stats(preds["after"], idx)
            dcer, dcer_h = delta_ci(b["cer"], a["cer"])
            dton, dton_h = delta_ci(b["tone"], a["tone"])
            fixed = b["_err_chars"] - a["_err_chars"]
            share = 100.0 * fixed / total_gain_chars if total_gain_chars else float("nan")
            star = "*" if abs(dcer) > dcer_h else " "
            print(f"{lab:>11s} {len(idx):5d} {b['_chars']:6d} | {b['cer'][0]:9.2f}% "
                  f"{a['cer'][0]:8.2f}% {-dcer:+9.2f}±{dcer_h:5.2f}{star} | "
                  f"{b['tone'][0]:10.2f}% {a['tone'][0]:9.2f}% {dton:+8.2f}±{dton_h:5.2f} | "
                  f"{share:7.1f}%")
            rows.append(dict(bin=lab, n=len(idx), chars=b["_chars"],
                             cer_before=b["cer"], cer_after=a["cer"],
                             d_cer=-dcer, d_cer_ci=dcer_h,
                             tone_before=b["tone"], tone_after=a["tone"],
                             d_tone=dton, d_tone_ci=dton_h,
                             chars_fixed=fixed, gain_share_pct=share))
        res["strata"][key] = dict(knob=knob, bins=rows)
        print(f"{'':11s} (* = ΔCER clears its own 95% CI; 'share of the gain' = this bin's chars fixed "
              f"/ all chars fixed)")

    # ------------------------------------------------- the LENGTH result, made mechanistic
    # The length stratum dominates the gain, so it gets a direct diagnostic rather than a story:
    # is the scarce-budget model TRUNCATING long sequences (premature <eos>), and does the
    # synthetic fix that? Predicted-vs-GT length answers it without hand-waving.
    long_idx = [j for j, f in enumerate(feats) if f["length"] >= 9]
    print(f"\n### TRUNCATION DIAGNOSTIC on long crops (>=9 chars, n={len(long_idx)})")
    print(f"{'arm':>8s} {'mean GT len':>12s} {'mean PRED len':>14s} {'severely truncated':>19s}")
    trunc = {}
    for arm in ARMS:
        gl, pl, tr = [], [], 0
        for s in SEEDS:
            for j in long_idx:
                gt, pr = preds[arm][s][j]
                gl.append(len(gt))
                pl.append(len(pr))
                tr += len(pr) < 0.6 * len(gt)
        n = len(long_idx) * len(SEEDS)
        trunc[arm] = dict(gt_len=st.mean(gl), pred_len=st.mean(pl), trunc_pct=100.0 * tr / n)
        print(f"{arm:>8s} {trunc[arm]['gt_len']:12.2f} {trunc[arm]['pred_len']:14.2f} "
              f"{trunc[arm]['trunc_pct']:18.1f}%")
    print("  (severely truncated = predicted length < 60% of GT length)")
    res["truncation_long_crops"] = dict(n=len(long_idx), threshold_chars=9, arms=trunc)

    with open("runs/c4_before_after_r10.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 100)
    print("READ IT HONESTLY (pre-stated): gain concentrated on TONE + small/low-contrast/tilted crops")
    print("=> the engine hit the MEASURED failure strata (mechanism confirmed). Gain UNIFORM across")
    print("axes and strata => the synthetic is a GENERIC PRIOR at a scarce budget, not targeted domain")
    print("transfer -- a real gain, but a DIFFERENT mechanism, and the write-up must say so.")
    print("BRAIN CHECKPOINT: report the table; do not declare the mechanism here.")
    print("\nwrote runs/c4_before_after_r10.json")


if __name__ == "__main__":
    main()
