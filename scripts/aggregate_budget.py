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

# Student t, 95% two-sided, by dof = k-1. k is NOT always 3: §14.2 (C2) raises the r=10% headline
# point to k=5, where t(4 dof)=2.776 -- using the k=3 constant there would inflate the CI by ~55%
# and could manufacture a separation failure (or hide one). Keyed by dof, never hardcoded.
T_BY_DOF = {1: 12.706204736432095, 2: 4.302652729911275, 3: 3.182446305284263,
            4: 2.776445105198166, 5: 2.570581835636197, 6: 2.446911850791612,
            7: 2.364624251592785, 8: 2.306004135204166, 9: 2.262157162798205}
N_FULL = 25742          # the full real train split (frozen, EVAL_PROTOCOL §13 E1)
RS = [10, 25, 50, 100]
METRICS = [("cer", "CER", True), ("axis3_tone", "tone", False),
           ("axis1_base", "base", False), ("axis2_modifier", "modifier", False),
           ("exact", "exact", False), ("wer", "WER", True)]


def ci(vals):
    m = st.mean(vals)
    n = len(vals)
    if n < 2:
        return m, float("nan")
    t = T_BY_DOF[n - 1]
    return m, t * st.stdev(vals) / (n ** 0.5)


def load(pattern):
    files = sorted(glob.glob(pattern))
    res = [json.load(open(f, encoding="utf-8")) for f in files]
    if res:
        assert all(r["n_instances"] == 10068 and r["n_chars"] == 37254 for r in res), \
            "DENOMINATOR DRIFT -- a run scored a different test set. Stop."
    return res


def arm_runs(r, arm):
    """r=100% is REUSED per §14.1: real -> Stage-0 baseline A; synth -> the leg re-gate run.

    arm=strict (§14.2 C1) exists only at the green points r=10/25 -- Source B restricted to the
    r-subset's OWN transcripts. Per §14.2 the HEADLINE quotes this arm; `synth` (full train
    transcript bank) remains the pre-registered primary, reported with its caveat.
    """
    if arm == "strict" and r not in (10, 25):
        return []
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


ARMS = ("real", "synth", "strict")
LABEL = {"synth": "full-bank (§14.1 primary)", "strict": "STRICT-bank (§14.2 C1 — HEADLINE)"}


def worth(realonly_cer, r, cer_mean, cer_half):
    """§14.2 reporting rule: quote the worth as a RANGE, never a 4-digit point.

    Propagate the +synth arm's 95% CI through the §14.1 interpolation: invert the real-only curve
    at the arm's CER mean AND at both CI bounds. A LOWER CER inverts to a HIGHER r' (more real
    crops), so the CI's low end gives the optimistic N and its high end the pessimistic N.

    Stated limitation: only the +synth arm's CI is propagated. The real-only curve being inverted
    is taken at its per-point MEANS -- its own seed spread (notably r=10%, ±2.350) is NOT folded in,
    so this range is a LOWER bound on the true uncertainty, not a full error budget.
    """
    out = {}
    for tag, y in (("mean", cer_mean), ("hi", cer_mean + cer_half), ("lo", cer_mean - cer_half)):
        rp = invert_realonly(realonly_cer, y)
        out[tag] = None if rp is None else dict(r_prime=rp, n=(rp - r) / 100.0 * N_FULL)
    return out


def fmt_worth(w):
    if w["mean"] is None:
        return "OUTSIDE the measured real-only range -> NOT extrapolated (no claim)"
    m = w["mean"]["n"]
    lo, hi = w["lo"], w["hi"]
    if lo is None or hi is None:
        return (f"≈ {m:+,.0f} real crops (r'={w['mean']['r_prime']:.1f}%); a CI bound falls "
                f"outside the measured range -> range truncated, not extrapolated")
    return (f"≈ {m:+,.0f} real crops (r'={w['mean']['r_prime']:.1f}%), "
            f"95% CI range [{hi['n']:+,.0f} .. {lo['n']:+,.0f}]")


