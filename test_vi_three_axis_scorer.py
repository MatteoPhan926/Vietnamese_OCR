"""Unit tests for vi_three_axis_scorer. Standard library only.

    python -m unittest test_vi_three_axis_scorer -v
    python test_vi_three_axis_scorer.py

These are the tests that have to pass BEFORE any model number is trusted. A scorer bug and a
model regression look identical in a results table, and only one of them is visible here.
"""
from __future__ import annotations

import unittest

from vi_three_axis_scorer import Score, align, decompose, nfc, score, score_pair


class TestDecompose(unittest.TestCase):
    """The two Unicode hazards, pinned."""

    def test_plain_letter(self):
        d = decompose("a")
        self.assertEqual((d.base, d.modifier, d.tone), ("a", "none", "ngang"))

    def test_tone_only(self):
        for ch, tone in (("á", "sac"), ("à", "huyen"), ("ả", "hoi"), ("ã", "nga"), ("ạ", "nang")):
            d = decompose(ch)
            self.assertEqual((d.base, d.modifier, d.tone), ("a", "none", tone), ch)

    def test_modifier_only(self):
        for ch, mod in (("ă", "breve"), ("â", "circumflex"), ("ê", "circumflex"),
                        ("ô", "circumflex"), ("ơ", "horn"), ("ư", "horn")):
            d = decompose(ch)
            self.assertEqual(d.modifier, mod, ch)
            self.assertEqual(d.tone, "ngang", ch)

    def test_stacked_tone_first_in_nfd(self):
        # HAZARD 2: NFD gives 'ệ' as e + dot-below + circumflex -- the TONE comes first.
        # Reading nfd[1] as "the modifier" would label this tone as a modifier.
        d = decompose("ệ")
        self.assertEqual((d.base, d.modifier, d.tone), ("e", "circumflex", "nang"))

    def test_stacked_modifier_first_in_nfd(self):
        d = decompose("ế")
        self.assertEqual((d.base, d.modifier, d.tone), ("e", "circumflex", "sac"))

    def test_stacked_horn_plus_tilde(self):
        d = decompose("ữ")
        self.assertEqual((d.base, d.modifier, d.tone), ("u", "horn", "nga"))

    def test_d_stroke_has_no_decomposition(self):
        # HAZARD 1: NFD leaves đ whole. Without the special case Axis 2 never sees a stroke.
        import unicodedata as ud
        self.assertEqual(ud.normalize("NFD", "đ"), "đ")     # the hazard itself
        d = decompose("đ")
        self.assertEqual((d.base, d.modifier, d.tone), ("d", "stroke", "ngang"))
        self.assertTrue(d.bears_modifier)

    def test_case_preserved(self):
        self.assertEqual(decompose("Ệ").base, "E")
        self.assertEqual(decompose("Đ").base, "D")

    def test_axis_denominators(self):
        self.assertTrue(decompose("a").bears_tone)
        self.assertTrue(decompose("y").bears_tone)
        self.assertFalse(decompose("d").bears_tone)      # d takes a stroke but never a tone
        self.assertTrue(decompose("d").bears_modifier)
        self.assertFalse(decompose("i").bears_modifier)  # i takes a tone but never a modifier
        self.assertFalse(decompose("1").is_letter)


class TestNormalization(unittest.TestCase):
    def test_nfd_input_is_normalized(self):
        composed, decomposed = "ệ", "ệ"
        self.assertNotEqual(composed, decomposed)                 # different strings...
        self.assertEqual(nfc(decomposed), composed)               # ...same text
        self.assertEqual(score([(composed, decomposed)]).cer, 0)  # so CER must be 0, not 2/1

    def test_zero_width_stripped(self):
        self.assertEqual(nfc("Vi​ệt"), "Việt")
        self.assertEqual(score([("Việt", "Vi​ệt")]).exact, 1.0)


class TestAlign(unittest.TestCase):
    def test_distance(self):
        self.assertEqual(align("abc", "abc")[1], 0)
        self.assertEqual(align("abc", "abd")[1], 1)
        self.assertEqual(align("abc", "ab")[1], 1)
        self.assertEqual(align("ab", "abc")[1], 1)

    def test_op_kinds(self):
        ops, _ = align("ab", "axb")
        self.assertEqual([o[0] for o in ops], ["eq", "ins", "eq"])
        ops, _ = align("axb", "ab")
        self.assertEqual([o[0] for o in ops], ["eq", "del", "eq"])

    def test_works_on_tokens_not_just_chars(self):
        self.assertEqual(align(["ha", "noi"], ["ha", "noi"])[1], 0)
        self.assertEqual(align(["ha", "noi"], ["ha"])[1], 1)


