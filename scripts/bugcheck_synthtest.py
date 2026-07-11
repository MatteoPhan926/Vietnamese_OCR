"""Bug-check (d) (DATA_ENGINE §8.2): did the synth-trained model even LEARN synthetic?

Score each Gate-A model on a HELD-OUT synthetic split (a seed disjoint from the 10k training
set). If synth-test CER is low, the model learned the synthetic distribution fine and the flat
REAL result means the data simply DOES NOT TRANSFER (the real finding). If synth-test CER is
also high, the pipeline is broken. Synthetic-test accuracy is a SANITY CHECK ONLY, never a
result (SCALING §6).
"""
import glob
import json
import sys

import torch
from PIL import Image

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

import scripts.compat  # noqa: E402,F401
from engine.corpus import Corpus  # noqa: E402
from engine.render import Generator, load_bg_index, load_fonts  # noqa: E402
from scripts.infer import Recognizer, load_config  # noqa: E402
from scripts.scorer import Score, format_score, score_pair  # noqa: E402
import cv2  # noqa: E402
import numpy as np  # noqa: E402

HELDOUT_SEED = 777    # disjoint from the 10k train set (seed 100)
N = 2000


def gen_heldout():
    g = Generator(Corpus(seed=HELDOUT_SEED), load_fonts(), load_bg_index(), seed=HELDOUT_SEED)
    crops, labels = [], []
    while len(crops) < N:
        r = g.generate()
        if r is None:
            continue
        crop, text, _ = r
        crops.append(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
        labels.append(text)
    return crops, labels


def main():
    crops, labels = gen_heldout()
    print(f"held-out synthetic: {len(crops)} crops (seed {HELDOUT_SEED}, disjoint from train seed 100)\n")
    cfg = load_config()
    cfg["dataset"] = dict(image_height=32, image_min_width=32, image_max_width=512)
    for wpath in sorted(glob.glob("runs/gateA_synth10k_seed[0-9]/best.pth")):
        rec = Recognizer(cfg, weights=wpath)
        preds = rec.predict(crops, max_batch=48)
        sc = Score()
        for gt, pr in zip(labels, preds):
            score_pair(sc, gt, pr)
        del rec
        torch.cuda.empty_cache()
        print(f"{wpath}:")
        print("  " + format_score(sc, scope="rec-only", testset=f"HELD-OUT SYNTHETIC (n={len(crops)})").replace("\n", "\n  "))
        print()


if __name__ == "__main__":
    main()
