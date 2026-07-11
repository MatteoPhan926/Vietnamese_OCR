"""Freeze the engine's font set (DATA_ENGINE §5): the per-font 3-check verdict + a diverse
selection of 15-20 PASS fonts ("quality over count").

Checks 1-2 ran in font_gate.py (27/30 PASS). Check 3 (visual audit of contact_sheet.png)
was performed by reading the sheet: ALL 27 render the stacked marks correctly-placed,
correctly-scaled, no overlap -> visual_audit = PASS for all 27.

From the 27 we SELECT 18 for visual diversity across type categories, honoring the locked
15-20 target. The unselected 9 remain PASS-on-record (usable later) but are not in v0's set,
so the generator's font distribution is auditable and reproducible.
"""
from __future__ import annotations

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
FONT_DIR = os.path.join("data", "synth", "fonts")

# 18 selected for category spread. Signage over-represents condensed + geometric + bold
# grotesque, so those categories get more slots than serif.
SELECTED = {
    "bevietnampro": "vietnamese-designed sans",
    "roboto": "neo-grotesque sans (ubiquitous)",
    "opensans": "humanist sans",
    "lato": "humanist sans",
    "notosans": "humanist sans (broad coverage)",
    "montserrat": "geometric sans (common signage)",
    "lexend": "geometric sans",
    "inter": "neo-grotesque sans (UI/signage)",
    "archivo": "grotesque display sans",
    "worksans": "grotesque sans",
    "oswald": "condensed sans (very common signage)",
    "barlow": "semi-condensed sans",
    "nunito": "rounded geometric sans",
    "quicksand": "rounded geometric sans",
    "notoserif": "serif",
    "lora": "serif (contemporary)",
    "merriweather": "serif (text)",
    "playfairdisplay": "high-contrast display serif (decorative signage)",
}


def main():
    verdicts = json.load(open(os.path.join(FONT_DIR, "verdicts.json"), encoding="utf-8"))
    by_fam = {v["family"]: v for v in verdicts}
    out = []
    for v in verdicts:
        if v["verdict"] == "PASS":
            v["visual_audit"] = "PASS"  # from reading contact_sheet.png
        else:
            v["visual_audit"] = "n/a (failed checks 1-2)"
    for fam, category in SELECTED.items():
        if fam not in by_fam or by_fam[fam]["verdict"] != "PASS":
            raise SystemExit(f"selected font {fam} is not a PASS -- fix SELECTED")
        e = by_fam[fam]
        out.append(dict(
            family=fam, file=e["file"], path=e["path"], license="OFL-1.1",
            category=category,
            check1_glyphs="PASS", check2_distinct="PASS", check3_visual="PASS",
        ))

    manifest = dict(
        source="Google Fonts (github.com/google/fonts), subset vietnamese, SIL OFL 1.1",
        n_candidates=len(verdicts),
        n_pass_checks_12=sum(v["verdict"] == "PASS" for v in verdicts),
        n_selected=len(out),
        failed=[dict(family=v["family"], reason=v.get("reason",
                     f"missing={v['n_missing_glyphs']} dropped={v['n_dropped_stacked']}"))
                for v in verdicts if v["verdict"] == "FAIL"],
        fonts=out,
    )
    with open(os.path.join(FONT_DIR, "fonts_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    # also rewrite verdicts.json with the visual_audit field recorded
    with open(os.path.join(FONT_DIR, "verdicts.json"), "w", encoding="utf-8") as f:
        json.dump(verdicts, f, ensure_ascii=False, indent=2)
    print(f"selected {len(out)}/{manifest['n_pass_checks_12']} PASS fonts -> fonts_manifest.json")
    for e in out:
        print(f"  {e['family']:16s} {e['category']}")
    print("FAILED (recorded):", ", ".join(v["family"] for v in verdicts if v["verdict"] == "FAIL"))


if __name__ == "__main__":
    main()
