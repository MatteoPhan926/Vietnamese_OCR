"""Materialise rec-only training crops for vietocr's Trainer.

CONTAMINATION FIREWALL (EVAL_PROTOCOL §10): only `train` and `val` crops are written.
The test-500 is NEVER written to disk as a training-shaped artifact and is NEVER seen by
the trainer. Test evaluation runs in-memory from the GT annotation via scripts/infer.py,
so the frozen 10,068 / 37,254 denominator (E8) cannot drift.

Degenerate quads ARE skipped here -- for TRAINING they are unusable inputs (a 4x2 px crop
teaches nothing). This is safe because it only removes training data; it does not touch a
denominator. At TEST time the same instances are scored as empty predictions, never dropped.
"""
import os
import sys

import cv2
import yaml

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.crops import crop_quad  # noqa: E402
from scripts.vintext import iter_instances  # noqa: E402

OUT = os.path.join("data", "crops")
VOCAB = set(yaml.safe_load(open("configs/vgg_transformer_pinned.yml", encoding="utf-8"))["vocab"])


def build(split):
    d = os.path.join(OUT, split)
    os.makedirs(d, exist_ok=True)
    lines = []
    n = degen = oov = 0
    cache_path, img = None, None
    for inst in iter_instances(split, scorable_only=True):
        # The locked 229-char vocab cannot ENCODE a char it does not contain, so such an
        # instance cannot be a training target at all. train has 2 ('°'); test has 0, so
        # no headline number is touched (EVAL_PROTOCOL §13 E7). Adding '°' to the locked
        # vocab to chase 0.008% of train chars would be a confound, not a fix.
        if any(c not in VOCAB for c in inst.text):
            oov += 1
            continue
        if inst.img_path != cache_path:
            img = cv2.imread(inst.img_path)
            cache_path = inst.img_path
        c = crop_quad(img, inst.poly)
        if c is None:
            degen += 1
            continue
        name = f"{split}/{inst.img_id:04d}_{n:06d}.jpg"
        cv2.imwrite(os.path.join(OUT, name), c, [cv2.IMWRITE_JPEG_QUALITY, 95])
        # vietocr annotation format: <path>\t<label>, label must not contain a tab
        assert "\t" not in inst.text and "\n" not in inst.text
        lines.append(f"{name}\t{inst.text}")
        n += 1

    ann = os.path.join(OUT, f"annotation_{split}.txt")
    with open(ann, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{split}: wrote {n} crops  ({degen} degenerate, {oov} out-of-vocab skipped) -> {ann}")
    return n


if __name__ == "__main__":
    total = {s: build(s) for s in ("train", "val")}
    print("\nTRAIN CROPS (the real-only baseline's data):", total["train"])
    print("VAL CROPS   (model selection only, never test):", total["val"])
    print("\ntest-500 deliberately NOT written to disk (EVAL_PROTOCOL §10).")
