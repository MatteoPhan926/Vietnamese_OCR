"""EVAL_PROTOCOL §14.4(A) — the clean-render control: the ATTRIBUTION SPLIT.

Three arms at the headline point r=10%, all from the same pretrained checkpoint, same HP/iters:
  real-only            (k=5)  -- the comparator
  + STRICT synth       (k=5)  -- the shipped generator (degradation stack ON). THE HEADLINE.
  + CLEAN synth        (k=3)  -- identical set with the ENTIRE degradation stack OFF (the control)

The question: is the +2.783 pp bought by the ENGINE'S REALISM MACHINERY, or would ANY 10k of extra
crops buy it (a decoder-training-signal effect)?

`[LOCKED, pre-registered §14.4(A) BEFORE the control ran -- not renegotiable after seeing it]`
  clean recovers >= ~80% of the gain -> realism NOT load-bearing here; the claim is label-efficiency
    via decoder-training signal (premature-<eos> repair).
  clean recovers <  ~50%             -> the degradations ARE load-bearing; the domain-transfer
    framing survives alongside the decoder mechanism.
  in between                         -> report the measured split, and nothing more.

This is an ABLATION FOR ATTRIBUTION of an already-green result. It is NOT a §8.1 re-gate attempt,
and the headline (+2.783, strict, k=5) does not move regardless of the outcome.
"""
import glob
import json
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")

T_BY_DOF = {2: 4.302652729911275, 4: 2.776445105198166}
METRICS = [("cer", "CER", True), ("axis3_tone", "tone", False), ("axis1_base", "base", False),
           ("axis2_modifier", "modifier", False), ("exact", "exact", False), ("wer", "WER", True)]


def load(pattern):
    res = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(pattern))]
    if res:
        assert all(r["n_instances"] == 10068 and r["n_chars"] == 37254 for r in res), \
            "DENOMINATOR DRIFT -- a run scored a different test set. Stop."
    return res


def ci(vals):
    m = st.mean(vals)
    if len(vals) < 2:
        return m, float("nan")
    return m, T_BY_DOF[len(vals) - 1] * st.stdev(vals) / len(vals) ** 0.5


def overlap(a, b):
    (am, ah), (bm, bh) = a, b
    return not (am + ah < bm - bh or bm + bh < am - ah)


