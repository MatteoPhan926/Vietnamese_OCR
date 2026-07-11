"""Check 3 of the font gate (DATA_ENGINE §5): the VISUAL AUDIT contact sheet.

Checks 1-2 (font_gate.py) prove marks EXIST and are DISTINCT from their base; they cannot
catch a mark that renders present-but-wrong: misplaced, wrong-scale, or overlapping. That is
a human-eye judgment. This renders every PASS font's fixed stacked-diacritic sample string
into one contact sheet; the audit is done by reading the image and rejecting bad rows.
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

FONT_DIR = os.path.join("data", "synth", "fonts")
# every stacked family + tone variety + both cases + horn/breve/circumflex + đ
SAMPLE = "Việt Nghệ Thuật ĐƯỜNG PHỐ  ăằẳ ôỗộ ưữự ơớợ êếệ âấậ"
FSIZE = 30
ROW_H = 52
LABEL_W = 150


def main():
    verdicts = json.load(open(os.path.join(FONT_DIR, "verdicts.json"), encoding="utf-8"))
    passes = [v for v in verdicts if v["verdict"] == "PASS"]
    W = 1400
    H = ROW_H * len(passes) + 20
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    lbl = ImageFont.truetype(passes[0]["path"], 16)
    for i, v in enumerate(passes):
        y = 10 + i * ROW_H
        d.text((8, y + 14), v["family"], font=lbl, fill=(180, 30, 30))
        try:
            f = ImageFont.truetype(v["path"], FSIZE)
            d.text((LABEL_W, y + 6), SAMPLE, font=f, fill=(0, 0, 0))
        except Exception as e:  # noqa: BLE001
            d.text((LABEL_W, y + 6), f"[render error: {e}]", font=lbl, fill=(200, 0, 0))
        d.line([(0, y), (W, y)], fill=(230, 230, 230))
    out = os.path.join(FONT_DIR, "contact_sheet.png")
    sheet.save(out)
    print(f"wrote {out}  ({len(passes)} PASS fonts, sample='{SAMPLE}')")


if __name__ == "__main__":
    main()
