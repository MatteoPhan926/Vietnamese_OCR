"""Stage 1 / ERROR_ANALYSIS §6 — pre-registered stratifications, each naming a generator knob.

Every stratum below is reported; none is dropped for being unflattering (§2 [LOCKED]).
Metrics per bin: CER (NFC) + the three axes (NFD), median over k=3 seeds.

Stratifications implemented here:
  crop height / resolution   -> downsample+blur degradation (DATA_ENGINE §6)
  contrast (Michelson)       -> photometric degradation
  text length               -> generation length distribution (DATA_ENGINE §4)
  orientation (quad tilt)   -> geometric degradation

'Stylized vs plain' (§6, 5th stratum) is NOT computed: VinText ships no style flag and no
defensible proxy exists without one. Reported as BLOCKED, not silently dropped. See RESULTS.
"""
import json
import statistics as st
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.crops import crop_quad, order_quad  # noqa: E402
from scripts.error_analysis import load_preds  # noqa: E402
from scripts.scorer import Score, score_pair  # noqa: E402
from scripts.vintext import iter_instances  # noqa: E402

SEEDS = (0, 1, 2)


def michelson(g):
    p5, p95 = np.percentile(g, 5), np.percentile(g, 95)
    return float((p95 - p5) / (p95 + p5 + 1e-6))


def features():
    feats = []
    cache, img = None, None
    for inst in iter_instances("test", scorable_only=True):
        if inst.img_path != cache:
            img = cv2.imread(inst.img_path)
            cache = inst.img_path
        c = crop_quad(img, inst.poly)
        p = order_quad(np.array(inst.poly, dtype=np.float32).reshape(4, 2))
        # tilt of the top edge, absolute degrees off horizontal
        dx, dy = p[1] - p[0]
        tilt = abs(np.degrees(np.arctan2(dy, dx)))
        tilt = min(tilt, 180 - tilt)
        feats.append(dict(
            height=0 if c is None else c.shape[0],
            contrast=0.0 if c is None else michelson(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)),
            length=len(inst.text),
            tilt=float(tilt),
        ))
    return feats


def binned(feats, preds_by_seed, key, edges, labels):
    """Return per-bin {n, cer, base, mod, tone} medians over seeds."""
    out = []
    for i, lab in enumerate(labels):
        lo, hi = edges[i], edges[i + 1]
        idx = [j for j, f in enumerate(feats) if lo <= f[key] < hi]
        if not idx:
            continue
        rows = {}
        for s in SEEDS:
            sc = Score()
            for j in idx:
                gt, pr = preds_by_seed[s][j]
                score_pair(sc, gt, pr)
            rows[s] = sc
        out.append(dict(
            label=lab, n=len(idx),
            chars=rows[SEEDS[0]].char_ref,
            cer=st.median([rows[s].cer * 100 for s in SEEDS]),
            base=st.median([rows[s].base_acc_ci * 100 for s in SEEDS]),
            mod=st.median([rows[s].mod_acc * 100 for s in SEEDS]),
            tone=st.median([rows[s].tone_acc * 100 for s in SEEDS]),
        ))
    return out


def show(title, rows, knob):
    print(f"\n### {title}")
    print(f"    knob -> {knob}")
    print(f"{'bin':>14s} {'n':>6s} {'chars':>7s} {'CER':>8s} {'base(ci)':>9s} {'modifier':>9s} {'tone':>8s}")
    for r in rows:
        print(f"{r['label']:>14s} {r['n']:6d} {r['chars']:7d} {r['cer']:7.2f}% "
              f"{r['base']:8.2f}% {r['mod']:8.2f}% {r['tone']:7.2f}%")


def main():
    feats = features()
    preds = {s: load_preds(s) for s in SEEDS}
    assert all(len(preds[s]) == len(feats) == 10068 for s in SEEDS)

    print("=" * 88)
    print("ERROR_ANALYSIS §6 — stratifications (real-only baseline, rec-only, test-500, k=3 median)")
    print("axes: base is CASE-INSENSITIVE (brain adjudication 2026-07-10)")
    print("=" * 88)

    res = {}
    res["height"] = binned(feats, preds, "height",
                           [0, 12, 16, 20, 24, 32, 48, 10 ** 9],
                           ["<12px", "12-15", "16-19", "20-23", "24-31", "32-47", ">=48"])
    show("Crop height / resolution", res["height"], "downsample->upsample + blur (DATA_ENGINE §6)")

    res["contrast"] = binned(feats, preds, "contrast",
                             [0, .2, .3, .4, .5, .65, 1.01],
                             ["<0.20", "0.20-0.29", "0.30-0.39", "0.40-0.49", "0.50-0.64", ">=0.65"])
    show("Contrast (Michelson)", res["contrast"], "photometric degradation (DATA_ENGINE §6)")

    res["length"] = binned(feats, preds, "length",
                           [0, 2, 4, 6, 9, 13, 10 ** 9],
                           ["1 char", "2-3", "4-5", "6-8", "9-12", ">=13"])
    show("Text length (chars)", res["length"], "generation length distribution (DATA_ENGINE §4)")

    res["tilt"] = binned(feats, preds, "tilt",
                         [0, 2, 5, 10, 20, 91],
                         ["<2deg", "2-5", "5-10", "10-20", ">=20"])
    show("Orientation (tilt of top edge)", res["tilt"], "geometric degradation (DATA_ENGINE §6)")

    print("\n### Stylized vs plain appearance  —  BLOCKED, not dropped")
    print("    VinText ships no style annotation and no defensible proxy exists without one.")
    print("    Reported as not-measured (ERROR_ANALYSIS §6 [LOCKED] requires all strata reported;")
    print("    a fabricated proxy would be worse than a stated gap).")

    with open("runs/stratifications_run0.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("\nwrote runs/stratifications_run0.json")


if __name__ == "__main__":
    main()