def main():
    arms = {
        "real-only": load("runs/budget_r10_real_seed[0-9]/result.json"),
        "+STRICT synth (shipped, degradation ON)": load("runs/budget_r10_strict_seed[0-9]/result.json"),
        "+CLEAN synth (CONTROL, degradation OFF)": load("runs/budget_r10_clean_seed[0-9]/result.json"),
    }
    missing = [k for k, v in arms.items() if not v]
    if missing:
        raise SystemExit(f"no runs for: {missing}")

    stats = {k: {m: ci([x[m] * 100 for x in v]) for m, _, _ in METRICS} for k, v in arms.items()}
    ks = {k: len(v) for k, v in arms.items()}

    print("=" * 104)
    print("§14.4(A) CLEAN-RENDER CONTROL — attribution at the headline point r=10% (2,574 real crops)")
    print("rec-only · VinText test-500 real held-out · NFC (CER/WER) / NFD (axes) · frozen denominator")
    print("=" * 104)
    print(f"\n{'arm':>42s} {'k':>2s} | {'CER':>15s} {'tone':>15s} {'base':>15s} {'modifier':>15s}")
    for k in arms:
        s = stats[k]
        print(f"{k:>42s} {ks[k]:2d} | {s['cer'][0]:8.3f}±{s['cer'][1]:5.3f} "
              f"{s['axis3_tone'][0]:8.3f}±{s['axis3_tone'][1]:5.3f} "
              f"{s['axis1_base'][0]:8.3f}±{s['axis1_base'][1]:5.3f} "
              f"{s['axis2_modifier'][0]:8.3f}±{s['axis2_modifier'][1]:5.3f}")

    ro = stats["real-only"]
    sh = stats["+STRICT synth (shipped, degradation ON)"]
    cl = stats["+CLEAN synth (CONTROL, degradation OFF)"]

    print("\nGAIN OVER REAL-ONLY (positive = better):")
    out = {}
    for key, label in (("cer", "CER"), ("axis3_tone", "tone")):
        sign = 1 if key == "cer" else -1          # CER: lower is better
        g_ship = sign * (ro[key][0] - sh[key][0])
        g_ctrl = sign * (ro[key][0] - cl[key][0])
        rec = 100.0 * g_ctrl / g_ship if g_ship else float("nan")
        sep_ship = not overlap(ro[key], sh[key])
        sep_ctrl = not overlap(ro[key], cl[key])
        print(f"  {label:>5s}: shipped {g_ship:+7.3f} ({'sep' if sep_ship else 'overlap'})   "
              f"control {g_ctrl:+7.3f} ({'sep' if sep_ctrl else 'overlap'})   "
              f"=> the CONTROL recovers {rec:5.1f}% of the shipped gain")
        out[label] = dict(gain_shipped=g_ship, gain_control=g_ctrl, recovered_pct=rec,
                          shipped_separated=sep_ship, control_separated=sep_ctrl)

    # Is shipped BETTER than clean? (does the degradation stack add anything on top of the control?)
    print("\nSHIPPED vs CONTROL, head to head (does the degradation stack add anything?):")
    for key, label in (("cer", "CER"), ("axis3_tone", "tone")):
        sign = 1 if key == "cer" else -1
        d = sign * (cl[key][0] - sh[key][0])       # + = shipped better than clean
        sep = not overlap(cl[key], sh[key])
        print(f"  {label:>5s}: shipped − control = {d:+7.3f}  CIs {'SEPARATED' if sep else 'OVERLAP'}"
              f"  -> degradation stack {'ADDS a measurable amount' if sep and d > 0 else 'adds nothing that clears noise'}")
        out[label]["shipped_minus_control"] = d
        out[label]["shipped_vs_control_separated"] = sep

    rec_cer = out["CER"]["recovered_pct"]
    print("\n" + "=" * 104)
    print("`[LOCKED]` PRE-REGISTERED READING (§14.4(A), fixed BEFORE this ran):")
    if rec_cer >= 80:
        print(f"  control recovers {rec_cer:.1f}% >= ~80%  =>  THE REALISM MACHINERY IS NOT LOAD-BEARING")
        print("  at this operating point. The honest claim is LABEL-EFFICIENCY VIA DECODER-TRAINING")
        print("  SIGNAL (premature-<eos> repair, C4), NOT domain transfer. The write-up must say so.")
    elif rec_cer < 50:
        print(f"  control recovers {rec_cer:.1f}% < ~50%  =>  THE DEGRADATIONS ARE LOAD-BEARING. The")
        print("  domain-transfer framing SURVIVES, alongside the C4 decoder mechanism.")
    else:
        print(f"  control recovers {rec_cer:.1f}% — BETWEEN the pre-registered thresholds (50%..80%).")
        print("  Report the measured split and nothing beyond it: the degradations carry part of the")
        print("  gain and a generic-prior effect carries the rest.")
    print("\nThe HEADLINE (+2.783 pp, strict bank, k=5) is UNAFFECTED by this control -- it is an")
    print("attribution ablation, not a re-gate (§8.1 attempts are untouched).")
    print("BRAIN CHECKPOINT: report the split; do not rewrite the claim here.")

    json.dump(dict(arms={k: {m: stats[k][m] for m, _, _ in METRICS} for k in arms},
                   k={k: ks[k] for k in arms}, attribution=out),
              open("runs/control_clean_summary.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote runs/control_clean_summary.json")


if __name__ == "__main__":
    main()
