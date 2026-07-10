"""Stage 0.5 — aggregate the k=3 real-only baseline seeds and FREEZE the Gate-A noise floor.

EVAL_PROTOCOL §7 [VERIFY->FREEZE @ Stage 0]:
  "Measure the real-only baseline's run-to-run std over k=3 seeds and FREEZE it. This is the
   yardstick Gate A is judged against."
and §3: "Every number that has run-to-run variance is reported as median + spread over k=3
seeds, not best-of-N. Best-of-N is a silent lie."

The Gate-A DECISION RULE is fixed by §7 *before* this measurement and is not re-derived from
it: GREEN = the synth-augmented improvement's CI over k=3 seeds does not overlap the
real-only baseline's, on BOTH CER and the tone axis. This script only supplies the floor's
VALUE; deriving the rule from the value would be the post-hoc rule-tuning §12 forbids.

With k=3 the 95% CI uses Student's t with 2 dof (t=4.303) -- deliberately wide. The min-max
range is reported alongside, because a 3-sample CI is a weak object and pretending otherwise
would be its own over-claim.
"""
import glob
import json
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")

T_CRIT_2DOF_95 = 4.302652729911275

METRICS = [
    ("cer", "CER", True),                    # lower is better
    ("wer", "WER", True),
    ("exact", "exact-match", False),
    ("axis1_base", "Axis1 base", False),
    ("axis2_modifier", "Axis2 modifier", False),
    ("axis3_tone", "Axis3 tone", False),
]


def ci95(vals):
    """mean, half-width of the 95% CI (t, 2 dof). Returns (mean, half) in the same units."""
    m = st.mean(vals)
    if len(vals) < 2:
        return m, float("nan")
    s = st.stdev(vals)  # sample std, n-1
    return m, T_CRIT_2DOF_95 * s / (len(vals) ** 0.5)


def main():
    files = sorted(glob.glob("runs/baseline_seed[0-9]/result.json"))
    files = [f for f in files if "seed99" not in f]
    res = [json.load(open(f, encoding="utf-8")) for f in files]
    if not res:
        raise SystemExit("no baseline results found")

    seeds = [r["seed"] for r in res]
    print(f"REAL-ONLY BASELINE  k={len(res)} seeds {seeds}")
    r0 = res[0]
    print(f"scope={r0['scope']}  testset={r0['testset']}  norm={r0['normalization']}")
    print(f"n={r0['n_instances']} instances / {r0['n_chars']} NFC chars   "
          f"(frozen denominator: 10,068 / 37,254)")
    assert all(r["n_instances"] == 10068 and r["n_chars"] == 37254 for r in res), \
        "DENOMINATOR DRIFT -- a seed scored a different test set. Stop."
    print(f"train crops={r0['train_crops']}  iters={r0['iters']}  hp fixed across seeds: "
          f"{all(r['hp'] == r0['hp'] for r in res)}\n")

    print(f"{'metric':16s} " + " ".join(f"seed{s:<7d}" for s in seeds) +
          f"{'median':>10s} {'std':>8s} {'mean':>9s} {'95% CI +/-':>11s} {'range':>9s}")
    summary = {}
    for key, label, _lower in METRICS:
        vals = [r[key] * 100 for r in res]
        med = st.median(vals)
        sd = st.stdev(vals) if len(vals) > 1 else float("nan")
        mean, half = ci95(vals)
        rng = max(vals) - min(vals)
        print(f"{label:16s} " + " ".join(f"{v:11.3f}" for v in vals) +
              f"{med:10.3f} {sd:8.3f} {mean:9.3f} {half:11.3f} {rng:9.3f}")
        summary[key] = dict(seeds=vals, median=med, std=sd, mean=mean, ci95_half=half, range=rng)

    print()
    print("=" * 78)
    print("GATE-A NOISE FLOOR  [VERIFY->FREEZE @ Stage 0]  (EVAL_PROTOCOL §7)")
    print(f"  run-to-run std of rec-only CER on test-500, k=3 seeds : "
          f"{summary['cer']['std']:.3f} pp (absolute)")
    print(f"  run-to-run std of Axis3 tone accuracy                 : "
          f"{summary['axis3_tone']['std']:.3f} pp")
    print(f"  baseline CER  median {summary['cer']['median']:.3f}%   "
          f"mean {summary['cer']['mean']:.3f}% ± {summary['cer']['ci95_half']:.3f} (95% CI, t, 2 dof)")
    print(f"  baseline tone median {summary['axis3_tone']['median']:.3f}%   "
          f"mean {summary['axis3_tone']['mean']:.3f}% ± {summary['axis3_tone']['ci95_half']:.3f}")
    print("=" * 78)
    print("Gate A is GREEN only if the synth-augmented run's 95% CI does NOT overlap the")
    print("baseline's, on BOTH CER and the tone axis (rule pre-registered in §7, not derived here).")
    print("A brain checkpoint adjudicates. This script does not declare a gate.")

    with open("runs/baseline_k3_summary.json", "w", encoding="utf-8") as f:
        json.dump(dict(
            k=len(res), seeds=seeds, scope=r0["scope"], testset=r0["testset"],
            n_instances=r0["n_instances"], n_chars=r0["n_chars"], hp=r0["hp"],
            metrics=summary,
            noise_floor=dict(
                cer_std_pp=summary["cer"]["std"],
                tone_std_pp=summary["axis3_tone"]["std"],
                cer_ci95_half_pp=summary["cer"]["ci95_half"],
                tone_ci95_half_pp=summary["axis3_tone"]["ci95_half"],
                note="k=3, Student t 2dof. Gate-A rule (non-overlapping CI) pre-registered in §7.",
            ),
        ), f, indent=2)
    print("\nwrote runs/baseline_k3_summary.json")


if __name__ == "__main__":
    main()
