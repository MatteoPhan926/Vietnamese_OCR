"""Aggregate the k=3 Gate-A seeds and apply the PRE-REGISTERED decision rule (EVAL_PROTOCOL §7).

Gate A GREEN (rule fixed in §7 BEFORE any synthetic result existed, and NOT re-derived here):
  the synth-augmented run's 95% CI does NOT overlap the real-only baseline's, on BOTH
  CER and the Axis-3 tone accuracy. This is a seed-noise significance test over k=3 seeds
  (Student t, 2 dof), the same machinery that froze the noise floor (aggregate_baseline.py).

This script REPORTS the evidence and states mechanically whether the non-overlap condition
is met. It does NOT declare the project's gate green/red — that is a BRAIN CHECKPOINT
(BUILD_PLAN Stage 2). The brain adjudicates whether green is real and what a red means.
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


def overlap(a_lo, a_hi, b_lo, b_hi):
    return not (a_hi < b_lo or b_hi < a_lo)


def main():
    files = sorted(glob.glob("runs/gateA_synth10k_seed[0-9]/result.json"))
    res = [json.load(open(f, encoding="utf-8")) for f in files]
    if len(res) < 2:
        raise SystemExit(f"need >=2 gateA seeds, found {len(res)}")
    base = json.load(open("runs/baseline_k3_summary.json", encoding="utf-8"))

    seeds = [r["seed"] for r in res]
    print(f"GATE A  real + {res[0]['condition'].split('+')[1]}   k={len(res)} seeds {seeds}")
    print(f"scope={res[0]['scope']}  testset={res[0]['testset']}  norm={res[0]['normalization']}")
    assert all(r["n_instances"] == 10068 and r["n_chars"] == 37254 for r in res), \
        "DENOMINATOR DRIFT -- a seed scored a different test set. Stop."
    assert all(r["hp"] == res[0]["hp"] for r in res), "HP drift across seeds"
    print(f"n={res[0]['n_instances']}/{res[0]['n_chars']}  real={res[0]['n_real']} synth={res[0]['n_synth']}  "
          f"iters={res[0]['iters']} (FIXED = baseline)\n")

    print(f"{'metric':16s} {'baseline mean±CI':>22s}   {'gateA mean±CI':>22s}   {'Δ(gateA-base)':>13s}  overlap?")
    summary = {}
    for key, label, lower in METRICS:
        gvals = [r[key] * 100 for r in res]
        gm, gh = ci(gvals)
        bm = base["metrics"][key]["mean"]
        bh = base["metrics"][key]["ci95_half"]
        ov = overlap(gm - gh, gm + gh, bm - bh, bm + bh)
        delta = gm - bm
        better = (delta < 0) if lower else (delta > 0)
        print(f"{label:16s} {bm:10.3f} ± {bh:7.3f}   {gm:10.3f} ± {gh:7.3f}   "
              f"{delta:+9.3f} {'✓' if better else '✗'}   {'OVERLAP' if ov else 'separated'}")
        summary[key] = dict(base_mean=bm, base_ci=bh, gate_mean=gm, gate_ci=gh,
                            gate_seeds=gvals, delta=delta, overlap=ov, improved=better)

    cer_sep = not summary["cer"]["overlap"] and summary["cer"]["improved"]
    tone_sep = not summary["axis3_tone"]["overlap"] and summary["axis3_tone"]["improved"]
    print("\n" + "=" * 82)
    print("PRE-REGISTERED GATE-A CONDITION (EVAL_PROTOCOL §7) — reported, NOT self-adjudicated:")
    print(f"  CER  : improved AND CIs separated ? {'YES' if cer_sep else 'NO'}  "
          f"(Δ={summary['cer']['delta']:+.3f} pp; need ~≥0.7 pp per frozen floor E11)")
    print(f"  tone : improved AND CIs separated ? {'YES' if tone_sep else 'NO'}  "
          f"(Δ={summary['axis3_tone']['delta']:+.3f} pp)")
    print(f"  -> non-overlap condition met on BOTH: {'YES' if (cer_sep and tone_sep) else 'NO'}")
    print("=" * 82)
    print("This is a BRAIN CHECKPOINT. Report to the design brain; do not start Stage 3 or")
    print("declare the gate here. RED -> DATA_ENGINE §8 re-diagnosis (degradation-first), re-gate at 10k.")

    json.dump(dict(k=len(res), seeds=seeds, metrics=summary,
                   condition_met=dict(cer=cer_sep, tone=tone_sep, both=cer_sep and tone_sep)),
              open("runs/gateA_synth10k_summary.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote runs/gateA_synth10k_summary.json")


if __name__ == "__main__":
    main()
