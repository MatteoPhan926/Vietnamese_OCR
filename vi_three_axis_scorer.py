"""vi_three_axis_scorer — CER/WER + a three-axis diacritic breakdown for Vietnamese OCR.

Single file. Standard library only. No dataset, no model, no dependencies.
Works on any Vietnamese OCR system's output — Tesseract, PaddleOCR, a cloud API, yours.

WHY THREE AXES. A Vietnamese glyph carries two orthogonal mark systems on one base letter:
a LETTER-FORMING MODIFIER (ă â ê ô ơ ư, and đ's stroke) and a TONE (á à ả ã ạ). A single
"accuracy" or "diacritic accuracy" number cannot tell you which one broke — and they break
for different reasons and are fixed by different things. Tone marks are also a small share of
all characters, so a model can post a fine CER while systematically destroying tones:

    >>> score([("tiếng Việt có dấu", "tiêng Viêt co dâu")]).report()
    CER 23.53% — but the TONE axis is at 42.86% while the BASE axis is a perfect 100%.

The overall CER understates the tone damage by more than 2x. That is the whole point.

USAGE (five lines)
------------------
    from vi_three_axis_scorer import score

    pairs = [("giá", "gia"), ("Việt Nam", "Viet Nam")]   # (ground_truth, prediction)
    s = score(pairs)
    print(s.report())                     # everything, formatted
    print(s.cer, s.tone_acc, s.base_acc)  # or pull the numbers out

CLI
---
    python vi_three_axis_scorer.py predictions.tsv        # TSV: ground_truth <TAB> prediction
    python vi_three_axis_scorer.py predictions.tsv --confusion

WHAT IT MEASURES
----------------
    CER / WER / exact-match   Levenshtein, on NFC-normalized strings.
    Axis 1  base letter       over every reference letter position       (a, e, d, ...)
    Axis 2  modifier          over reference letters that CAN take one   (a e o u d)
    Axis 3  tone              over reference letters that CAN bear one   (a e i o u y)

    Axes are scored on Levenshtein-ALIGNED positions after NFD decomposition. A deletion is
    charged as wrong on every axis the reference character bears (a dropped char is all-axes
    wrong). An insertion has no reference position, so no axis denominator exists for it — it
    is charged to CER/WER only. Both choices are stated rather than silently made.

TWO UNICODE HAZARDS THIS FILE IS BUILT AROUND (both found by measurement, not by reading)
-----------------------------------------------------------------------------------------
    1. 'đ'/'Đ' (U+0111/U+0110) have NO canonical decomposition — NFD leaves them whole. If you
       treat the stroke as a combining mark you will never once observe it, and Axis 2 will
       silently report a perfect score on every đ in your corpus. It is special-cased here.
    2. NFD returns combining marks in CANONICAL order (by combining class), NOT in
       "modifier then tone" order:
           'ệ' -> e + U+0323 dot-below + U+0302 circumflex     (tone comes FIRST)
           'ế' -> e + U+0302 circumflex + U+0301 acute         (modifier comes first)
       So marks are classified by CODEPOINT, never by position. Reading nfd[1] as "the
       modifier" mislabels ệ's tone as a modifier — a bug that inflates one axis and deflates
       the other while the total looks plausible.

Normalization: both sides are NFC-normalized and stripped of zero-width/format codepoints
before scoring. Skipping this silently inflates or deflates accuracy by an encoding mismatch
that looks exactly like a model result.

License: MIT. Copy it into your project; it is one file on purpose.
"""
from __future__ import annotations

import sys
import unicodedata as ud
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

__all__ = ["score", "score_pair", "Score", "decompose", "Decomposed", "nfc", "align",
           "TONE_MARKS", "MODIFIER_MARKS"]
__version__ = "1.0.0"

# ------------------------------------------------------------------ Unicode tables

