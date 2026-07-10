"""The measurement ruler: EVAL_PROTOCOL §2/§3 made code.

Reports, for a corpus of (prediction, ground-truth) pairs:
  * CER, WER, exact-match      -- on NFC strings                     (§2)
  * the THREE diacritic axes   -- on NFD-decomposed aligned chars    (§3.1)
        Axis 1 base letter | Axis 2 modifier | Axis 3 tone
  * a per-axis confusion matrix                                       (§3.1, a deliverable)

Never collapse the three axes into one "diacritic accuracy" number: Vietnamese carries
two orthogonal systems on one glyph and a single number hides which one failed (G2).

Two Unicode facts this file is built around, both verified by measurement:

  (1) 'đ'/'Đ' (U+0111/U+0110) have NO canonical decomposition. NFD leaves them intact.
      EVAL_PROTOCOL §3.1 counts `stroke` as a modifier, so it MUST be special-cased or
      Axis 2 would never once observe a stroke.

  (2) Combining marks come back in CANONICAL ORDER (sorted by combining class), not in
      "modifier then tone" order:
          'ệ' -> e + U+0323 dot-below (ccc 220) + U+0302 circumflex (ccc 230)   tone first
          'ế' -> e + U+0302 circumflex (ccc 230) + U+0301 acute     (ccc 230)   modifier first
      So marks are classified by CODEPOINT membership, never by position.
"""
from __future__ import annotations

import unicodedata as ud
from collections import Counter
from dataclasses import dataclass, field

# ---------------------------------------------------------------- Unicode tables

TONE_MARKS = {
    "́": "sac",  # ́  acute
    "̀": "huyen",  # ̀  grave
    "̉": "hoi",  # ̉  hook above
    "̃": "nga",  # ̃  tilde
    "̣": "nang",  # ̣  dot below
}
NO_TONE = "ngang"

MODIFIER_MARKS = {
    "̆": "breve",  # ă
    "̂": "circumflex",  # â ê ô
    "̛": "horn",  # ơ ư
}
NO_MODIFIER = "none"
STROKE = "stroke"  # đ -- has no NFD decomposition, injected by hand

# bases that admit a letter-forming modifier (Axis-2 denominator)
MODIFIER_BASES = set("aeoud")
# bases that bear tone (Axis-3 denominator): Vietnamese tones sit on vowels
TONE_BASES = set("aeiouy")


@dataclass(frozen=True)
class Decomposed:
    base: str  # e.g. 'e'  (case preserved)
    modifier: str  # 'none' | 'breve' | 'circumflex' | 'horn' | 'stroke'
    tone: str  # 'ngang' | 'sac' | 'huyen' | 'hoi' | 'nga' | 'nang'

    @property
    def is_letter(self) -> bool:
        return self.base.isalpha()

    @property
    def bears_modifier(self) -> bool:
        return self.base.lower() in MODIFIER_BASES

    @property
    def bears_tone(self) -> bool:
        return self.base.lower() in TONE_BASES


def decompose(ch: str) -> Decomposed:
    """Split one NFC glyph into (base, modifier, tone) -- §3.1."""
    nfd = ud.normalize("NFD", ch)
    base, marks = nfd[0], nfd[1:]

    modifier, tone = NO_MODIFIER, NO_TONE

    # (1) 'đ'/'Đ' do not decompose; the stroke IS the modifier.
    if base in ("đ", "Đ"):
        base = "d" if base == "đ" else "D"
        modifier = STROKE

    # (2) classify each mark by codepoint, NOT by position.
    for m in marks:
        if m in MODIFIER_MARKS:
            modifier = MODIFIER_MARKS[m]
        elif m in TONE_MARKS:
            tone = TONE_MARKS[m]

    return Decomposed(base, modifier, tone)


# ---------------------------------------------------------------- normalization

def clean(s: str) -> str:
    """Strip zero-width / format codepoints before any scoring (§2)."""
    return "".join(c for c in s if ud.category(c) != "Cf")


def nfc(s: str) -> str:
    return ud.normalize("NFC", clean(s))


# ---------------------------------------------------------------- alignment

def align(ref: str, hyp: str):
    """Levenshtein alignment. Yields ops as ('eq'|'sub'|'del'|'ins', r_char, h_char).

    'del' = a reference char with no hypothesis counterpart.
    'ins' = a hypothesis char with no reference counterpart.
    Returns (ops, distance).
    """
    n, m = len(ref), len(hyp)
    # d[i][j] = edit distance ref[:i] -> hyp[:j]
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i
    for j in range(1, m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            if d[i][j] == d[i - 1][j - 1] + cost:
                ops.append(("eq" if cost == 0 else "sub", ref[i - 1], hyp[j - 1]))
                i, j = i - 1, j - 1
                continue
        if i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("del", ref[i - 1], None))
            i -= 1
            continue
        ops.append(("ins", None, hyp[j - 1]))
        j -= 1
    ops.reverse()
    return ops, d[n][m]


