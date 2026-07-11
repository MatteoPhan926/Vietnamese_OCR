"""Aggregate the THREE-ARM Attempt-1 experiment (DATA_ENGINE §8.4, EVAL_PROTOCOL §15).

  A = real + default aug            (Stage-0 baseline)
  B = real + strata-targeted aug    (CONTROL -- raises the comparator; not a re-gate attempt)
  C = real + same aug + strata-targeted synthetic   (Attempt 1)

Reports:
  B - A  = what AUGMENTATION ALONE buys.
  C - B  = the PURE SYNTHETIC contribution AT MATCHED AUGMENTATION -- the only honest answer to
           "was generating the synthetic worth it?"  (§15: judge C against the STRONGEST real-only
           config, never against an under-augmented A. The bar may be RAISED, never lowered.)

Gate-A decision rule is UNCHANGED (§7, pre-registered): GREEN = the synth arm's 95% CI does NOT
overlap the comparator's, on BOTH CER and the Axis-3 tone axis, over k=3 seeds (Student t, 2 dof).

This script REPORTS. It does not declare the gate -- that is a BRAIN CHECKPOINT.
"""
import glob
import json
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
T = 4.302652729911275  # Student t, 2 dof, 95%

METRICS = [
    ("cer", "CER", True), ("wer", "WER", True), ("exact", "exact-match", False),
    ("axis1_base", "Axis1 base", False), ("axis2_modifier", "Axis2 modifier", False),
    ("axis3_tone", "Axis3 tone", False),
]


def ci(vals):
    m = st.mean(vals)
    if len(vals) < 2:
        return m, float("nan")
    return m, T * st.stdev(vals) / (len(vals) ** 0.5)


def overlap(a, b):
    (am, ah), (bm, bh) = a, b
    return not (am + ah < bm - bh or bm + bh < am - ah)


def load_arm(pattern):
    files = sorted(glob.glob(pattern))
    res = [json.load(open(f, encoding="utf-8")) for f in files]
    if not res:
        return None
    assert all(r["n_instances"] == 10068 and r["n_chars"] == 37254 for r in res), \
        "DENOMINATOR DRIFT -- an arm scored a different test set. Stop."
    return res


def stats_of(res, key):
    vals = [r[key] * 100 for r in res]
    return ci(vals), vals


