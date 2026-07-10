"""Stage 1 / ERROR_ANALYSIS Run 0 — the diagnostic instrument on the real-only baseline.

Implements ERROR_ANALYSIS §3 (three-axis breakdown + CER decomposition + confusion
matrices + per-class ranking) and §6 (pre-registered stratifications).

Input: runs/baseline_seed{N}/predictions.tsv  (GT<TAB>PRED, one per scorable test-500
instance, in iter_instances('test') order). Model checkpoints are not reloaded -- the
predictions are the frozen artifact of the k=3 baseline.

ANTI-CHERRY-PICK (§2 [LOCKED]): every breakdown below is reported. None is dropped for
being unflattering. Median + spread over k=3 seeds wherever the model varies.

§3.2 is THE kill-test for CLAUDE.md §5's "the dominant error class is diacritics, not base
characters" [CONJECTURE]. Axis ACCURACY is not the same as SHARE-OF-CER: an axis can be the
least accurate while contributing a minority of character errors, because the axes have
different denominators (only vowels bear tone; only {a,e,o,u,d} bear a modifier; every
letter has a base). This script measures the share directly.
"""
import argparse
import collections
import json
import statistics as st
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.scorer import align, decompose, nfc  # noqa: E402
from scripts.vintext import iter_instances  # noqa: E402

SEEDS = (0, 1, 2)