TONE_MARKS = {
    "́": "sac",     # ́  acute        á
    "̀": "huyen",   # ̀  grave        à
    "̉": "hoi",     # ̉  hook above   ả
    "̃": "nga",     # ̃  tilde        ã
    "̣": "nang",    # ̣  dot below    ạ
}
NO_TONE = "ngang"        # the unmarked (level) tone -- a real tone, not "no tone"

MODIFIER_MARKS = {
    "̆": "breve",       # ̆  ă
    "̂": "circumflex",  # ̂  â ê ô
    "̛": "horn",        # ̛  ơ ư
}
NO_MODIFIER = "none"
STROKE = "stroke"        # đ -- no NFD decomposition exists; injected by hand (hazard 1)

MODIFIER_BASES = set("aeoud")   # letters that can take a modifier  -> Axis-2 denominator
TONE_BASES = set("aeiouy")      # letters that can bear a tone      -> Axis-3 denominator


@dataclass(frozen=True)
class Decomposed:
    """One glyph, split into its three axes. Case is preserved on `base`."""
    base: str        # 'e', 'E', 'd', ...
    modifier: str    # 'none' | 'breve' | 'circumflex' | 'horn' | 'stroke'
    tone: str        # 'ngang' | 'sac' | 'huyen' | 'hoi' | 'nga' | 'nang'

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
    """Split one character into (base, modifier, tone).

    >>> decompose("ệ")
    Decomposed(base='e', modifier='circumflex', tone='nang')
    >>> decompose("đ")
    Decomposed(base='d', modifier='stroke', tone='ngang')
    """
    nfd = ud.normalize("NFD", ch)
    base, marks = nfd[0], nfd[1:]
    modifier, tone = NO_MODIFIER, NO_TONE

    if base in ("đ", "Đ"):                      # hazard 1: no decomposition exists
        base = "d" if base == "đ" else "D"
        modifier = STROKE

    for m in marks:                             # hazard 2: classify by codepoint, not position
        if m in MODIFIER_MARKS:
            modifier = MODIFIER_MARKS[m]
        elif m in TONE_MARKS:
            tone = TONE_MARKS[m]

    return Decomposed(base, modifier, tone)


# ------------------------------------------------------------------ normalization

def nfc(s: str) -> str:
    """NFC-normalize and drop zero-width / format codepoints (Unicode category Cf)."""
    return ud.normalize("NFC", "".join(c for c in s if ud.category(c) != "Cf"))


# ------------------------------------------------------------------ alignment

