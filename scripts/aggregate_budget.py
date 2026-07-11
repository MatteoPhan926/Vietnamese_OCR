"""The §14 LABEL-EFFICIENCY CURVE + the pre-registered readout (EVAL_PROTOCOL §14 / §14.1).

Deliverable: the GAP between real-only(r) and real(r)+synth as a function of the real-data
budget r -- i.e. **how much real annotation can this synthetic replace?**

`[LOCKED]` readout (§14.1): *"synthetic ~ worth N real crops at budget r"* -- invert the
real-only-vs-r curve (LINEAR IN log r between adjacent MEASURED points, NEVER extrapolated
beyond the measured range) to find r' where real-only(r') matches real(r)+synth;
N = (r' - r) x 25,742.

`[LOCKED]` per-point rule, unchanged (§7): non-overlapping 95% CI over k=3 seeds, on CER AND tone.
A green at r<100% is a LABEL-EFFICIENCY claim for that budget ONLY -- never a full-real claim.
The r=100% null (C≈B; synthetic adds nothing at full real data) keeps FULL prominence.

Reuse (§14.1): r=100% real-only = the Stage-0 baseline (A); r=100% +synth = the hygiene re-gate
(synth10k_leg) run. This script does NOT declare a gate -- the curve is a BRAIN CHECKPOINT.
"""
import glob
import json
import math
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")

T = 4.302652729911275   # Student t, 2 dof, 95%
N_FULL = 25742          # the full real train split (frozen, EVAL_PROTOCOL §13 E1)
RS = [10, 25, 50, 100]
METRICS = [("cer", "CER", True), ("axis3_tone", "tone", False),
           ("axis1_base", "base", False), ("axis2_modifier", "modifier", False),
           ("exact", "exact", False), ("wer", "WER", True)]


def ci(vals):
    m = st.mean(vals)
    if len(vals) < 2:
        return m, float("nan")
    return m, T * st.stdev(vals) / (len(vals) ** 0.5)


def load(pattern):
    files = sorted(glob.glob(pattern))
    res = [json.load(open(f, encoding="utf-8")) for f in files]
    if res:
        assert all(r["n_instances"] == 10068 and r["n_chars"] == 37254 for r in res), \
            "DENOMINATOR DRIFT -- a run scored a different test set. Stop."
    return res


def arm_runs(r, arm):
    """r=100% is REUSED per §14.1: real -> Stage-0 baseline A; synth -> the leg re-gate run."""
    if r == 100:
        return load("runs/baseline_seed[0-9]/result.json" if arm == "real"
                    else "runs/gateA_synth10k_leg_seed[0-9]/result.json")
    return load(f"runs/budget_r{r}_{arm}_seed[0-9]/result.json")


def overlap(a, b):
    (am, ah), (bm, bh) = a, b
    return not (am + ah < bm - bh or bm + bh < am - ah)


def invert_realonly(curve, y):
    """Find r' where the real-only curve reaches CER y. Linear in log r between adjacent
    MEASURED points; returns None if y falls outside the measured range (never extrapolate)."""
    pts = sorted((r, curve[r]) for r in curve)          # r ascending; CER descending
    ys = [p[1] for p in pts]
    if y > ys[0] or y < ys[-1]:
        return None                                     # outside measured range
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        lo, hi = min(y0, y1), max(y0, y1)
        if lo <= y <= hi and y0 != y1:
            t = (y - y0) / (y1 - y0)
            return math.exp(math.log(r0) + t * (math.log(r1) - math.log(r0)))
    return None


