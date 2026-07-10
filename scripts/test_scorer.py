"""Self-tests for the ruler. BUILD_PLAN 0.3: the scorer is unit-tested on known strings
BEFORE any model number is trusted. A wrong ruler makes every later number meaningless.

Run:  python -m pytest scripts/test_scorer.py -q      (or: python scripts/test_scorer.py)
"""
import sys
import unicodedata as ud

sys.path.insert(0, ".")
from scripts.scorer import (  # noqa: E402
    Score, align, decompose, nfc, score_corpus, score_pair,
)

FAILS = []


def check(name, got, want):
    ok = got == want
    if not ok:
        FAILS.append(f"{name}: got {got!r}, want {want!r}")
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}: {got!r}")


def approx(name, got, want, tol=1e-9):
    ok = abs(got - want) < tol
    if not ok:
        FAILS.append(f"{name}: got {got!r}, want {want!r}")
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}: {got:.6f}")


print("=== decomposition: the two hazards, explicitly ===")

# EVAL_PROTOCOL §3.1 worked example: ệ -> e + circumflex + nặng(dot below)
d = decompose("ệ")
check("ệ base", d.base, "e")
check("ệ modifier", d.modifier, "circumflex")
check("ệ tone", d.tone, "nang")

# §3.1 worked example: ữ -> u + horn + ngã(tilde)
d = decompose("ữ")
check("ữ base", d.base, "u")
check("ữ modifier", d.modifier, "horn")
check("ữ tone", d.tone, "nga")

# HAZARD 1: đ has no NFD decomposition -> stroke must be injected by hand.
d = decompose("đ")
check("đ base", d.base, "d")
check("đ modifier", d.modifier, "stroke")
check("đ tone", d.tone, "ngang")
d = decompose("Đ")
check("Đ base", d.base, "D")
check("Đ modifier", d.modifier, "stroke")

# HAZARD 2: canonical mark ORDER differs. ệ puts the TONE first, ế puts the MODIFIER first.
# If the scorer read nfd[1] as "the modifier" it would call ệ's modifier 'nang'.
check("ệ NFD order", [hex(ord(c)) for c in ud.normalize("NFD", "ệ")],
      ["0x65", "0x323", "0x302"])
check("ế NFD order", [hex(ord(c)) for c in ud.normalize("NFD", "ế")],
      ["0x65", "0x302", "0x301"])
d = decompose("ế")
check("ế modifier", d.modifier, "circumflex")
check("ế tone", d.tone, "sac")

# plain / partial cases
check("a modifier", decompose("a").modifier, "none")
check("a tone", decompose("a").tone, "ngang")
check("ă modifier", decompose("ă").modifier, "breve")
check("ă tone", decompose("ă").tone, "ngang")
check("à tone", decompose("à").tone, "huyen")
check("ỷ tone", decompose("ỷ").tone, "hoi")
check("ơ modifier", decompose("ơ").modifier, "horn")

# axis-bearing predicates
check("ệ bears_tone", decompose("ệ").bears_tone, True)
check("d bears_modifier", decompose("d").bears_modifier, True)
check("i bears_modifier", decompose("i").bears_modifier, False)  # i takes tone, not modifier
check("i bears_tone", decompose("i").bears_tone, True)
check("5 is_letter", decompose("5").is_letter, False)
check("5 bears_tone", decompose("5").bears_tone, False)

print("\n=== NFC/NFD equivalence: a decomposed prediction must NOT be punished ===")
# This is exactly what §2's NFC rule protects against.
precomposed = "Điện"
decomposed = ud.normalize("NFD", "Điện")
check("differ as raw strings", precomposed == decomposed, False)
check("equal after nfc()", nfc(precomposed) == nfc(decomposed), True)
sc = Score()
score_pair(sc, precomposed, decomposed)
approx("CER(precomposed, decomposed) == 0", sc.cer, 0.0)
approx("tone acc == 1", sc.tone_acc, 1.0)

print("\n=== zero-width chars are stripped before scoring ===")
sc = Score()
score_pair(sc, "Điện", "Đi​ện")  # U+200B ZERO WIDTH SPACE, category Cf
approx("CER with ZWSP == 0", sc.cer, 0.0)

