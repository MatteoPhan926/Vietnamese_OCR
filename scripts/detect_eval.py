"""Stage 1 / ERROR_ANALYSIS §5 — det-only P/R/F1 and the e2e pipeline.

EVAL_PROTOCOL §1: det-only = IoU-based P/R/F1 at a STATED IoU threshold
  [LOCKED: report at IoU 0.5; also curve F1 over IoU 0.5 -> 0.9].

EVAL_PROTOCOL §13 E2 [LOCKED]: '###' regions are DON'T CARE for det/e2e. A detection
overlapping a '###' region is neither TP nor FP -- it is removed from the match set before
P/R/F1. Scoring it as an FP would understate precision and, through it, the e2e number.

GT boxes are 4-point QUADS. doctr can emit rotated polygons; we compare polygon-to-polygon
with shapely, never axis-aligned-box-to-quad (which would under-report IoU on tilted text --
and §6 measured tilt as the single most damaging stratum, so that bias would be large).
"""
import argparse
import collections
import json
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from shapely.geometry import Polygon  # noqa: E402

from scripts.vintext import SPLITS, iter_instances  # noqa: E402


def to_poly(pts):
    p = Polygon(np.asarray(pts, dtype=float).reshape(-1, 2))
    return p if p.is_valid else p.buffer(0)


def iou(a, b):
    if not a.is_valid or not b.is_valid:
        return 0.0
    inter = a.intersection(b).area
    if inter <= 0:
        return 0.0
    return inter / (a.area + b.area - inter)


def load_gt(split):
    """img_id -> (care_polys, dontcare_polys)"""
    care = collections.defaultdict(list)
    dont = collections.defaultdict(list)
    for inst in iter_instances(split, scorable_only=False):
        p = to_poly(inst.poly)
        if p.area <= 0:
            continue
        (care if inst.scorable else dont)[inst.img_id].append(p)
    return care, dont


def match(gt_polys, dc_polys, pred_polys, thr):
    """Greedy IoU matching. Returns (tp, fp, fn). '###' regions are DON'T CARE [E2]."""
    matched_gt = set()
    tp = 0
    unmatched_preds = []
    for pi, pp in enumerate(pred_polys):
        best, bi = 0.0, -1
        for gi, gp in enumerate(gt_polys):
            if gi in matched_gt:
                continue
            v = iou(pp, gp)
            if v > best:
                best, bi = v, gi
        if best >= thr:
            matched_gt.add(bi)
            tp += 1
        else:
            unmatched_preds.append(pi)

    # a prediction landing on a '###' region is neither TP nor FP -- drop it [E2]
    fp = 0
    for pi in unmatched_preds:
        pp = pred_polys[pi]
        if any(iou(pp, dp) >= thr or (pp.area > 0 and pp.intersection(dp).area / pp.area >= 0.5)
               for dp in dc_polys):
            continue  # don't care
        fp += 1

    fn = len(gt_polys) - len(matched_gt)
    return tp, fp, fn


def build_predictor(size):
    from doctr.models import detection
    from doctr.models.detection.predictor import DetectionPredictor
    from doctr.models.preprocessor import PreProcessor
    m = detection.db_resnet50(pretrained=True, assume_straight_pages=False).eval().cuda()
    pre = PreProcessor(output_size=(size, size), batch_size=1,
                       mean=(0.798, 0.785, 0.772), std=(0.264, 0.2749, 0.287))
    return DetectionPredictor(pre, m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="runs/det_eval.json")
    args = ap.parse_args()

    care, dont = load_gt(args.split)
    folder, idxs = SPLITS[args.split]
    ids = list(idxs)[: args.limit] if args.limit else list(idxs)

    pred = build_predictor(args.size)
    preds = {}
    for n, img_id in enumerate(ids):
        img = cv2.imread(f"data/vietnamese/{folder}/im{img_id:04d}.jpg")
        H, W = img.shape[:2]
        out = pred([cv2.cvtColor(img, cv2.COLOR_BGR2RGB)])[0]["words"]
        polys = []
        for row in out:
            geo = np.asarray(row[:-1] if row.ndim == 1 else row[:4], dtype=float)
            if geo.size == 4:  # xmin,ymin,xmax,ymax (straight)
                x0, y0, x1, y1 = geo
                q = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            else:
                q = geo.reshape(-1, 2)
            q = np.asarray(q, dtype=float) * [W, H]
            p = to_poly(q)
            if p.area > 0:
                polys.append(p)
        preds[img_id] = polys
        if (n + 1) % 100 == 0:
            print(f"  detected {n+1}/{len(ids)} images", flush=True)

    print(f"\ndet-only, DBNet db_resnet50 (NOT fine-tuned on VinText), split={args.split}, "
          f"input {args.size}x{args.size}")
    print(f"'###' regions treated as DON'T CARE (EVAL_PROTOCOL §13 E2)\n")
    print(f"{'IoU':>6s} {'P':>8s} {'R':>8s} {'F1':>8s} {'TP':>7s} {'FP':>7s} {'FN':>7s}")
    res = {}
    for thr in (0.5, 0.6, 0.7, 0.8, 0.9):
        TP = FP = FN = 0
        for img_id in ids:
            tp, fp, fn = match(care[img_id], dont[img_id], preds[img_id], thr)
            TP += tp
            FP += fp
            FN += fn
        P = TP / (TP + FP) if TP + FP else 0.0
        R = TP / (TP + FN) if TP + FN else 0.0
        F = 2 * P * R / (P + R) if P + R else 0.0
        print(f"{thr:6.1f} {P*100:7.2f}% {R*100:7.2f}% {F*100:7.2f}% {TP:7d} {FP:7d} {FN:7d}")
        res[str(thr)] = dict(precision=P, recall=R, f1=F, tp=TP, fp=FP, fn=FN)

    res["_meta"] = dict(split=args.split, images=len(ids), size=args.size,
                        detector="doctr db_resnet50 pretrained (NOT fine-tuned on VinText)",
                        dontcare="### regions excluded from TP/FP (E2)",
                        gt_care=sum(len(care[i]) for i in ids),
                        gt_dontcare=sum(len(dont[i]) for i in ids))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