def load_preds(seed):
    rows = []
    with open(f"runs/baseline_seed{seed}/predictions.tsv", encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            gt, _, pred = ln.partition("\t")
            rows.append((gt, pred))
    return rows


def classify_sub(r, h):
    """Attribute one substitution (GT char r -> pred char h) to axes. Returns dict of flags."""
    dr, dh = decompose(r), decompose(h)
    base_diff = dr.base != dh.base
    base_diff_ci = dr.base.lower() != dh.base.lower()
    case_only = base_diff and not base_diff_ci
    mod_diff = dr.modifier != dh.modifier
    tone_diff = dr.tone != dh.tone
    return dict(dr=dr, dh=dh, base_diff=base_diff, base_diff_ci=base_diff_ci,
                case_only=case_only, mod_diff=mod_diff, tone_diff=tone_diff)


def decompose_cer(pairs):
    """ERROR_ANALYSIS §3.2. Returns counters over ALL CER edits."""
    c = collections.Counter()
    tone_cm = collections.Counter()
    mod_cm = collections.Counter()
    base_cm = collections.Counter()
    tone_class_err = collections.Counter()
    tone_class_n = collections.Counter()
    mod_class_err = collections.Counter()
    mod_class_n = collections.Counter()

    for gt_raw, pred_raw in pairs:
        gt, pred = nfc(gt_raw), nfc(pred_raw)
        ops, _ = align(gt, pred)
        for op, r, h in ops:
            if op == "eq":
                d = decompose(r)
                if d.bears_tone:
                    tone_class_n[d.tone] += 1
                if d.bears_modifier:
                    mod_class_n[d.modifier] += 1
                continue
            c["edits_total"] += 1
            if op == "del":
                c["del"] += 1
                d = decompose(r)
                if d.bears_tone:
                    tone_class_n[d.tone] += 1
                    tone_class_err[d.tone] += 1
                    tone_cm[(d.tone, "<del>")] += 1
                if d.bears_modifier:
                    mod_class_n[d.modifier] += 1
                    mod_class_err[d.modifier] += 1
                    mod_cm[(d.modifier, "<del>")] += 1
                continue
            if op == "ins":
                c["ins"] += 1
                continue

            # substitution
            c["sub"] += 1
            f = classify_sub(r, h)
            dr, dh = f["dr"], f["dh"]

            if dr.bears_tone:
                tone_class_n[dr.tone] += 1
                if f["tone_diff"]:
                    tone_class_err[dr.tone] += 1
                    tone_cm[(dr.tone, dh.tone)] += 1
            if dr.bears_modifier:
                mod_class_n[dr.modifier] += 1
                if f["mod_diff"]:
                    mod_class_err[dr.modifier] += 1
                    mod_cm[(dr.modifier, dh.modifier)] += 1
            if f["base_diff_ci"]:
                base_cm[(dr.base.lower(), dh.base.lower())] += 1

            # involvement (categories overlap by construction)
            if f["tone_diff"]:
                c["sub_involves_tone"] += 1
            if f["mod_diff"]:
                c["sub_involves_modifier"] += 1
            if f["base_diff_ci"]:
                c["sub_involves_base"] += 1
            if f["case_only"]:
                c["sub_involves_case_only"] += 1

            # PURE categories (exactly one axis differs). base uses case-insensitive
            # identity; a pure case flip is its own class.
            nd = sum([f["base_diff_ci"], f["mod_diff"], f["tone_diff"]])
            if nd == 0:
                c["sub_pure_case"] += 1          # only the case differs
            elif nd == 1:
                if f["tone_diff"]:
                    c["sub_pure_tone"] += 1
                elif f["mod_diff"]:
                    c["sub_pure_modifier"] += 1
                else:
                    c["sub_pure_base"] += 1
            else:
                c["sub_mixed"] += 1

    return c, dict(tone=tone_cm, modifier=mod_cm, base=base_cm), \
        dict(tone=(tone_class_err, tone_class_n), modifier=(mod_class_err, mod_class_n))


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def med_range(vals):
    return st.median(vals), min(vals), max(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/error_analysis_run0.json")
    args = ap.parse_args()

    insts = list(iter_instances("test", scorable_only=True))
    per_seed = {}
    for s in SEEDS:
        pairs = load_preds(s)
        assert len(pairs) == len(insts) == 10068, f"seed {s}: {len(pairs)} rows != 10068"
        per_seed[s] = decompose_cer(pairs)

    print("=" * 84)
    print("ERROR_ANALYSIS Run 0 — real-only baseline, rec-only, VinText test-500 (real held-out)")
    print("n=10,068 instances / 37,254 NFC chars · NFC (axes NFD) · k=3 seeds · public labels")
    print("=" * 84)

    # ---------------- §3.2 CER decomposition ----------------
    print("\n### §3.2  CER DECOMPOSITION — the kill-test\n")
    print("Composition of ALL character edits (subs + deletions + insertions):\n")
    keys = [("sub", "substitutions"), ("del", "deletions"), ("ins", "insertions")]
    print(f"{'edit type':22s} {'median share':>13s} {'range':>18s}")
    tot = [per_seed[s][0]["edits_total"] for s in SEEDS]
    for k, lab in keys:
        vals = [pct(per_seed[s][0][k], per_seed[s][0]["edits_total"]) for s in SEEDS]
        m, lo, hi = med_range(vals)
        print(f"{lab:22s} {m:12.2f}% {f'[{lo:.2f}, {hi:.2f}]':>18s}")
    print(f"{'TOTAL EDITS':22s} {st.median(tot):12.0f}  {f'[{min(tot)}, {max(tot)}]':>18s}")

    print("\nOf the SUBSTITUTIONS, which axes differ (categories OVERLAP):\n")
    print(f"{'involves':22s} {'median share of subs':>20s} {'range':>18s}")
    for k, lab in [("sub_involves_tone", "tone"), ("sub_involves_modifier", "modifier"),
                   ("sub_involves_base", "base (case-insens)"), ("sub_involves_case_only", "case only")]:
        vals = [pct(per_seed[s][0][k], per_seed[s][0]["sub"]) for s in SEEDS]
        m, lo, hi = med_range(vals)
        print(f"{lab:22s} {m:19.2f}% {f'[{lo:.2f}, {hi:.2f}]':>18s}")

    print("\nPURE categories (exactly ONE axis differs) — these PARTITION the substitutions:\n")
    print(f"{'pure class':22s} {'median share of subs':>20s} {'share of ALL edits':>20s}")
    partition = [("sub_pure_tone", "PURE TONE"), ("sub_pure_modifier", "pure modifier"),
                 ("sub_pure_base", "pure base"), ("sub_pure_case", "pure case"),
                 ("sub_mixed", "mixed (>1 axis)")]
    for k, lab in partition:
        v_sub = [pct(per_seed[s][0][k], per_seed[s][0]["sub"]) for s in SEEDS]
        v_all = [pct(per_seed[s][0][k], per_seed[s][0]["edits_total"]) for s in SEEDS]
        print(f"{lab:22s} {st.median(v_sub):19.2f}% {st.median(v_all):19.2f}%")
    chk = [sum(per_seed[s][0][k] for k, _ in partition) for s in SEEDS]
    print(f"  (partition check: {chk} vs subs {[per_seed[s][0]['sub'] for s in SEEDS]})")

    # ---------------- §3.3 confusion matrices ----------------
    print("\n### §3.3  PER-AXIS CONFUSION MATRICES (seed 0; deliverables, not diagnostics-only)\n")
    cms = per_seed[0][1]
    print("TONE confusions (GT -> pred), top 12:")
    for (a, b), n in cms["tone"].most_common(12):
        print(f"   {a:>6s} -> {b:<7s} {n:5d}")
    print("\nMODIFIER confusions (GT -> pred), top 12:")
    for (a, b), n in cms["modifier"].most_common(12):
        print(f"   {a:>11s} -> {b:<12s} {n:5d}")
    print("\nBASE confusions (case-insens, GT -> pred), top 12:")
    for (a, b), n in cms["base"].most_common(12):
        print(f"   {a!r:>5} -> {b!r:<6} {n:5d}")

    # ---------------- §3.4 per-class ranking ----------------
    print("\n### §3.4  PER-CLASS ERROR RANKING (seed 0) — what the engine over-samples\n")
    for axis in ("tone", "modifier"):
        err, n = per_seed[0][2][axis]
        print(f"{axis.upper():9s} {'class':12s} {'errors':>8s} {'positions':>10s} {'error rate':>11s}")
        rows = sorted(n.items(), key=lambda kv: -pct(err[kv[0]], kv[1]))
        for cls, cnt in rows:
            print(f"{'':9s} {cls:12s} {err[cls]:8d} {cnt:10d} {pct(err[cls], cnt):10.2f}%")
        print()

    out = {f"seed{s}": dict(per_seed[s][0]) for s in SEEDS}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