print("\n=== alignment / CER / WER arithmetic ===")
ops, dist = align("abc", "abc")
check("identical distance", dist, 0)
ops, dist = align("abc", "abd")
check("one sub distance", dist, 1)
ops, dist = align("abc", "ab")
check("one del distance", dist, 1)
ops, dist = align("ab", "abc")
check("one ins distance", dist, 1)

sc = Score()
score_pair(sc, "hello", "hallo")  # 1 substitution / 5 chars
approx("CER 1/5", sc.cer, 0.2)
approx("exact-match 0", sc.exact, 0.0)

sc = Score()
score_pair(sc, "a b c", "a b")  # 1 word deleted / 3 words
approx("WER 1/3", sc.wer, 1 / 3)

sc = score_corpus([("abc", "abc"), ("abc", "xbc")])  # corpus-level: 1 edit / 6 chars
approx("corpus CER 1/6", sc.cer, 1 / 6)
approx("corpus exact 1/2", sc.exact, 0.5)

print("\n=== the keystone: overall CER hides tone failure (G2) ===")
# Destroy ONLY the tones; keep every base letter. Overall CER looks mild,
# tone-axis accuracy collapses. This is the whole reason for §3.1.
ref = "tiếng Việt có dấu"
hyp = "tiêng Viêt co dâu"  # tones stripped, bases + modifiers intact
sc = Score()
score_pair(sc, ref, hyp)
print(f"    CER={sc.cer*100:.2f}%  base={sc.base_acc*100:.2f}%  "
      f"mod={sc.mod_acc*100:.2f}%  tone={sc.tone_acc*100:.2f}%")
check("base axis unharmed", sc.base_acc == 1.0, True)
check("tone axis < base axis", sc.tone_acc < sc.base_acc, True)
check("CER understates tone damage", sc.cer < (1 - sc.tone_acc), True)

print("\n=== hỏi <-> ngã confusion is caught on the tone axis only ===")
sc = Score()
score_pair(sc, "ả", "ã")  # same base, same modifier, different tone
approx("base acc 1.0", sc.base_acc, 1.0)
approx("modifier acc 1.0", sc.mod_acc, 1.0)
approx("tone acc 0.0", sc.tone_acc, 0.0)
check("confusion cell (hoi->nga)", sc.tone_cm[("hoi", "nga")], 1)

print("\n=== horn drop is caught on the modifier axis only ===")
sc = Score()
score_pair(sc, "ư", "u")
approx("base acc 1.0", sc.base_acc, 1.0)
approx("modifier acc 0.0", sc.mod_acc, 0.0)
approx("tone acc 1.0", sc.tone_acc, 1.0)
check("confusion cell (horn->none)", sc.mod_cm[("horn", "none")], 1)

print("\n=== deletion counts wrong on every axis the GT char bears ===")
sc = Score()
score_pair(sc, "ệ", "")
check("base_n", sc.base_n, 1)
check("mod_n", sc.mod_n, 1)
check("tone_n", sc.tone_n, 1)
approx("base acc 0", sc.base_acc, 0.0)
approx("mod acc 0", sc.mod_acc, 0.0)
approx("tone acc 0", sc.tone_acc, 0.0)
check("del recorded in tone cm", sc.tone_cm[("nang", "<del>")], 1)

print("\n=== insertion is charged to CER but creates no axis denominator ===")
sc = Score()
score_pair(sc, "a", "ab")
approx("CER 1/1", sc.cer, 1.0)
check("base_n stays 1 (only the GT 'a')", sc.base_n, 1)
approx("base acc 1.0", sc.base_acc, 1.0)

print("\n=== case-sensitivity: primary base axis is case-SENSITIVE ===")
sc = Score()
score_pair(sc, "A", "a")
approx("base acc (case-sensitive) 0", sc.base_acc, 0.0)
approx("base acc (case-insens) 1", sc.base_acc_ci, 1.0)

print()
if FAILS:
    print(f"!! {len(FAILS)} FAILURES")
    for f in FAILS:
        print("   -", f)
    sys.exit(1)
print("ALL SCORER SELF-TESTS PASSED")