def main():
    data = {}
    for r in RS:
        for arm in ARMS:
            runs = arm_runs(r, arm)
            if not runs:
                continue
            data[(r, arm)] = {k: ci([x[k] * 100 for x in runs]) for k, _, _ in METRICS}
            data[(r, arm)]["_n"] = len(runs)
            data[(r, arm)]["_n_real"] = runs[0].get("n_real", N_FULL)

    print("§14 LABEL-EFFICIENCY CURVE — rec-only · VinText test-500 · NFC/axes-NFD · frozen denom")
    print("§6 operating config (DEFAULT aug) · iters=12,000 FIXED · uniform pooled sampling\n")
    print("ARMS: real-only(r)  |  +synth full-bank (§14.1 primary)  |  +synth STRICT-bank (§14.2 C1)")
    print("  STRICT = Source B drawn ONLY from the r-subset's own transcripts (transcripts ARE labels;")
    print("  a practitioner at budget r holds only r% of them). Per §14.2 the HEADLINE quotes STRICT.\n")

    hdr = (f"{'r':>5s} {'real crops':>11s} {'arm':>28s} {'k':>2s} | {'CER':>15s} "
           f"{'ΔCER':>8s} | {'tone':>15s} {'Δtone':>7s} | {'per-point rule':>14s}")
    print(hdr)
    print("-" * len(hdr))

    realonly_cer = {}
    rows = {}
    for r in RS:
        if (r, "real") not in data:
            continue
        ro = data[(r, "real")]
        realonly_cer[r] = ro["cer"][0]
        n_real = ro["_n_real"]
        print(f"{r:4d}% {n_real:11d} {'real-only':>28s} {ro['_n']:2d} | "
              f"{ro['cer'][0]:8.3f}±{ro['cer'][1]:5.3f} {'':>8s} | "
              f"{ro['axis3_tone'][0]:8.3f}±{ro['axis3_tone'][1]:5.3f} {'':>7s} | {'(comparator)':>14s}")
        rows[r] = dict(n_real=n_real, real_only={k: ro[k] for k, _, _ in METRICS}, k_real=ro["_n"])

        for arm in ("synth", "strict"):
            if (r, arm) not in data:
                continue
            sy = data[(r, arm)]
            gap_cer = ro["cer"][0] - sy["cer"][0]                   # >0 = synth reduces CER (helps)
            gap_tone = sy["axis3_tone"][0] - ro["axis3_tone"][0]    # >0 = synth improves tone
            cer_sep = not overlap(ro["cer"], sy["cer"])
            tone_sep = not overlap(ro["axis3_tone"], sy["axis3_tone"])
            green = cer_sep and gap_cer > 0 and tone_sep and gap_tone > 0
            print(f"{'':4s}  {'':11s} {LABEL[arm]:>28s} {sy['_n']:2d} | "
                  f"{sy['cer'][0]:8.3f}±{sy['cer'][1]:5.3f} {gap_cer:+8.3f} | "
                  f"{sy['axis3_tone'][0]:8.3f}±{sy['axis3_tone'][1]:5.3f} {gap_tone:+7.3f} | "
                  f"{'GREEN' if green else 'red':>14s}")
            rows[r][f"{arm}_arm"] = dict(
                gap_cer=gap_cer, gap_tone=gap_tone, cer_sep=cer_sep, tone_sep=tone_sep,
                green=green, k=sy["_n"], metrics={k: sy[k] for k, _, _ in METRICS})
        print()

    print("PER-POINT GATE RULE (§7, unchanged): non-overlapping 95% CI on CER *and* tone, both arms")
    for r in sorted(rows):
        for arm in ("synth", "strict"):
            d = rows[r].get(f"{arm}_arm")
            if not d:
                continue
            print(f"  r={r:3d}% {LABEL[arm]:>28s}  CER Δ{d['gap_cer']:+.3f} "
                  f"({'separated' if d['cer_sep'] else 'overlap'})   "
                  f"tone Δ{d['gap_tone']:+.3f} ({'separated' if d['tone_sep'] else 'overlap'})   "
                  f"=> {'GREEN' if d['green'] else 'red'}")

    if len(realonly_cer) >= 2:
        print("\n`[LOCKED]` PRE-REGISTERED READOUT (§14.1) + the §14.2 RANGE rule:")
        print("  \"synthetic ≈ worth N real crops at budget r\" — invert the real-only curve (linear in")
        print("  log r between MEASURED points, NEVER extrapolated); the CI of the +synth arm is")
        print("  propagated through the inversion. The real-only curve is inverted at its MEANS, so the")
        print("  range is a LOWER bound on the true uncertainty (its own seed spread is not folded in).")
        for r in sorted(rows):
            for arm in ("synth", "strict"):
                d = rows[r].get(f"{arm}_arm")
                if not d:
                    continue
                cm, ch = d["metrics"]["cer"]
                w = worth(realonly_cer, r, cm, ch)
                rows[r][f"{arm}_arm"]["worth"] = w
                print(f"  r={r:3d}% {LABEL[arm]:>28s}: CER {cm:.3f} -> {fmt_worth(w)}")

        # C1's actual question: how much of the full-bank gain survives the strict bank?
        print("\nC1 VERDICT (§14.2): does the low-budget value survive when Source B is held to the")
        print("  r-subset's OWN transcripts? (If strict kills a green, the value was carried by the")
        print("  in-domain TEXT BANK, not the renderer — reported at the same prominence.)")
        for r in sorted(rows):
            f_arm, s_arm = rows[r].get("synth_arm"), rows[r].get("strict_arm")
            if not (f_arm and s_arm):
                continue
            retained = 100.0 * s_arm["gap_cer"] / f_arm["gap_cer"] if f_arm["gap_cer"] else float("nan")
            print(f"  r={r:3d}%: full-bank gap {f_arm['gap_cer']:+.3f} -> strict gap "
                  f"{s_arm['gap_cer']:+.3f} pp  ({retained:.0f}% of the gain RETAINED)  "
                  f"strict verdict: {'GREEN' if s_arm['green'] else 'red'}")

    print("\n" + "=" * 100)
    print("§14.2 OBSERVATION-ONLY (never a mechanism claim): CI-width comparisons across arms at k=3")
    print("are themselves high-variance. The r=10% tightening is reportable as an OBSERVATION; the")
    print("cross-r 'stabilizer vs dead-weight' narrative is NOT (r=50% reverses it).")
    print("STATED LIMITATION: one fixed nested subset draw per r -> training-seed variance only;")
    print("subset-draw variance is UNQUANTIFIED (standard for label-efficiency curves; said out loud).")
    print()
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
