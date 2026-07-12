# PAGE_SPEC.md — the public layer (narrative spine + honesty rules)

> **What this is.** The brain-side spec for the project page + README. The method docs say what is
> correct; this says **what the reader is told, in what order, in whose voice.** Claude Code implements
> this; it does not invent the story.
>
> **The framing, once, so nothing drifts from it:** this is **not** a method paper and must never posture
> as one. There is no new architecture and no SOTA number. The contribution is **epistemic**: a
> pre-registered, controlled, honestly-reported answer to a question practitioners actually face and
> almost nobody tests — *is synthetic data worth generating, or should you just augment harder?* The
> negative results are the product, not the embarrassment.

---

## 1. Title and the one-paragraph abstract

**Title (lead with the question, not a method):**
> **"Is synthetic data worth generating? A pre-registered study on Vietnamese scene-text OCR."**

**Abstract (the three findings, negatives first, every number scoped):**
> A synthetic data engine for Vietnamese scene text — fonts, corpus, degradation, the usual stack — built
> against a document-pretrained VietOCR recognizer and measured on real VinText held-out (rec-only,
> k seeds, pre-registered gates). **At full real data (25,742 crops) it is worth nothing**: not when the
> generator matches the real crop-statistics, not when it over-represents the measured failure strata, and
> not against a baseline whose augmentation was cranked to manufacture those same strata — the control arm
> almost nobody runs. **At a 2,574-crop label budget it is worth ≈2,200 real annotations** (CER 16.51 →
> 13.73, non-overlapping 95% CIs), decaying to nil by 50% of the labels. **And the mechanism is not the
> one it was built for**: the gain comes from repairing premature decoder termination on long strings, not
> from the domain-realism machinery the engine's design was organised around.

---

## 2. TL;DR box (above the fold, three bullets, in this order)

1. **Full real data → synthetic buys 0.** Augmentation-matched control included.
2. **Scarce labels (10%) → synthetic ≈ 2.2k real crops** [range 1.68k–2.55k], and the value decays
   monotonically with the label budget.
3. **The mechanism is not the realism stack** — it's decoder-truncation repair. The knobs we tuned are
   not the knobs that paid.

**The money figure = the label-efficiency curve** (gap vs r, both arms, CIs). It goes at the top. Second
figure = the truncation histogram (predicted vs GT length, real-only vs +synth at r=10%).

---

## 3. The story (siboehm-style: a journey where every step has a number and a falsification)

Written in **first person, plain past tense, no marketing register.** Each act ends with the measurement
that forced the next one.

- **Act 0 — The setup.** A document-pretrained recognizer, 25.7k real scene-text crops, and the question:
  can synthetic data close what's left? Pre-registration written first (link), thresholds frozen.
- **Act 1 — My hypothesis died first.** I predicted diacritics dominate the error. Built a three-axis
  scorer (base / modifier / tone) to prove it. It refuted me: base errors outweigh diacritics ~2.5×. But
  the instrument survived its own verdict — tone is the most fragile axis *per position*, base is the
  largest contributor *in total*, and only the decomposition shows both. **A single CER hides both.**
- **Act 2 — The gate said no.** 10k synthetic, matched to real's crop-statistics, on top of full real
  data: every metric flat. The pre-registered gate said RED. It also said *stop* — don't scale to 200k.
- **Act 3 — First I suspected my code, not the world.** ~26% of the synthetic crops were degraded past
  legibility. Fixed. The predicted signature (inflated seed variance) vanished exactly as predicted —
  ±0.895 → ±0.237. Still RED.
- **Act 4 — Then I suspected my comparator.** The baseline already ran vietocr's augmentation: blur,
  noise, JPEG, perspective — *on real crops, every epoch*. So I built the arm almost nobody builds:
  **real data with augmentation cranked to manufacture the exact failure strata, no synthetic at all.**
  At matched augmentation, **synthetic contributed nothing** (|Δ| < 0.17 pp, all CIs overlapping). A real
  crop degraded hard beats a rendered crop degraded hard. *(Also: "just augment harder" is not free — it
  buys per-character robustness and pays in sequence-length errors.)*
- **Act 5 — The pivot was pre-registered, not invented.** The budget axis was reserved before any of this
  ran. Sweep the real-label budget: **the gap is monotone.** Green at 10% and (before correction) 25%;
  nil at 50% and 100%.
