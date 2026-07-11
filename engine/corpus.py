"""The synthetic corpus (DATA_ENGINE §4) — scene-leaning, license-clean, firewalled.

Two sources, mixed scene-heavy:
  Source B (up-weighted, scene domain): VinText TRAIN-split transcripts, verbatim. These ARE
    the target distribution -- per-word, short (median 3 chars), 68% ALLCAPS -- so sampling
    them injects the scene domain directly. Firewall (EVAL_PROTOCOL §10): TRAIN split only,
    never val/test.
  Source A (down-weighted, breadth + natural diacritic frequency): wiki_vi syllable tokens.
    Vietnamese is monosyllabic per whitespace token, so a wiki token is already short and
    matches the scene per-word length -- no truncation needed. Wiki is lowercase prose, so
    case AUGMENTATION reshapes it to the measured scene case mix.

MEASURED length/case targets (VinText train, 25,776 scorable; supersedes §4's "1-4 tokens"
guess): 99.0% single-token; char median 3, p90 5; case 67.9% UPPER / 15.6% Title / 21.7%
has-lower; 6.6% single-char; 10.2% contain a digit. §12 requires very short / 1-char crops.

Build the wiki bank once (network) -> data/synth/corpus/wiki_tokens.tsv; the sampler then
runs offline and deterministically from a seed.
"""
from __future__ import annotations

import os
import random
import re
import sys
import unicodedata as ud
from collections import Counter

import yaml

sys.path.insert(0, ".")
from scripts.vintext import iter_instances  # noqa: E402

CORPUS_DIR = os.path.join("data", "synth", "corpus")
WIKI_TSV = os.path.join(CORPUS_DIR, "wiki_tokens.tsv")
SCENE_TXT = os.path.join(CORPUS_DIR, "scene_phrases.txt")

VOCAB = set(yaml.safe_load(open("configs/vgg_transformer_pinned.yml", encoding="utf-8"))["vocab"])
# tokens are split on whitespace; keep leading/trailing punctuation off but preserve
# internal (e.g. "3/4", "T.P"). A token is usable only if every char is in the locked vocab.
_STRIP = " \t\r\n\"'()[]{}<>«»“”‘’.,;:!?…·•|/\\"


def _clean_token(tok: str) -> str | None:
    t = ud.normalize("NFC", tok).strip(_STRIP)
    if not t:
        return None
    if any(c not in VOCAB for c in t):
        return None
    # drop tokens that are pure punctuation/symbols (no letter or digit)
    if not re.search(r"[0-9A-Za-zÀ-ỹ]", t):
        return None
    return t


# ----------------------------------------------------------------- bank building
def build_wiki_bank(max_tokens=2_000_000, max_articles=20_000):
    """Stream wiki_vi, tokenize to syllable tokens, write a frequency table."""
    from datasets import load_dataset

    os.makedirs(CORPUS_DIR, exist_ok=True)
    ds = load_dataset("wikimedia/wikipedia", "20231101.vi", split="train", streaming=True)
    freq: Counter = Counter()
    n_tok = n_art = 0
    for ex in ds:
        n_art += 1
        for raw in ex["text"].split():
            t = _clean_token(raw)
            if t is None:
                continue
            freq[t.lower()] += 1  # store lowercased; case is applied at sample time
            n_tok += 1
        if n_tok >= max_tokens or n_art >= max_articles:
            break
    with open(WIKI_TSV, "w", encoding="utf-8") as f:
        for tok, c in freq.most_common():
            f.write(f"{tok}\t{c}\n")
    print(f"wiki bank: {len(freq)} unique tokens from {n_tok} tokens / {n_art} articles -> {WIKI_TSV}")
    return len(freq), n_tok, n_art


def build_scene_bank():
    """Write VinText TRAIN transcripts verbatim (NFC). Firewall: train split ONLY."""
    os.makedirs(CORPUS_DIR, exist_ok=True)
    seen = []
    for inst in iter_instances("train", scorable_only=True):
        t = inst.nfc
        if all(c in VOCAB for c in t):
            seen.append(t)
    with open(SCENE_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(seen) + "\n")
    print(f"scene bank: {len(seen)} VinText-train transcripts (verbatim) -> {SCENE_TXT}")
    return len(seen)


def strict_bank_path(r: int) -> str:
    return os.path.join(CORPUS_DIR, f"scene_phrases_r{r}.txt")