def main():
    data = {}
    for r in RS:
        for arm in ("real", "synth"):
            runs = arm_runs(r, arm)
            if not runs:
                continue
            data[(r, arm)] = {k: ci([x[k] * 100 for x in runs]) for k, _, _ in METRICS}
            data[(r, arm)]["_n"] = len(runs)
            data[(r, arm)]["_n_real"] = runs[0].get("n_real", N_FULL)

    print("§14 LABEL-EFFICIENCY CURVE — rec-only · VinText test-500 · NFC/axes-NFD · frozen denom")
    print("§6 operating config (DEFAULT aug) · iters=12,000 FIXED · uniform pooled sampling · k=3\n")
    print(f"{'r':>5s} {'real crops':>11s} | {'real-only CER':>16s} {'real+synth CER':>16s} "
          f"{'GAP(CER)':>9s} | {'real-only tone':>15s} {'real+synth tone':>16s} {'GAP':>7s}")
    print("-" * 108)

    realonly_cer = {}
    rows = {}
    for r in RS:
        if (r, "real") not in data:
            continue
        ro = data[(r, "real")]
        realonly_cer[r] = ro["cer"][0]
        n_real = ro["_n_real"]
        if (r, "synth") not in data:
            print(f"{r:4d}% {n_real:11d} | {ro['cer'][0]:8.3f}±{ro['cer'][1]:.3f} "
                  f"{'(pending)':>16s}")
            continue
        sy = data[(r, "synth")]
        gap_cer = ro["cer"][0] - sy["cer"][0]        # >0 = synth reduces CER (helps)
        gap_tone = sy["axis3_tone"][0] - ro["axis3_tone"][0]   # >0 = synth improves tone
        print(f"{r:4d}% {n_real:11d} | {ro['cer'][0]:8.3f}±{ro['cer'][1]:5.3f} "
              f"{sy['cer'][0]:8.3f}±{sy['cer'][1]:5.3f} {gap_cer:+9.3f} | "
              f"{ro['axis3_tone'][0]:7.3f}±{ro['axis3_tone'][1]:5.3f} "
              f"{sy['axis3_tone'][0]:8.3f}±{sy['axis3_tone'][1]:5.3f} {gap_tone:+7.3f}")
        rows[r] = dict(gap_cer=gap_cer, gap_tone=gap_tone,
                       cer_sep=not overlap(ro["cer"], sy["cer"]),
                       tone_sep=not overlap(ro["axis3_tone"], sy["axis3_tone"]),
                       real_only={k: data[(r, 'real')][k] for k, _, _ in METRICS},
                       real_synth={k: data[(r, 'synth')][k] for k, _, _ in METRICS},
                       n_real=n_real)

    print("\nPER-POINT GATE RULE (§7, unchanged): non-overlapping 95% CI on CER *and* tone")
    for r in sorted(rows):
        d = rows[r]
        cer_ok = d["cer_sep"] and d["gap_cer"] > 0
        tone_ok = d["tone_sep"] and d["gap_tone"] > 0
        print(f"  r={r:3d}%  CER: {'PASS' if cer_ok else 'no':4s} (Δ{d['gap_cer']:+.3f}, "
              f"CIs {'separated' if d['cer_sep'] else 'overlap'})   "
              f"tone: {'PASS' if tone_ok else 'no':4s} (Δ{d['gap_tone']:+.3f}, "
              f"CIs {'separated' if d['tone_sep'] else 'overlap'})   "
              f"=> {'GREEN' if (cer_ok and tone_ok) else 'red'}")

    if len(realonly_cer) >= 2:
        print("\n`[LOCKED]` PRE-REGISTERED READOUT (§14.1): \"synthetic ≈ worth N real crops at budget r\"")
        print("  (invert the real-only curve, linear in log r between MEASURED points; never extrapolated)")
        for r in sorted(rows):
            y = rows[r]["real_synth"]["cer"][0]      # CER achieved by real(r)+synth
            rp = invert_realonly(realonly_cer, y)
            if rp is None:
                print(f"  r={r:3d}%: real+synth CER {y:.3f} lies OUTSIDE the measured real-only "
                      f"range -> NOT extrapolated (no claim)")
                continue
            n = (rp - r) / 100.0 * N_FULL
            print(f"  r={r:3d}%: real+synth CER {y:.3f} == real-only at r'={rp:.1f}%  "
                  f"=> synthetic ≈ worth {n:+,.0f} real crops")

    print("\n" + "=" * 100)
    print("HONEST READING (§14, pre-committed): gap WIDENS as r shrinks -> synthetic substitutes for")
    print("labels. Gap FLAT at every r -> the generator produces no usable signal at any budget (a clean")
    print("negative result). r=100% IS a point on this curve and its RED is reported at full prominence.")
    print("NEVER claimable: 'synthetic improves Vietnamese OCR' — it did not, at full real data.")
    print("BRAIN CHECKPOINT: report the curve; do not declare it here.")

    json.dump({f"r{r}": rows[r] for r in rows},
              open("runs/budget_curve_summary.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote runs/budget_curve_summary.json")


if __name__ == "__main__":
    main()
