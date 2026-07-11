"""INS/DEL/SUB decomposition across arms A / B / C (BUILD_PLAN step 1; free, no training).

WHY THIS IS A REAL CHECK, NOT A FORMALITY. The three diacritic axes are scored on MATCHED
positions: a substitution or a deletion charges the axes, but an INSERTION has no reference
position, so it charges CER/WER ONLY. Arm B (strata augmentation) showed the odd pattern
"all three axes IMPROVE while CER/WER get WORSE". If that pattern is real, it must be driven
by INSERTIONS (extra hallucinated characters). If it turns out DELETIONS drive it instead,
the "per-character robustness bought with length errors" story is WRONG and must be restated
before it becomes a write-up claim.

Reuses scripts/scorer.align (the single alignment implementation) -- a second aligner would be
a second chance to get it wrong.
"""
import glob
import json
import statistics as st
import sys
from collections import Counter

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.scorer import align, clean, nfc  # noqa: E402

T = 4.302652729911275  # Student t, 2 dof, 95%
ARMS = [
    ("A", "runs/baseline_seed[0-9]/predictions.tsv"),
    ("B", "runs/armB_seed[0-9]/predictions.tsv"),
    ("C", "runs/armC_seed[0-9]/predictions.tsv"),
]


def decomp(path):
    c = Counter()
    n_ref = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            gt, _, pr = line.partition("\t")
            r, h = nfc(clean(gt)), nfc(clean(pr))
            n_ref += len(r)
            ops, _dist = align(r, h)          # align returns (ops, distance)
            for op, _, _ in ops:
                c[op] += 1
    return c, n_ref


def ci(vals):
    m = st.mean(vals)
    if len(vals) < 2:
        return m, float("nan")
    return m, T * st.stdev(vals) / (len(vals) ** 0.5)


def main():
    print("INS / DEL / SUB decomposition — rec-only, VinText test-500, NFC, k=3 seeds")
    print("Axes charge SUB and DEL (matched/reference positions); INSERTIONS charge CER/WER ONLY.\n")
    print(f"{'arm':4s} {'sub/100ch':>12s} {'del/100ch':>12s} {'ins/100ch':>12s} {'CER%':>10s}")
    out = {}
    for name, pat in ARMS:
        files = sorted(glob.glob(pat))
        if not files:
            print(f"{name}: no predictions found ({pat})")
            continue
        per = {k: [] for k in ("sub", "del", "ins", "cer")}
        for f in files:
            c, n_ref = decomp(f)
            for k in ("sub", "del", "ins"):
                per[k].append(100.0 * c[k] / n_ref)
            per["cer"].append(100.0 * (c["sub"] + c["del"] + c["ins"]) / n_ref)
        m = {k: ci(v) for k, v in per.items()}
        out[name] = {k: dict(mean=m[k][0], ci95=m[k][1], seeds=per[k]) for k in per}
        print(f"{name:4s} {m['sub'][0]:8.3f}±{m['sub'][1]:.3f} {m['del'][0]:8.3f}±{m['del'][1]:.3f} "
              f"{m['ins'][0]:8.3f}±{m['ins'][1]:.3f} {m['cer'][0]:9.3f}")

    if "A" in out and "B" in out:
        print("\nB − A  (does the 'axes up + CER up' pattern come from INSERTIONS?)")
        for k in ("sub", "del", "ins", "cer"):
            d = out["B"][k]["mean"] - out["A"][k]["mean"]
            print(f"  {k:4s} {d:+8.3f} per 100 chars")
        d_ins = out["B"]["ins"]["mean"] - out["A"]["ins"]["mean"]
        d_del = out["B"]["del"]["mean"] - out["A"]["del"]["mean"]
        d_sub = out["B"]["sub"]["mean"] - out["A"]["sub"]["mean"]
        d_cer = out["B"]["cer"]["mean"] - out["A"]["cer"]["mean"]
        print()
        if d_cer > 0:
            share_ins = 100.0 * d_ins / d_cer if d_cer else float("nan")
            share_del = 100.0 * d_del / d_cer if d_cer else float("nan")
            share_sub = 100.0 * d_sub / d_cer if d_cer else float("nan")
            print(f"  CER regression B−A = {d_cer:+.3f}/100ch  is  "
                  f"{share_ins:.0f}% insertions, {share_del:.0f}% deletions, {share_sub:.0f}% substitutions")
        verdict = ("INSERTIONS drive it -> the 'per-character robustness bought with hallucinated "
                   "characters' story HOLDS (axes untouched by ins)."
                   if d_ins > max(d_del, d_sub) else
                   "NOT insertion-driven -> the tradeoff story must be RESTATED (see numbers above).")
        print(f"  VERDICT: {verdict}")

    if "B" in out and "C" in out:
        print("\nC − B  (synthetic's effect on the error mix, at matched augmentation)")
        for k in ("sub", "del", "ins", "cer"):
            print(f"  {k:4s} {out['C'][k]['mean'] - out['B'][k]['mean']:+8.3f} per 100 chars")

    json.dump(out, open("runs/insdel_decomp.json", "w", encoding="utf-8"), indent=2)
    print("\nwrote runs/insdel_decomp.json")


if __name__ == "__main__":
    main()
