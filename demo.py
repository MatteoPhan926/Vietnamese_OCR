"""demo.py — read any image with the shipped checkpoint and print the three-axis breakdown.

No dataset needed. VinText is not redistributable, so this is the part of the pipeline you can
actually run: a trained recognizer + the scorer, on an image you supply.

    # just read it (no ground truth -> prediction only)
    python demo.py path/to/crop.jpg

    # read it AND score it (ground truth supplied -> CER/WER + the three axes)
    python demo.py path/to/crop.jpg --gt "Việt Nam"

    # a whole folder of crops, with ground truth in a TSV (filename <TAB> ground_truth)
    python demo.py path/to/crops/ --gt-tsv labels.tsv

The input is a WORD CROP, not a full scene photo. The headline model is a RECOGNIZER: it is
scored rec-only (given ground-truth boxes) throughout this project, and it will happily emit
nonsense if you hand it a whole street scene. Detection is deferred (see the README's "what
this does not claim"). Pass --crop x1,y1,x2,y2 to cut a box out of a larger image first.

Checkpoint: the full-real-data baseline by default — the most accurate model here (rec-only CER
9.38% on VinText test-500). The study's headline arm is a deliberately label-starved model; run
it with --checkpoint runs/budget_r10_strict_seed0/best.pth if you want to see what 2,574 real
crops + 10k synthetic buys you.
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scripts.infer import Recognizer, load_config          # noqa: E402
from vi_three_axis_scorer import score                     # noqa: E402

DEFAULT_CKPT = "runs/baseline_seed0/best.pth"
IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="an image file, or a directory of image files")
    ap.add_argument("--gt", help="ground truth for a single image (enables scoring)")
    ap.add_argument("--gt-tsv", help="TSV of 'filename <TAB> ground_truth' for a directory")
    ap.add_argument("--checkpoint", default=DEFAULT_CKPT)
    ap.add_argument("--crop", help="x1,y1,x2,y2 — cut this box out before recognizing")
    ap.add_argument("--device", default="cuda:0", help="cuda:0 | cpu")
    ap.add_argument("--confusion", action="store_true", help="also print per-axis confusions")
    args = ap.parse_args()

    if not os.path.exists(args.checkpoint):
        sys.exit(f"checkpoint not found: {args.checkpoint}\n"
                 f"(train one with scripts/train_budget.py, or point --checkpoint at your own)")

    # ---- gather (path, ground_truth or None)
    items = []
    if os.path.isdir(args.image):
        gts = {}
        if args.gt_tsv:
            with open(args.gt_tsv, encoding="utf-8") as f:
                for ln in f:
                    if ln.strip():
                        k, _, v = ln.rstrip("\n").partition("\t")
                        gts[os.path.basename(k)] = v
        for fn in sorted(os.listdir(args.image)):
            if fn.lower().endswith(IMG_EXT):
                items.append((os.path.join(args.image, fn), gts.get(fn)))
        if not items:
            sys.exit(f"no images in {args.image}")
    else:
        items = [(args.image, args.gt)]

    # ---- recognize
    rec = Recognizer(load_config(device=args.device), weights=args.checkpoint)
    imgs = []
    for path, _ in items:
        im = Image.open(path).convert("RGB")
        if args.crop:
            x1, y1, x2, y2 = (int(v) for v in args.crop.split(","))
            im = im.crop((x1, y1, x2, y2))
        imgs.append(im)
    preds = rec.predict(imgs)

    # ---- print
    print(f"\ncheckpoint : {args.checkpoint}")
    print(f"scope      : rec-only (the model reads a word crop; it does not detect)\n")
    w = max(len(os.path.basename(p)) for p, _ in items)
    for (path, gt), pred in zip(items, preds):
        mark = "" if gt is None else ("  ✓" if gt.strip() == pred.strip() else "  ✗")
        print(f"  {os.path.basename(path):<{w}s}  ->  {pred!r}{mark}")
        if gt is not None and gt.strip() != pred.strip():
            print(f"  {'':<{w}s}      GT {gt!r}")

    scored = [(gt, pred) for (_, gt), pred in zip(items, preds) if gt is not None]
    if not scored:
        print("\n(no ground truth given -> nothing to score. Pass --gt or --gt-tsv for the "
              "three-axis breakdown.)")
        return

    s = score(scored)
    print("\n" + "-" * 68)
    print(s.report(scope="rec-only", testset=args.image))
    print("-" * 68)
    if args.confusion:
        print()
        for ax in ("tone", "modifier", "base"):
            print(s.confusion(ax))
    print("\nRead the axes, not just the CER: a tone axis far below the base axis means the "
          "\nmodel is reading the letters and losing the marks — and CER alone hides that.")


if __name__ == "__main__":
    main()
