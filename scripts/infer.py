"""Batched rec-only inference over GT-box crops (EVAL_PROTOCOL §1 rec-only scope).

vietocr's own Predictor.predict_batch buckets every same-width crop into ONE batch, which
OOMs an 8 GB card on VinText-sized splits. We bucket by width *and* chunk each bucket.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import cv2
import numpy as np
import torch
import yaml
from PIL import Image

sys.path.insert(0, ".")
from scripts.crops import crop_quad  # noqa: E402


def load_config(path="configs/vgg_transformer_pinned.yml", device="cuda:0"):
    cfg = yaml.safe_load(open(path, encoding="utf-8"))
    cfg["device"] = device
    return cfg


class Recognizer:
    def __init__(self, cfg, weights=None):
        from vietocr.tool.translate import build_model

        self.cfg = cfg
        self.device = cfg["device"]
        self.model, self.vocab = build_model(cfg)
        w = weights or cfg["weights"]
        state = torch.load(w, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.eval()

    def _prep(self, pil_img):
        from vietocr.tool.translate import process_input

        d = self.cfg["dataset"]
        return process_input(pil_img, d["image_height"], d["image_min_width"], d["image_max_width"])

    @torch.no_grad()
    def predict(self, pil_imgs, max_batch=48):
        """Return list[str] aligned with pil_imgs."""
        from vietocr.tool.translate import translate

        tensors = [self._prep(im) for im in pil_imgs]
        buckets = defaultdict(list)
        for i, t in enumerate(tensors):
            buckets[t.shape[-1]].append(i)

        out = [None] * len(tensors)
        for width, idxs in buckets.items():
            for s in range(0, len(idxs), max_batch):  # chunk: 8 GB VRAM
                chunk = idxs[s:s + max_batch]
                batch = torch.cat([tensors[i] for i in chunk], 0).to(self.device)
                sent, _ = translate(batch, self.model)
                for i, row in zip(chunk, self.vocab.batch_decode(sent.tolist())):
                    out[i] = row
        return out


def crops_for(instances):
    """Perspective-rectified PIL crops, one per instance. None where the quad is degenerate.

    A degenerate quad is NEVER dropped. VinText's test-500 contains 19 scorable instances
    whose quads are 2-3 px on a side ('000' in 6x3 px, '-' in 4x2, ':' in 3x10) -- real,
    labelled, microscopic text. Dropping them would make `min_side` a knob on the TEST SET:
    raising it 4 -> 8 would delete 250 of the hardest instances and improve CER for free.
    The denominator must not move with the crop code, so an unrectifiable crop becomes an
    EMPTY PREDICTION (all deletions), not an exclusion.  [EVAL_PROTOCOL §13 E8]
    """
    out = []
    cache_path, cache_img = None, None
    for inst in instances:
        if inst.img_path != cache_path:
            cache_img = cv2.imread(inst.img_path)
            cache_path = inst.img_path
        c = crop_quad(cache_img, inst.poly)
        out.append((inst, None if c is None
                    else Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))))
    return out


def predict_instances(rec: "Recognizer", instances, max_batch=48):
    """Return (instances, predictions, n_degenerate) with predictions aligned 1:1.

    Degenerate crops get '' -- scored as full deletions, never excluded. [E8]
    """
    pairs = crops_for(instances)
    idx = [i for i, (_, im) in enumerate(pairs) if im is not None]
    preds = [""] * len(pairs)
    if idx:
        got = rec.predict([pairs[i][1] for i in idx], max_batch=max_batch)
        for i, p in zip(idx, got):
            preds[i] = p
    return [p[0] for p in pairs], preds, len(pairs) - len(idx)