# ---------------------------------------------------------------- the scorer

@dataclass
class Score:
    # CER / WER / exact-match are corpus-level: sum(edits) / sum(ref_len)
    char_edits: int = 0
    char_ref: int = 0
    word_edits: int = 0
    word_ref: int = 0
    exact_hit: int = 0
    n_samples: int = 0

    # three axes: correct / bearing-positions
    base_ok: int = 0
    base_n: int = 0
    base_ok_ci: int = 0  # case-insensitive diagnostic
    mod_ok: int = 0
    mod_n: int = 0
    tone_ok: int = 0
    tone_n: int = 0

    base_cm: Counter = field(default_factory=Counter)
    mod_cm: Counter = field(default_factory=Counter)
    tone_cm: Counter = field(default_factory=Counter)

    # ---- derived
    @property
    def cer(self):
        return self.char_edits / self.char_ref if self.char_ref else float("nan")

    @property
    def wer(self):
        return self.word_edits / self.word_ref if self.word_ref else float("nan")

    @property
    def exact(self):
        return self.exact_hit / self.n_samples if self.n_samples else float("nan")

    @property
    def base_acc(self):
        return self.base_ok / self.base_n if self.base_n else float("nan")

    @property
    def base_acc_ci(self):
        return self.base_ok_ci / self.base_n if self.base_n else float("nan")

    @property
    def mod_acc(self):
        return self.mod_ok / self.mod_n if self.mod_n else float("nan")

    @property
    def tone_acc(self):
        return self.tone_ok / self.tone_n if self.tone_n else float("nan")


def score_pair(sc: Score, ref_raw: str, hyp_raw: str) -> None:
    """Accumulate one (ground-truth, prediction) pair into `sc`."""
    ref, hyp = nfc(ref_raw), nfc(hyp_raw)

    # ---- CER / WER / exact-match, on NFC (§2)
    _, dist = align(ref, hyp)
    sc.char_edits += dist
    sc.char_ref += len(ref)

    rw, hw = ref.split(), hyp.split()
    _, wdist = align(rw, hw)  # align() is char/token agnostic (indexable sequences)
    sc.word_edits += wdist
    sc.word_ref += len(rw)

    sc.exact_hit += int(ref == hyp)
    sc.n_samples += 1

    # ---- three axes, on NFD-decomposed ALIGNED chars (§3.1)
    ops, _ = align(ref, hyp)
    for op, r, h in ops:
        if op == "ins":
            # No reference position exists, so no axis denominator exists. Insertions are
            # charged to CER only. (EVAL_PROTOCOL §3.1 says "deletion/insertion counts as
            # all applicable axes wrong"; for an insertion the *applicable* axes are
            # undefined -- there is no GT char to ask what it bears. Documented deviation.)
            continue

        dr = decompose(r)

        if op == "del":
            # a GT char the model never emitted: wrong on every axis it bears.
            if dr.is_letter:
                sc.base_n += 1
                sc.base_cm[(dr.base, "<del>")] += 1
            if dr.bears_modifier:
                sc.mod_n += 1
                sc.mod_cm[(dr.modifier, "<del>")] += 1
            if dr.bears_tone:
                sc.tone_n += 1
                sc.tone_cm[(dr.tone, "<del>")] += 1
            continue

        dh = decompose(h)

        if dr.is_letter:
            sc.base_n += 1
            sc.base_ok += int(dr.base == dh.base)
            sc.base_ok_ci += int(dr.base.lower() == dh.base.lower())
            sc.base_cm[(dr.base, dh.base)] += 1
        if dr.bears_modifier:
            sc.mod_n += 1
            sc.mod_ok += int(dr.modifier == dh.modifier)
            sc.mod_cm[(dr.modifier, dh.modifier)] += 1
        if dr.bears_tone:
            sc.tone_n += 1
            sc.tone_ok += int(dr.tone == dh.tone)
            sc.tone_cm[(dr.tone, dh.tone)] += 1


def score_corpus(pairs) -> Score:
    sc = Score()
    for ref, hyp in pairs:
        score_pair(sc, ref, hyp)
    return sc


def format_score(sc: Score, scope: str, testset: str) -> str:
    return "\n".join([
        f"scope={scope}  testset={testset}  norm=NFC (axes: NFD)  n={sc.n_samples}",
        f"  CER          {sc.cer*100:6.2f}%   ({sc.char_edits} edits / {sc.char_ref} chars)",
        f"  WER          {sc.wer*100:6.2f}%   ({sc.word_edits} edits / {sc.word_ref} words)",
        f"  exact-match  {sc.exact*100:6.2f}%",
        f"  Axis1 base   {sc.base_acc*100:6.2f}%   (n={sc.base_n})   [case-insens {sc.base_acc_ci*100:.2f}%]",
        f"  Axis2 modif  {sc.mod_acc*100:6.2f}%   (n={sc.mod_n})",
        f"  Axis3 tone   {sc.tone_acc*100:6.2f}%   (n={sc.tone_n})",
    ])