def main():
    base = json.load(open("runs/baseline_k3_summary.json", encoding="utf-8"))
    B = load_arm("runs/armB_seed[0-9]/result.json")
    C = load_arm("runs/armC_seed[0-9]/result.json")
    if not B or not C:
        raise SystemExit(f"need both arms; have B={len(B or [])} C={len(C or [])}")

    print("THREE-ARM ATTEMPT 1 (DATA_ENGINE §8.4)   rec-only · VinText test-500 · NFC/axes-NFD")
    print(f"n=10,068 instances / 37,254 chars (frozen)   iters={C[0]['iters']} FIXED   k=3 seeds")
    print(f"  A = real + DEFAULT aug            (n_real={C[0]['n_real']})")
    print(f"  B = real + STRATA aug, NO synth   (control, same augmentor as C)")
    print(f"  C = real + STRATA aug + {C[0]['n_synth']} strata-targeted synth ({C[0]['synth_set']})\n")

    rows = {}
    hdr = f"{'metric':16s} {'A (baseline)':>18s} {'B (strata aug)':>18s} {'C (aug+synth)':>18s} " \
          f"{'B−A':>9s} {'C−B':>9s}"
    print(hdr)
    print("-" * len(hdr))
    for key, label, lower in METRICS:
        am, ah = base["metrics"][key]["mean"], base["metrics"][key]["ci95_half"]
        (bm, bh), _ = stats_of(B, key)
        (cm, ch), _ = stats_of(C, key)
        ba, cb = bm - am, cm - bm
        print(f"{label:16s} {am:10.3f}±{ah:6.3f} {bm:10.3f}±{bh:6.3f} {cm:10.3f}±{ch:6.3f} "
              f"{ba:+9.3f} {cb:+9.3f}")
        rows[key] = dict(A=(am, ah), B=(bm, bh), C=(cm, ch), B_minus_A=ba, C_minus_B=cb,
                         lower_is_better=lower)

    def verdict(key, against="B"):
        r = rows[key]
        lower = r["lower_is_better"]
        d = r["C"][0] - r[against][0]
        improved = (d < 0) if lower else (d > 0)
        sep = not overlap(r["C"], r[against])
        return improved, sep

    def strongest(key):
        """§15: the comparator is the STRONGEST real-only config. Measured per metric, because
        B did NOT come out uniformly stronger than A (it improves the axes but worsens CER/WER)."""
        r = rows[key]
        if r["lower_is_better"]:
            return "A" if r["A"][0] <= r["B"][0] else "B"
        return "A" if r["A"][0] >= r["B"][0] else "B"

    print("\n" + "=" * 84)
    print("§15 — WHICH ARM IS THE COMPARATOR? (the STRONGEST real-only config; bar RAISED never lowered)")
    a_cer, b_cer = rows["cer"]["A"][0], rows["cer"]["B"][0]
    a_tone, b_tone = rows["axis3_tone"]["A"][0], rows["axis3_tone"]["B"][0]
    print(f"  CER : A {a_cer:.3f}  vs  B {b_cer:.3f}   -> B is {'STRONGER' if b_cer < a_cer else 'WEAKER'} on CER")
    print(f"  tone: A {a_tone:.3f}  vs  B {b_tone:.3f}   -> B is {'STRONGER' if b_tone > a_tone else 'WEAKER'} on tone")

    print("\nB − A  (what AUGMENTATION ALONE buys, no synthetic):")
    for key, label, _ in METRICS:
        print(f"  {label:16s} {rows[key]['B_minus_A']:+8.3f} pp")
    print("\nC − B  (the PURE SYNTHETIC contribution at MATCHED augmentation):")
    for key, label, _ in METRICS:
        r = rows[key]
        imp, sep = verdict(key, "B")
        print(f"  {label:16s} {r['C_minus_B']:+8.3f} pp   {'improves' if imp else 'no gain':9s}  "
              f"CIs {'SEPARATED' if sep else 'overlap'}")

    print("\n" + "=" * 84)
    print("GATE-A vs the STRONGEST real-only comparator PER METRIC (§15: bar RAISED, never lowered).")
    print("NOTE: B is NOT uniformly stronger than A -- it improves the three axes but worsens CER/WER,")
    print("so the strictest honest comparator is the better of {A, B} on each metric.")
    ok_all = True
    for key, label, _ in METRICS:
        s = strongest(key)
        imp, sep = verdict(key, s)
        if key in ("cer", "axis3_tone"):
            ok_all = ok_all and imp and sep
        print(f"  {label:16s} comparator={s}  C−{s} = {rows[key]['C'][0]-rows[key][s][0]:+7.3f} pp  "
              f"{'improves' if imp else 'no gain':9s}  CIs {'SEPARATED' if sep else 'overlap'}")

    print("\n" + "=" * 84)
    print("PRE-REGISTERED GATE-A CONDITION (§7, unchanged) — REPORTED, NOT self-adjudicated:")
    for key, label in (("cer", "CER"), ("axis3_tone", "tone")):
        s = strongest(key)
        imp, sep = verdict(key, s)
        print(f"  C vs {s} — {label:5s}: improved AND CIs separated? {'YES' if (imp and sep) else 'NO'}")
    print(f"  -> met on BOTH CER and tone: {'YES' if ok_all else 'NO'}")
    print("=" * 84)
    print("Outcome map (§8.4): C>B = synth adds what aug cannot | C~B>A = 'just augment harder'")
    print("(strong negative result) | C~B~A = strata resist both -> EVAL_PROTOCOL §14 label-efficiency axis.")
    print("BRAIN CHECKPOINT: report to the design brain. Do not declare the gate here.")

    json.dump(rows, open("runs/three_arm_summary.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote runs/three_arm_summary.json")


if __name__ == "__main__":
    main()
