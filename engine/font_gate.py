"""The 3-check font coverage gate (DATA_ENGINE §5 / G6).

A font that mangles or drops a letter-forming mark trains the recognizer on WRONG glyphs;
the damage surfaces as Modifier/Tone-axis error on real data, indistinguishable from a model
failure. So only PASS fonts generate. Checks (this file does 1 & 2 programmatically;
check 3 = font_sheet.py + a visual audit read):

  1. GLYPH EXISTS  -- every required Vietnamese codepoint maps to a real glyph via the font
     cmap (not .notdef / tofu). fontTools getBestCmap.
  2. DISTINCTNESS / ROUND-TRIP -- for every tone-bearing stacked vowel, render the stacked
     char, its base-without-tone, and its base-without-modifier; the three bitmaps must be
     pixel-distinct. A font that renders `ệ` identically to `ê` or `ẹ` is SILENTLY DROPPING a
     mark and passes check 1 while still being poison.

Output: per-font verdict (PASS/FAIL + failing codepoints) -> data/synth/fonts/verdicts.json.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from engine.vn_charset import all_vn_letters, stacked_chars  # noqa: E402

FONT_DIR = os.path.join("data", "synth", "fonts")
CANVAS = 160
FSIZE = 96
# A SILENTLY-DROPPED mark = the font substitutes an IDENTICAL glyph, so the two bitmaps are
# ~byte-identical (0 differing pixels; a few from anti-alias jitter). A correctly-rendered
# mark -- even the tiny nặng dot -- moves dozens of pixels at this render size (measured:
# Montserrat ệ-vs-ê = 26 px @ size 96). So the "same glyph" bar is LOW (<=6 px); an earlier
# 30 px bar false-failed good fonts (Montserrat/Open Sans/Nunito) because a nặng dot at
# size 56 is only ~9 px -- smaller than the tolerance. Render big, judge tight.
INTENSITY = 30    # a pixel "changed" if |Δ| > 30
SAME_PIXELS = 6   # <= this many changed px == the mark was dropped (identical glyph)


def cmap_codepoints(path):
    tt = TTFont(path, fontNumber=0, lazy=True)
    cps = set()
    for table in tt["cmap"].tables:
        if table.isUnicode():
            cps.update(table.cmap.keys())
    tt.close()
    return cps


def _render(font, ch):
    img = Image.new("L", (CANVAS, CANVAS), 255)
    d = ImageDraw.Draw(img)
    d.text((CANVAS / 2, CANVAS / 2), ch, font=font, fill=0, anchor="mm")
    return np.asarray(img, dtype=np.int16)


def _n_diff(a, b):
    return int((np.abs(a - b) > INTENSITY).sum())


def check_glyphs(path):
    """Check 1: which required Vietnamese codepoints are absent from the cmap."""
    cps = cmap_codepoints(path)
    missing = [c for c in all_vn_letters() if ord(c) not in cps]
    return missing


def check_distinct(path):
    """Check 2: stacked forms whose mark is silently dropped (bitmap-identical to base)."""
    font = ImageFont.truetype(path, FSIZE)
    dropped = []
    for d in stacked_chars():
        st = _render(font, d["stacked"])
        nt = _render(font, d["no_tone"])
        nm = _render(font, d["no_mod"])
        tone_dropped = _n_diff(st, nt) <= SAME_PIXELS   # looks like base-without-tone
        mod_dropped = _n_diff(st, nm) <= SAME_PIXELS     # looks like base-without-modifier
        blank = int((st < 215).sum()) < 20               # rendered almost nothing (tofu/empty)
        if tone_dropped or mod_dropped or blank:
            dropped.append(dict(
                char=d["stacked"],
                tone_dropped=tone_dropped, mod_dropped=mod_dropped, blank=blank,
                diff_no_tone=_n_diff(st, nt), diff_no_mod=_n_diff(st, nm),
            ))
    return dropped


def main():
    downloaded = json.load(open(os.path.join(FONT_DIR, "downloaded.json"), encoding="utf-8"))
    verdicts = []
    n_pass = 0
    for ent in downloaded:
        path = ent["path"]
        fam = ent["family"]
        try:
            missing = check_glyphs(path)
            dropped = check_distinct(path)
        except Exception as e:  # noqa: BLE001
            verdicts.append(dict(family=fam, path=path, verdict="FAIL",
                                 reason=f"error: {e}"))
            print(f"FAIL {fam:16s} (error: {e})")
            continue
        ok = not missing and not dropped
        v = dict(
            family=fam, file=ent["file"], path=path, license=ent["license"],
            verdict="PASS" if ok else "FAIL",
            n_missing_glyphs=len(missing),
            missing_glyphs="".join(missing),
            n_dropped_stacked=len(dropped),
            dropped_stacked=[d["char"] for d in dropped],
            dropped_detail=dropped,
        )
        verdicts.append(v)
        n_pass += ok
        tag = "PASS" if ok else "FAIL"
        extra = "" if ok else f"  missing={len(missing)} dropped={len(dropped)} {''.join(d['char'] for d in dropped[:8])}"
        print(f"{tag} {fam:16s}{extra}")

    out = os.path.join(FONT_DIR, "verdicts.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(verdicts, f, ensure_ascii=False, indent=2)
    print(f"\n{n_pass}/{len(verdicts)} PASS checks 1+2 -> {out}")
    print("(check 3 visual audit next: engine/font_sheet.py)")


if __name__ == "__main__":
    main()