- **Act 6 — Then I attacked my own green, twice.** The synthetic corpus had been drawing text from the
  *full* train transcript bank — but transcripts are labels, and a practitioner at a 10% budget doesn't
  have them. Regenerated with a strict bank: the 10% green survived at 84% of its size; **the 25% green
  died.** Re-ran the headline point at k=5 (pre-committed to replace k=3 in either direction): it held.
- **Act 7 — And the mechanism isn't what I built.** The gain concentrates in *long* crops (54% of it),
  not the tilted ones the engine was designed around (2.8%, not significant). At a scarce budget the
  decoder terminates early and truncates ~25% of long strings; the synthetic fixes that. The realism
  knobs are precisely where it didn't pay. *(Clean-render control: [PENDING — fills this slot.])*

---

## 4. Results section

- **Full table**: every arm (A baseline / B strata-aug / C aug+synth), every budget point, with
  **scope + n + k + CI** on every row. Negative rows are not smaller or greyer than positive ones.
- **Context row [OPTIONAL, high value / low cost]:** off-the-shelf Vietnamese OCR (Tesseract-vie,
  EasyOCR, PaddleOCR) on the **same test-500, rec-only, same scorer** — inference only, no training.
  Right now a reader cannot tell whether 9.4% CER is good; this fixes that, and it doubles as a live demo
  of the three-axis scorer on systems that are not ours. Label it clearly: *context, not a contest*
  (different training data, different scopes).
- **Gold noise floor** [PENDING pass 2]: quoted as a **lower bound** ("public labels contain ≥ X% …"),
  with the blind-vs-assisted disagreement rate stated.

---

## 5. Sections most portfolios skip (these are the senior signal)

- **"What I'd do differently."** Name the real ones: the operating point should have been chosen *after*
  measuring how much of the domain gap the real fine-tune already closes; the degradation stack was
  organised around a stratum ranking that turned out not to drive the gain; one subset draw per budget
  point (training-seed variance only).
- **"What this does not claim."** Not an e2e promise (rec-only headline; detection is deferred and its
  ceiling is stated). Not other languages. Not that synthetic teaches Vietnamese (the prior does).
  Not a curve beyond the measured budgets.
- **"The pre-registration."** Link `docs/`. State plainly: *these were written before the experiments they
  govern, and the git history proves the ordering.* This is the project's spine — **do not hide it, do not
  rewrite it, do not delete it.** Every credible claim on this page rests on it.
- **"How this was built" (optional, author's call).** A short methods note — design partner + agentic
  implementation, every gate adjudicated by hand, the manual gold pass done by the author. Matter-of-fact,
  not a confession. Being able to describe the workflow precisely is itself a signal.

---

## 6. Reproducibility (the demo problem, solved by shipping what *is* runnable)

VinText is not redistributable, so "clone and run the paper" is impossible. Ship the parts that stand
alone:
1. **The three-axis diacritic scorer, standalone and unit-tested** — needs no dataset, works on anyone's
   Vietnamese OCR output. This is the single most reusable artifact the project produced; package it so it
   can be `pip install`-ed or copied as one file, with a 5-line usage example.
2. **The synthetic generator**, runnable without VinText (bundle a few CC-licensed background patches and
   the font manifest; wiki_vi is public).
3. **The trained checkpoint + a `demo.py`** that reads any image and prints the three-axis breakdown.
4. **A short screen recording / GIF**: the generator producing crops → the scorer breaking down a
   prediction. No dataset needed to watch it work.
5. Exact commands, seeds, package versions, hardware (RTX 4060 Laptop, 8 GB).

---

## 7. Voice and hard rules

- **First person, past tense, plain.** No "we propose", no "novel", no "state-of-the-art". The register is
  a lab notebook that happens to be well-lit — the reader should feel they are watching someone think.
- **Every number carries its scope**: rec-only, test-500, NFC, k seeds, CI. A number without scope is cut.
- **Negatives before positives**, in the abstract, the TL;DR, and every table.
- **No result may be softened after the fact.** The r=25% death, the full-real null, and the
  mechanism-mismatch are stated as plainly as the win.
- **Aesthetic**: CVPR-ish project page is fine (clean typography, figure-first, monospace numbers). But
  the page must never *claim* to be a paper.
