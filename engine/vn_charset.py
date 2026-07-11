"""The Vietnamese charset the font gate verifies (DATA_ENGINE §5, G6).

Two sets:
  ALL_VN   -- every Vietnamese letter (both cases) the locked vocab uses; check-1 (glyph
              exists) runs over all of them.
  STACKED  -- the doubly-marked vowels (modifier + tone on one base) + the toneless modified
              bases + đ; check-2 (distinctness round-trip) runs over the tone-bearing ones,
              which are the glyphs fonts silently drop marks on.

For a stacked char X we also need its base-without-tone (drop the tone, keep the modifier)
and base-without-modifier (drop the modifier, keep the tone), built by NFD surgery so the
gate can prove the rendered bitmaps are pixel-distinct.
"""
from __future__ import annotations

import unicodedata as ud

# combining marks
CIRCUMFLEX = "̂"
BREVE = "̆"
HORN = "̛"
TONES = {
    "sac": "́", "huyen": "̀", "hoi": "̉",
    "nga": "̃", "nang": "̣",
}

# the six modified-vowel families that also bear tones: base letter + its modifier mark
MODIFIED_BASES = {
    "a_circ": ("a", CIRCUMFLEX),  # â
    "a_breve": ("a", BREVE),      # ă
    "e_circ": ("e", CIRCUMFLEX),  # ê
    "o_circ": ("o", CIRCUMFLEX),  # ô
    "o_horn": ("o", HORN),        # ơ
    "u_horn": ("u", HORN),        # ư
}


def _nfc(s: str) -> str:
    return ud.normalize("NFC", s)


def stacked_chars():
    """Yield dicts for every tone-bearing stacked vowel, lower + upper case.

    Each dict: stacked (NFC), no_tone (NFC, modifier kept), no_mod (NFC, tone kept).
    """
    out = []
    for base, mod in MODIFIED_BASES.values():
        for tone in TONES.values():
            stacked = _nfc(base + mod + tone)          # e.g. ệ = e+circumflex+nang
            no_tone = _nfc(base + mod)                  # ê
            no_mod = _nfc(base + tone)                  # ẹ
            for cased in (str.lower, str.upper):
                out.append(dict(
                    stacked=cased(stacked),
                    no_tone=cased(no_tone),
                    no_mod=cased(no_mod),
                ))
    return out


def _vn_vowel_forms():
    """All precomposed Vietnamese vowel forms (base x modifier x tone), both cases."""
    forms = set()
    plain = {"a": "", "e": "", "i": "", "o": "", "u": "", "y": ""}
    mods = {
        "a": ["", CIRCUMFLEX, BREVE],
        "e": ["", CIRCUMFLEX],
        "o": ["", CIRCUMFLEX, HORN],
        "u": ["", HORN],
        "i": [""], "y": [""],
    }
    for base in plain:
        for m in mods[base]:
            for t in ["", *TONES.values()]:
                # y takes no tone-less-modifier combos beyond tones; skip impossible mods
                forms.add(_nfc(base + m + t))
    both = set()
    for f in forms:
        both.add(f.lower())
        both.add(f.upper())
    return both


def all_vn_letters():
    """Every Vietnamese letter the gate requires a glyph for (check 1)."""
    letters = set(_vn_vowel_forms())
    letters.update({"đ", "Đ"})
    # base consonants/vowels are ASCII and assumed present; the gate still checks đ/Đ and
    # every accented vowel, which is where coverage actually fails.
    return sorted(c for c in letters if c.strip())


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    letters = all_vn_letters()
    st = stacked_chars()
    print(f"ALL_VN letters (check 1): {len(letters)}")
    print("".join(letters))
    print(f"\nSTACKED tone-bearing forms (check 2): {len(st)} (lower+upper)")
    print(" ".join(sorted({d['stacked'] for d in st})))