class TestScoring(unittest.TestCase):
    def test_perfect(self):
        s = score([("Việt Nam", "Việt Nam")])
        self.assertEqual(s.cer, 0.0)
        self.assertEqual(s.wer, 0.0)
        self.assertEqual(s.exact, 1.0)
        self.assertEqual(s.tone_acc, 1.0)
        self.assertEqual(s.base_acc, 1.0)
        self.assertEqual(s.mod_acc, 1.0)

    def test_corpus_level_not_mean_of_rates(self):
        # 1 edit over 5 ref chars total => 20%, NOT mean(1/1, 0/4) = 50%.
        s = score([("a", "b"), ("abcd", "abcd")])
        self.assertAlmostEqual(s.cer, 1 / 5)

    def test_tone_stripped_is_the_headline_demo(self):
        # THE reason the three axes exist: CER understates the tone damage by >2x.
        s = score([("tiếng Việt có dấu", "tiêng Viêt co dâu")])
        self.assertAlmostEqual(s.cer * 100, 23.53, places=1)
        self.assertAlmostEqual(s.tone_acc * 100, 42.86, places=1)
        self.assertEqual(s.base_acc, 1.0)      # every base letter is right...
        self.assertEqual(s.mod_acc, 1.0)       # ...and every modifier is right
        # ...so the damage is tone-only, and CER hides more than half of it:
        self.assertGreater(1 - s.tone_acc, 2 * s.cer)

    def test_deletion_charges_every_axis_it_bears(self):
        # 'ệ' dropped: base, modifier and tone are each charged one wrong.
        s = score([("ệ", "")])
        self.assertEqual((s.base_n, s.base_ok), (1, 0))
        self.assertEqual((s.mod_n, s.mod_ok), (1, 0))
        self.assertEqual((s.tone_n, s.tone_ok), (1, 0))
        self.assertEqual(s.dels, 1)

    def test_insertion_charges_no_axis(self):
        # No reference position exists -> no axis denominator. CER only. (Documented choice.)
        s = score([("a", "aX")])
        self.assertEqual(s.ins, 1)
        self.assertEqual(s.base_n, 1)          # only the 'a', not the inserted 'X'
        self.assertEqual(s.base_acc, 1.0)
        self.assertAlmostEqual(s.cer, 1.0)     # 1 edit / 1 ref char

    def test_modifier_denominator_excludes_letters_that_cannot_take_one(self):
        s = score([("in", "in")])              # i, n: neither takes a modifier
        self.assertEqual(s.mod_n, 0)
        self.assertEqual(s.base_n, 2)
        self.assertNotEqual(s.mod_acc, s.mod_acc)   # nan, not a fake 100%

    def test_case_insensitive_diagnostic(self):
        s = score([("Anh", "anh")])
        self.assertLess(s.base_acc, 1.0)       # case-sensitive: the 'A' is wrong
        self.assertEqual(s.base_acc_ci, 1.0)   # case-insensitive: nothing is wrong

    def test_wrong_tone_vs_dropped_tone_are_different_cells(self):
        dropped = score([("á", "a")])
        confused = score([("á", "à")])
        self.assertEqual(dropped.tone_acc, 0.0)
        self.assertEqual(confused.tone_acc, 0.0)          # same axis accuracy...
        self.assertEqual(dropped.tone_cm[("sac", "ngang")], 1)    # ...different confusion cell:
        self.assertEqual(confused.tone_cm[("sac", "huyen")], 1)   # visibility bug vs shape bug

    def test_empty_prediction(self):
        s = score([("Việt", "")])
        self.assertEqual(s.cer, 1.0)
        self.assertEqual(s.exact, 0.0)

    def test_score_pair_accumulates(self):
        sc = Score()
        score_pair(sc, "a", "a")
        score_pair(sc, "b", "c")
        self.assertEqual(sc.n_samples, 2)
        self.assertAlmostEqual(sc.cer, 0.5)

    def test_report_and_confusion_render(self):
        s = score([("tiếng", "tiêng")])
        self.assertIn("Axis3 tone", s.report())
        self.assertIn("sac", s.confusion("tone"))


class TestParityWithTheProjectScorer(unittest.TestCase):
    """The standalone file must agree with the scorer that produced every number in RESULTS.md.

    If this drifts, the artifact people copy out of the repo is no longer the instrument that
    was actually used. Skipped when the project scorer is not present (i.e. for anyone who
    copied this single file out on its own — which is the entire point of it).
    """

    def test_parity(self):
        try:
            from scripts import scorer as project
        except Exception:
            self.skipTest("project scorer not importable (standalone use)")

        pairs = [
            ("tiếng Việt có dấu", "tiêng Viêt co dâu"),
            ("ĐƯỜNG", "DUONG"), ("Nguyễn", "Nguyên"), ("0583.871197", "0587.87"),
            ("phở", "pho"), ("ệ", ""), ("a", "aX"), ("Anh", "anh"), ("", ""),
        ]
        mine, theirs = score(pairs), project.score_corpus(pairs)
        for attr in ("cer", "wer", "exact", "base_acc", "base_acc_ci", "mod_acc", "tone_acc"):
            a, b = getattr(mine, attr), getattr(theirs, attr)
            if a != a and b != b:      # both nan
                continue
            self.assertAlmostEqual(a, b, places=12, msg=attr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