def align(ref: Sequence, hyp: Sequence):
    """Levenshtein alignment. Returns (ops, distance).

    ops are ('eq'|'sub'|'del'|'ins', ref_item_or_None, hyp_item_or_None).
      'del' = a reference item the hypothesis never produced.
      'ins' = a hypothesis item with no reference counterpart.
    Works on any indexable sequence, so it serves characters (CER) and tokens (WER) alike.
    """
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i
    for j in range(1, m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    ops, i, j = [], n, m
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


# ------------------------------------------------------------------ the scorer

@dataclass
class Score:
    """Corpus-level totals. CER/WER are sum(edits)/sum(ref) — never a mean of per-sample rates."""
    char_edits: int = 0
    char_ref: int = 0
    word_edits: int = 0
    word_ref: int = 0
    exact_hit: int = 0
    n_samples: int = 0

    base_ok: int = 0
    base_n: int = 0
    base_ok_ci: int = 0          # case-insensitive diagnostic: how much "base error" is just case
    mod_ok: int = 0
    mod_n: int = 0
    tone_ok: int = 0
    tone_n: int = 0

    subs: int = 0
    dels: int = 0
    ins: int = 0

    base_cm: Counter = field(default_factory=Counter)   # (ref, hyp) -> count; hyp '<del>' if dropped
    mod_cm: Counter = field(default_factory=Counter)
    tone_cm: Counter = field(default_factory=Counter)

    def _r(self, num, den):
        return num / den if den else float("nan")

    @property
    def cer(self) -> float:
        return self._r(self.char_edits, self.char_ref)

    @property
    def wer(self) -> float:
        return self._r(self.word_edits, self.word_ref)

    @property
    def exact(self) -> float:
        return self._r(self.exact_hit, self.n_samples)

    @property
    def base_acc(self) -> float:
        return self._r(self.base_ok, self.base_n)

    @property
    def base_acc_ci(self) -> float:
        return self._r(self.base_ok_ci, self.base_n)

    @property
    def mod_acc(self) -> float:
        return self._r(self.mod_ok, self.mod_n)

    @property
    def tone_acc(self) -> float:
        return self._r(self.tone_ok, self.tone_n)

    # ---- output
    def report(self, scope: str = "rec-only", testset: str = "-") -> str:
        p = lambda v: "  nan  " if v != v else f"{v * 100:6.2f}%"  # noqa: E731
        return "\n".join([
            f"scope={scope}  testset={testset}  norm=NFC (axes: NFD)  n={self.n_samples}",
            f"  CER          {p(self.cer)}   ({self.char_edits} edits / {self.char_ref} chars)",
            f"  WER          {p(self.wer)}   ({self.word_edits} edits / {self.word_ref} words)",
            f"  exact-match  {p(self.exact)}",
            f"  Axis1 base   {p(self.base_acc)}   (n={self.base_n})"
            f"   [case-insens {p(self.base_acc_ci).strip()}]",
            f"  Axis2 modif  {p(self.mod_acc)}   (n={self.mod_n})",
            f"  Axis3 tone   {p(self.tone_acc)}   (n={self.tone_n})",
            f"  edits        sub={self.subs}  del={self.dels}  ins={self.ins}",
        ])

    def confusion(self, axis: str = "tone", top: int = 12) -> str:
        """The per-axis confusion matrix — which mark became which, most frequent first.

        This is the artifact that tells you *what to fix*: a tone that is DROPPED
        ('<del>' / 'ngang') is a visibility problem (resolution, blur); a tone CONFUSED for
        another tone is a shape problem (fonts, similar marks). They are different bugs.
        """
        cm = {"base": self.base_cm, "modifier": self.mod_cm, "tone": self.tone_cm}[axis]
        wrong = Counter({k: v for k, v in cm.items() if k[0] != k[1]})
        if not wrong:
            return f"  {axis}: no errors"
        lines = [f"  {axis} confusion (ref -> hyp), top {top}:"]
        for (r, h), c in wrong.most_common(top):
            lines.append(f"    {r:>12s} -> {h if h is not None else '<del>':<12s} {c:5d}")
        return "\n".join(lines)


def score_pair(sc: Score, ground_truth: str, prediction: str) -> None:
    """Accumulate one (ground_truth, prediction) pair into `sc`."""
    ref, hyp = nfc(ground_truth), nfc(prediction)

    ops, dist = align(ref, hyp)
    sc.char_edits += dist
    sc.char_ref += len(ref)

    _, wdist = align(ref.split(), hyp.split())
    sc.word_edits += wdist
    sc.word_ref += len(ref.split())

    sc.exact_hit += int(ref == hyp)
    sc.n_samples += 1

    for op, r, h in ops:
        if op == "ins":
            # No reference position -> no axis denominator exists. CER/WER only.
            sc.ins += 1
            continue

        dr = decompose(r)

        if op == "del":
            sc.dels += 1
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

        sc.subs += int(op == "sub")
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


def score(pairs: Iterable[tuple[str, str]]) -> Score:
    """Score an iterable of (ground_truth, prediction) pairs. This is the entry point."""
    sc = Score()
    for gt, pred in pairs:
        score_pair(sc, gt, pred)
    return sc


# ------------------------------------------------------------------ CLI

def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = argv[0]
    pairs = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip("\n"):
                continue
            parts = ln.rstrip("\n").split("\t")
            pairs.append((parts[0], parts[1] if len(parts) > 1 else ""))
    sc = score(pairs)
    print(sc.report(testset=path))
    if "--confusion" in argv:
        print()
        for ax in ("tone", "modifier", "base"):
            print(sc.confusion(ax))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