def build_strict_scene_bank(r: int) -> str:
    """EVAL_PROTOCOL §14.2 (C1) — the STRICT-BANK Source B.

    The full bank (SCENE_TXT) holds all 25,742 train transcripts. But transcripts ARE labels: a
    practitioner at real-label budget r holds only the r-subset's transcripts, so a generator that
    draws Source B from the full bank spends label information beyond its stated budget. This
    builds Source B from the r-subset's OWN transcripts only -- the crop-level nested subset that
    the +synth arm at budget r actually trains on (data/crops/annotation_train_r{r}.txt).

    Everything else about the corpus is unchanged (same wiki bank, same source_b_prob, same case /
    length sampling): one variable at a time.
    """
    ann = os.path.join("data", "crops", f"annotation_train_r{r}.txt")
    seen = []
    for ln in open(ann, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln.strip():
            continue
        t = ud.normalize("NFC", ln.split("\t", 1)[1])
        if all(c in VOCAB for c in t):
            seen.append(t)
    out = strict_bank_path(r)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(seen) + "\n")
    print(f"strict scene bank r={r}%: {len(seen)} transcripts (r-subset ONLY) -> {out}")
    return out


# ----------------------------------------------------------------- the sampler
# measured scene case mix (VinText train)
CASE_UPPER, CASE_TITLE = 0.68, 0.16  # remainder -> keep-as-is (lower/mixed)
SINGLE_CHAR_RATE = 0.06              # match measured 6.6% isolated 1-char crops (§12)
SOURCE_B_PROB = 0.65                 # scene-heavy mix (§4 [CONJECTURE]); A/B-able later
DIGIT_GLYPHS = "0123456789"
LETTER_GLYPHS = "aăâbcdđeêghiklmnoôơpqrstuưvxy"


class Corpus:
    def __init__(self, seed=0, source_b_prob=SOURCE_B_PROB, single_char_rate=SINGLE_CHAR_RATE,
                 short_rate=0.0, scene_bank=None):
        """short_rate: extra probability of forcing a 1-2 char string (DATA_ENGINE §8.3 strata
        targeting -- the measured 1-2-char / small-crop failure stratum).

        scene_bank: path to the Source-B transcript bank. Default = the FULL train bank (the
        pre-registered primary run). §14.2 (C1) passes an r-restricted bank instead."""
        self.rng = random.Random(seed)
        self.source_b_prob = source_b_prob
        self.single_char_rate = single_char_rate
        self.short_rate = short_rate
        self.scene_bank = scene_bank or SCENE_TXT
        self.scene = [ln.rstrip("\n") for ln in open(self.scene_bank, encoding="utf-8") if ln.strip()]
        self.wiki, w = [], []
        for ln in open(WIKI_TSV, encoding="utf-8"):
            tok, c = ln.rstrip("\n").split("\t")
            self.wiki.append(tok)
            w.append(int(c))
        self.wiki_w = w  # frequency weights -> natural diacritic distribution

    def _recase(self, s: str) -> str:
        r = self.rng.random()
        if r < CASE_UPPER:
            return s.upper()
        if r < CASE_UPPER + CASE_TITLE:
            return s.title()
        return s  # keep source case

    def _single_char(self) -> str:
        # isolated 1-char crop: §12 finding (isolated char destroys letter identity ->
        # small-text legibility signal). Mix digits and letters roughly at scene rates.
        if self.rng.random() < 0.35:
            return self.rng.choice(DIGIT_GLYPHS)
        ch = self.rng.choice(LETTER_GLYPHS)
        return ch.upper() if self.rng.random() < CASE_UPPER else ch

    def _short(self) -> str:
        """A 1-2 character string (the measured short-crop failure stratum)."""
        if self.rng.random() < 0.45:
            return self._single_char()
        return self._single_char() + self._single_char()

    def sample(self) -> str:
        if self.rng.random() < self.single_char_rate:
            return self._single_char()
        if self.short_rate and self.rng.random() < self.short_rate:
            return self._short()
        if self.rng.random() < self.source_b_prob:
            # Source B: a real scene transcript, verbatim (case already scene-realistic)
            return self.rng.choice(self.scene)
        # Source A: wiki syllable token, frequency-weighted, then case-augmented.
        # 99% single-token to match the measured per-word distribution; rare 2-token.
        tok = self.rng.choices(self.wiki, weights=self.wiki_w, k=1)[0]
        if self.rng.random() < 0.01:
            tok2 = self.rng.choices(self.wiki, weights=self.wiki_w, k=1)[0]
            tok = f"{tok} {tok2}"
        return self._recase(tok)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.exists(SCENE_TXT):
        build_scene_bank()
    if not os.path.exists(WIKI_TSV):
        build_wiki_bank()
    c = Corpus(seed=1)
    print("\n40 samples:")
    for _ in range(40):
        print("  ", repr(c.sample()))
