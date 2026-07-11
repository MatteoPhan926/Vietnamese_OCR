"""Real background patches for compositing (DATA_ENGINE §6 — 'the biggest single transfer
element'). Text is composited onto real scene-background patches so the recognizer stops
relying on the document-white prior.

Patches are cropped from VinText TRAIN images ONLY, from regions that overlap NO annotated
box (scorable or ###) -- so no real glyph leaks into a 'background'. Test images are never
touched (they are the held-out set; using them as backgrounds would drag test imagery into
training). This is images, not labels, but the train-only rule is kept for cleanliness.
"""
from __future__ import annotations

import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
from scripts.vintext import iter_instances  # noqa: E402

OUT = os.path.join("data", "synth", "bg")
N_TARGET = 5000
TRIES_PER_IMG = 12


def _boxes_for_image():
    """img_path -> list of (x0,y0,x1,y1) axis-aligned bboxes of ALL annotated regions."""
    from collections import defaultdict
    boxes = defaultdict(list)
    for inst in iter_instances("train", scorable_only=False):
        xs = inst.poly[0::2]
        ys = inst.poly[1::2]
        boxes[inst.img_path].append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def _overlaps(rect, boxes):
    x0, y0, x1, y1 = rect
    for bx0, by0, bx1, by1 in boxes:
        if x0 < bx1 and bx0 < x1 and y0 < by1 and by0 < y1:
            return True
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(20260711)
    boxes = _boxes_for_image()
    paths = list(boxes.keys())
    rng.shuffle(paths)
    n = 0
    manifest = []
    for p in paths:
        if n >= N_TARGET:
            break
        img = cv2.imread(p)
        if img is None:
            continue
        H, W = img.shape[:2]
        bx = boxes[p]
        for _ in range(TRIES_PER_IMG):
            if n >= N_TARGET:
                break
            # random patch, size 48-320 px, aspect wide-ish (crops are wide)
            pw = rng.randint(64, min(320, W - 1))
            ph = rng.randint(32, min(200, H - 1))
            if pw >= W or ph >= H:
                continue
            x0 = rng.randint(0, W - pw)
            y0 = rng.randint(0, H - ph)
            rect = (x0, y0, x0 + pw, y0 + ph)
            if _overlaps(rect, bx):
                continue
            patch = img[y0:y0 + ph, x0:x0 + pw]
            # reject near-flat patches only if truly degenerate (all one value); we WANT
            # some flat patches (solid signs) and some textured ones.
            if patch.std() < 1.0:
                continue
            fn = f"bg_{n:05d}.jpg"
            cv2.imwrite(os.path.join(OUT, fn), patch, [cv2.IMWRITE_JPEG_QUALITY, 92])
            manifest.append(fn)
            n += 1
    with open(os.path.join(OUT, "index.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(manifest) + "\n")
    print(f"extracted {n} text-free background patches from VinText train -> {OUT}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
