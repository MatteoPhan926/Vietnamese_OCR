"""Download Google Fonts (SIL OFL 1.1) candidates for the synthetic engine.

DATA_ENGINE §5 / EVAL_PROTOCOL §10: fonts are license-clean Google Fonts. This only
FETCHES candidates; coverage verification (the 3-check gate) is font_gate.py, and only
PASS fonts ever generate. A generous candidate list is fine -- the gate rejects the
un-Vietnamese and the mark-mangling ones, which is exactly its job.

We pick, per family, a single upright non-italic weight (prefer a Regular/[wght] file),
because the recognizer trains on crops where weight diversity is cheap via candidates,
not via loading every instance of one family.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join("data", "synth", "fonts")
os.makedirs(OUT, exist_ok=True)

# Curated for likely Vietnamese subset + visual diversity (sans/serif/condensed/rounded/
# slab/display + Vietnamese-designed). The gate, not this list, is the arbiter of coverage.
FAMILIES = [
    "bevietnampro", "lexend", "roboto", "opensans", "lato", "montserrat",
    "notosans", "notoserif", "lora", "merriweather", "playfairdisplay",
    "nunito", "mulish", "inter", "barlow", "bitter", "arimo", "tinos",
    "sarabun", "josefinsans", "oswald", "archivo", "manrope", "quicksand",
    "comfortaa", "ptsans", "worksans", "rubik", "karla", "cabin",
]

API = "https://api.github.com/repos/google/fonts/contents/ofl/{fam}"
RAW = "https://github.com/google/fonts/raw/main/ofl/{fam}/{name}"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ocr-engine/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def pick_ttf(files):
    """Choose one upright, non-italic TTF filename from a family dir listing."""
    ttfs = [f["name"] for f in files if f["name"].lower().endswith(".ttf")]
    if not ttfs:
        return None
    up = [t for t in ttfs if "italic" not in t.lower()]
    cand = up or ttfs
    # prefer a static Regular
    for t in cand:
        if t.lower().endswith("-regular.ttf"):
            return t
    # else a weight-axis variable font (no width/italic axis to keep it upright default)
    for t in cand:
        if "[wght].ttf" in t.lower():
            return t
    for t in cand:
        if t.startswith("[") is False and "[" in t:  # any variable file
            return t
    return sorted(cand)[0]


def main():
    manifest = []
    for fam in FAMILIES:
        try:
            listing = json.loads(_get(API.format(fam=fam)))
        except Exception as e:  # noqa: BLE001
            print(f"SKIP {fam}: listing failed ({e})")
            continue
        if not isinstance(listing, list):
            print(f"SKIP {fam}: {listing.get('message', 'no dir')}")
            continue
        name = pick_ttf(listing)
        if not name:
            print(f"SKIP {fam}: no ttf")
            continue
        dst = os.path.join(OUT, f"{fam}__{name}")
        if not os.path.exists(dst):
            try:
                data = _get(RAW.format(fam=fam, name=urllib.parse.quote(name)))
            except Exception as e:  # noqa: BLE001
                print(f"SKIP {fam}: download {name} failed ({e})")
                continue
            with open(dst, "wb") as f:
                f.write(data)
        manifest.append(dict(family=fam, file=name, path=dst, license="OFL-1.1"))
        print(f"OK  {fam:16s} {name}  ({os.path.getsize(dst)//1024} KB)")
        time.sleep(0.3)  # be polite to the API

    with open(os.path.join(OUT, "downloaded.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n{len(manifest)} fonts downloaded -> {OUT}")


if __name__ == "__main__":
    import urllib.parse  # noqa: E402
    main()
