"""Single source of truth for reading VinText annotations.

Every rule here is frozen in EVAL_PROTOCOL §13:
  E2 — '###' and empty transcripts are NOT rec-only scorable (no reference string).
  E4 — 756 lines put a comma INSIDE the transcript => rejoin parts[8:], never parts[8].
  E5 — folder 'test_image' is the 300-image VALIDATION split;
       the 500-image TEST split is 'unseen_test_images'.
  E6 — transcripts are stripped of LEADING/TRAILING whitespace (27 instances carry it);
       internal spaces are preserved. Strip the transcript, never the raw line: stripping
       the line removes trailing but not leading spaces, a silent asymmetry.

Import this rather than re-parsing; a second parser is a second chance to get it wrong.
"""
from __future__ import annotations

import os
import unicodedata as ud
from dataclasses import dataclass

ROOT = os.path.join("data", "vietnamese")

# protocol role -> (image folder, image-id range)   [E5]
SPLITS = {
    "train": ("train_images", range(1, 1201)),
    "val": ("test_image", range(1201, 1501)),
    "test": ("unseen_test_images", range(1501, 2001)),
}

DONT_CARE = "###"


@dataclass(frozen=True)
class Instance:
    img_id: int
    img_path: str
    poly: tuple  # 8 ints: x1,y1,x2,y2,x3,y3,x4,y4
    text: str  # transcript, edge-whitespace stripped  [E6]
    raw_text: str  # transcript exactly as shipped, for provenance
    scorable: bool  # False for '###' and empty  [E2]

    @property
    def nfc(self) -> str:
        return ud.normalize("NFC", self.text)


def _label_path(img_id: int) -> str:
    return os.path.join(ROOT, "labels", f"gt_{img_id}.txt")


def iter_instances(split: str, scorable_only: bool = True):
    """Yield Instance for a protocol split ('train' | 'val' | 'test')."""
    folder, idxs = SPLITS[split]
    for img_id in idxs:
        img_path = os.path.join(ROOT, folder, f"im{img_id:04d}.jpg")
        with open(_label_path(img_id), encoding="utf-8") as fh:
            for line in fh:
                # strip ONLY the newline; never .strip() the whole line, which would
                # remove a trailing transcript space but leave a leading one.  [E6]
                line = line.rstrip("\r\n")
                if not line.strip():
                    continue
                parts = line.split(",")
                poly = tuple(int(p) for p in parts[:8])
                raw_text = ",".join(parts[8:])  # [E4]
                text = raw_text.strip()  # [E6]
                scorable = bool(text) and text != DONT_CARE  # [E2]
                if scorable_only and not scorable:
                    continue
                yield Instance(img_id, img_path, poly, text, raw_text, scorable)
