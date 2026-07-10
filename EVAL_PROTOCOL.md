# EVAL_PROTOCOL.md — the measurement ruler (frozen before any modeling)

> **What this file is.** The pre-registered evaluation protocol for the Vietnamese scene-text OCR
> project — a **sibling of CLAUDE.md**, same character: no over-claim, validate-before-you-claim,
> pre-register the threshold *before* the stage that tests it. CLAUDE.md governs *scope*; this file
> governs *how every number is defined and gated*. It exists so that no metric, threshold, or gate is
> silently chosen after the number is seen (the p-hack the whole project is built to prevent), and so
> Claude Code cannot fill an unresolved definition with a reasonable-looking default that quietly voids
> the moat.
>
> **The one rule that generates all the others.** A number is not a result until it is (i) on **real
> VinText held-out**, (ii) at a **stated pipeline scope**, (iii) under **stated Unicode normalization**,
> (iv) with **diacritics reported on three separate axes**, (v) reproducible from script+config+manifest+seed.
> Miss any one → not a result.
>
> **Pre-registration discipline.** Values marked `[LOCKED]` are decided now and do not reopen without a
> dated amendment (§12). Values marked `[VERIFY→FREEZE @ Stage N]` cannot be set from the armchair
> because they require a Stage-0/Stage-N measurement — but the **procedure that sets them is locked now**,
> and the value is frozen *before* the stage that tests it. That is still pre-registration: you commit to
> *how* the bar is derived before you can see whether you clear it.

---

## §1. Scope every number (the most common OCR benchmark cheat)

Three scopes exist; a number without one is void, and comparing across scopes is forbidden.

- **det-only** — DBNet detection. IoU-based Precision / Recall / F1 at a **stated IoU threshold**
  `[LOCKED: report at IoU 0.5; also curve F1 over IoU 0.5→0.9 for the detection section]`.
- **rec-only** — VietOCR recognition **given ground-truth boxes** (GT-box crops fed to the recognizer).
  No detection error propagates in. This isolates the recognizer.
- **end-to-end (e2e)** — detection feeds recognition; det errors propagate into rec.

**`[LOCKED]` Headline scope for the scaling curve = rec-only.** The synthetic engine acts on the
recognizer (it generates word/line crops); the curve must measure where the intervention acts, on the
test-500 rec-only instances (§4). **e2e is reported alongside** every headline curve point so real-world impact is
visible, but the curve's *shape claim* is a rec-only claim. Rationale: if a detection bottleneck (surfaced
in Stage-1 error analysis) flattens the e2e number, an e2e headline would hide a real recognition gain —
the exact confounding this protocol forbids.

**`[LOCKED]` Baseline-scope matching.** Any external baseline (Apple Vision, Tesseract, ML Kit) is a
whole-system e2e recognizer. It is compared **e2e-to-e2e** by default; a rec-only comparison is obtained
by feeding it the **same GT-box crops** the recognizer sees. Never quote our rec-only against their e2e.

---

## §2. Unicode handling (a correctness prerequisite, almost always missed)

Vietnamese characters have precomposed and decomposed forms (NFC vs NFD). Two normalizations are used,
for two different jobs, and both are stated in every result:

- **`[LOCKED]` CER / WER / exact-match are computed on NFC-normalized strings** — both prediction and
  ground truth normalized to NFC identically before scoring. An encoding mismatch otherwise inflates or
  deflates accuracy in a way that looks like a model result.
- **`[LOCKED]` The three diacritic axes (§3.1) are computed on NFD-decomposed aligned characters** —
  NFD splits a glyph into base letter + combining marks, which is exactly the decomposition the three
  axes need. NFD is used **only inside the diacritic-axis scorer**, not for CER/WER.

Any string entering scoring is first stripped of zero-width/format codepoints and NFC/NFD-normalized as
above. State "NFC" (or "NFD, diacritic-axis scorer") in every reported table.

---

## §3. The metric suite (report the relevant one, name it, never cherry-pick)

Reported for every model/stage, all of them, no quiet selection of the flattering one:

- **CER** (character error rate, NFC) — headline scalar for overall recognition quality.
- **WER** (word error rate, NFC) — reported; scene text is short, so WER is high-variance, treat as context.
- **Exact-match / sequence accuracy** (NFC) — reported; the strictest, most variance-prone number.
- **The three diacritic axes (§3.1)** — the credibility core; **co-headline with CER**.
- **Detection: P/R/F1 @ stated IoU** (§1).

**`[LOCKED]` Variance reporting.** Every number that has run-to-run variance is reported as **median +
spread over k=3 seeds**, not best-of-N. Curve points, Gate-A deltas, and INT8 before/after all carry the
spread. Best-of-N is a silent lie.

### §3.1 The three-axis diacritic decomposition — THE keystone (G2 made precise)

A single "diacritic accuracy" number **re-creates the exact hiding problem G2 warns about, one level
down**: Vietnamese carries two orthogonal systems on one glyph, and collapsing them hides which one fails.
So diacritics are scored on **three separate axes**, never one number.

After NFD decomposition, each syllable-nucleus glyph splits into a **base letter**, an optional
**letter-forming modifier**, and an optional **tone mark**. Example: `ệ` (U+1EC7) → `e` + combining
circumflex (U+0302) + combining dot-below (U+0323); `ữ` → `u` + horn (U+031B) + tilde (U+0303).

- **Axis 1 — Base-letter accuracy.** Correct base letter, ignoring modifier and tone. (Did it read `e`
  vs `o` vs `a`?)
- **Axis 2 — Modifier accuracy** over the letter-forming marks **{breve U+0306 (ă), circumflex U+0302
  (â ê ô), horn U+031B (ơ ư), stroke (đ)}**, scored on positions whose base admits a modifier. (Did it
  read `ê` vs `e`, `ư` vs `u`, `đ` vs `d`?)
- **Axis 3 — Tone accuracy** over **{none/ngang, sắc U+0301, huyền U+0300, hỏi U+0309, ngã U+0303,
  nặng U+0323}**, scored on tone-bearing positions. (Did it read the tone `ẻ` vs `ẽ` vs `ẹ`?)

**`[LOCKED]` Alignment.** Prediction and GT are aligned by minimum-edit path (Levenshtein). Axis scores
are computed on **matched-position pairs**; a deletion/insertion counts as all applicable axes wrong at
that position. Axis accuracy = correct-on-axis ÷ axis-bearing positions.

**`[LOCKED]` The confusion matrices are deliverables, not diagnostics-only.** Report a **per-axis
confusion matrix**, with special attention to:
- **Tone: hỏi (̉) ↔ ngã (~)** — the canonical Vietnamese tone confusion (regionally merged); and
  **sắc/huyền/nặng** blurring under low-res/motion-blur.
- **Modifier: `ơ/ư` horn drop** and **`â/ê/ô` circumflex drop** — the marks fonts most often mangle (§ DATA_ENGINE),
  so this axis also audits font-coverage failures leaking into training.

This breakdown is the single most credible artifact the project produces, and it is what tells the
synthetic engine *what to generate* (tones dying → resolution/blur; modifiers dying → font coverage).

---

## §4. Splits and the instance-count rule

**`[LOCKED]` VinText standard split, unchanged:** 1,200 train / 300 validation / 500 test images
(56,084 text instances total, ~28 instances/image). Recognition sees **~33k real word-crops** from the
train split — a non-starved real-only baseline, which is what makes "+X% from synthetic" a fair claim
rather than beating a weakened model.

**`[LOCKED]` The scaling curve is measured in instances, never images.** Each curve point is CER over
the **rec-only instances of the test-500** — the GT-labeled text instances, **counted exactly from the
VinText test annotation at Stage 0** (rec-only is scored on GT boxes, so **no detection run is needed to
count them**; **~14k is an estimate**, 500 × ~28, to be replaced by the measured count). Not over 500
image-level numbers. Char-level counts in the tens of thousands are what keep each point's error bar
smaller than the gap between points; an image-count curve has error bars that swamp the signal.

**`[LOCKED]` Gold ⊂ test-500** (§5), so the noise floor calibrated on gold transfers to the curve's test set.

---

## §5. The Gold reference set (the closest thing to an oracle — defined in instances, stratified)

Public VinText labels contain annotation noise, so raw CER = model error + label error, entangled. A
frozen hand-verified gold set breaks the entanglement.

**`[LOCKED]` Defined in INSTANCES, not images.** Target **~2,000–3,000 word-instances**
`[VERIFY→FREEZE @ Stage 0: exact count after inspecting the test-500 instance distribution]`. Defining
gold as "200–300 images" implies ~8,400 instances × 2 passes ≈ 60–70 h of the hardest possible manual
work; the instance definition delivers the same two roles at ~¼ the labor.

**`[LOCKED]` Stratified, not uniform.** Over-sample the crops that actually fail: diacritic-dense
(stacked ế/ệ/ữ/ự), small/low-resolution, low-contrast, and unusual fonts. Uniform sampling burns the
verification budget on easy clean words that never fail.

**`[LOCKED]` Double-pass.** Transcribe codepoint-by-codepoint, NFC-normalize, then **re-review after a
day**. Report every position where gold disagrees with the public label — that disagreement is itself a
finding (it quantifies the public test set's noise floor).

**`[LOCKED]` Two roles, never conflated:** (a) gold = noise-floor calibration + deploy decision;
(b) full test-500 = the curve's test set. Gold is **too small to carry the curve** (per-point variance).

> **Honest limit (state it, never hide it):** gold is *human*-verified, not "absolute." The transcriber
> makes diacritic errors too; the double-pass reduces, not eliminates them. It is a **high-confidence
> gold reference** — the claim is calibration + rigor, never infallibility. Do not write "oracle" or
> "absolute" on the CV or in any doc.

---

## §6. The scaling curve's operating point (locked, and stated in the headline sentence)

The curve varies **only** synthetic count; everything else is fixed (Firewall 3). The fixed operating
point is now pinned, because fine-tuning from a pretrained checkpoint changes what the curve measures:

**`[LOCKED]` Operating point = document-pretrained pbcquoc VietOCR → fine-tuned on the full VinText-real
train split → synthetic added on top at 10k / 50k / 200k.** Fixed across all points: the backbone (locked
just below), hyperparameters, the real-data amount (full train split), augmentation, and this evaluation
protocol.

**`[LOCKED]` Backbone = pbcquoc `vgg_transformer`** — VGG CNN encoder + **Transformer decoder**. This is
an *explicit* lock, **not** something CLAUDE.md L1 pinned (L1 named only "VietOCR"). pbcquoc ships two
configs — `vgg_transformer` (Transformer decoder) and `vgg_seq2seq` (RNN-attention decoder) — and they
carry **different INT8 stories** (§8), so exactly one name must appear in every file. `vgg_transformer` is
chosen: the stronger, more widely-reproduced config with a public checkpoint. **Terminology guard:** a
Transformer decoder is still **autoregressive at inference** (batch=1, one token per step over a growing
KV-cache), so the GPT-2 batch=1 INT8 lesson still applies — its mechanism differs from the `vgg_seq2seq`
RNN (growing self/cross-attention vs a fixed-size hidden state), which is exactly *why* the config is
pinned rather than left as the ambiguous word "seq2seq" (pbcquoc calls **both** configs "seq2seq" in the
general encoder-decoder sense, so that word alone does not identify a backbone).

**`[LOCKED]` The honest headline sentence** is therefore:
> "+X% CER on real VinText held-out (rec-only) from the synthetic scene-text engine, **on top of a
> document-pretrained VietOCR fine-tuned on VinText-real**" —
attribution is **domain-transfer value** (document→scene), *not* "from scratch." The pretrained prior
already reads clean Vietnamese; the synthetic engine's job is scene realism, and the sentence must say so.

**`[VERIFY→FREEZE @ Stage 0]`** Confirm from the pbcquoc repo that the pretraining corpus (10M images,
document/handwritten/synthetic domain) is **disjoint from the VinText scene-text test set**, and state
the disjointness in RESULTS.md. If any overlap exists, the held-out is contaminated at the checkpoint
level and Firewall 1 is void until a clean held-out is used.

*(Optional, compute permitting — not headline: a second curve from a cold/generic start, to show the
domain-transfer value is larger when the prior is weaker. Report only if the 4060 budget allows; the
single fine-tune curve is the deliverable.)*

---

## §7. Gate A — does synthetic close the real gap AT ALL (pre-registered, not a post-hoc judgment)

Gate A is the heart: it stops the project from quietly failing by scaling an untested assumption to 200k.
A gate without a pre-registered threshold is a vibe, so the threshold is fixed by procedure now.

- **Protocol.** Generate ~10k synthetic, fine-tune on top of the §6 operating point, test on the full
  test-500 (rec-only). Compare CER against the **real-only** operating point (pretrained + full-real, no
  synthetic).
- **`[LOCKED]` Noise floor.** Measure the real-only baseline's **run-to-run std over k=3 seeds** at
  Stage 0 and **freeze it** `[VERIFY→FREEZE @ Stage 0]`. This is the yardstick Gate A is judged against.
- **`[LOCKED]` GREEN** = the synth-augmented CER improvement is **significant against seed noise** — the
  improvement's confidence interval over the k=3 seeds does **not overlap** the real-only baseline's (a
  real effect, not run-to-run variance) — **on both CER and the tone axis** (a lift that leaves tones
  unchanged is not the lift this project claims). This is a **seed-noise** test (run-to-run std, above),
  **not** the **label-noise** floor (gold-vs-public disagreement, §5) — different quantities, never
  conflated. The decision *rule* (non-overlapping CIs) is fixed **now**; only the floor *value* is measured
  at Stage 0. Deriving the rule *from* the measured floor would be post-hoc rule-tuning — the exact p-hack
  §12 forbids. (With k=3 seeds the non-overlapping-CI bar is deliberately conservative; a paired
  significance test at a pre-registered level is the equivalent formal statement.)
- **`[LOCKED]` RED** = improvement within noise → **STOP. Do not scale to 200k.** Diagnose the synth-real
  gap on the ranked axes (§ DATA_ENGINE: degradation realism first, then font/background/corpus
  distribution — *not* "add more data"), fix the engine, **re-run Gate A at 10k.** Red-at-10k is cheap;
  red-discovered-at-200k is two wasted weeks.

**Gate A does double duty as the compute-feasibility probe:** time the full 10k loop (generate → train →
eval); 200k ≈ ~20× that. This tells you *before committing* whether the curve's top point is reachable on
the 4060 (8 GB) or aspirational.

---

## §8. INT8 gates — quality AND speed (the sibling project proved speed is not free)

The GPT-2 sibling measured INT8 buying **1.00×** at batch=1 on a small model (compute-bound on discarded
work / launch-bound, not bandwidth-bound). VietOCR's `vgg_transformer` decoder (autoregressive at
inference, §6) is the same batch=1 regime, so INT8 speedup is a **conjecture**, not a given, and both a quality gate and a speed gate
are pre-registered.

- **`[LOCKED]` Quality gate.** After INT8: **CER +≤0.5 absolute** and **tone-axis accuracy −≤1.0%** vs
  fp16, on real test-500 (rec-only). Exceed → keep the sensitive layer(s) in fp16 (the sibling's
  tied-head fix generalizes: the output projection into the softmax is the first suspect), or per-channel
  quant. The bound is frozen before Stage 3 and **not re-tuned after seeing the result**.
- **`[LOCKED]` Speed gate + dispatch instrumentation.** Report the measured INT8 speedup against a
  **pre-registered floor** derived the sibling's way (quantizable-weight fraction × achievable
  low-precision throughput) `[VERIFY→FREEZE @ Stage 3]`. If INT8 buys **less than the floor, that is a
  measured finding, not a failure** — and it must be explained via **Core ML compute-unit dispatch**
  (ANE / GPU / CPU, from the Xcode Core ML performance report). INT8 on the A14 ANE can be a real
  speedup; INT8 on GPU/CPU at batch=1 replays the sibling's zero-speedup result. The claim is conditional
  on where Core ML actually dispatches the encoder (VGG CNN) vs the AR decoder (dynamic-length, the op
  class that tends to fall off the ANE).

---

## §9. On-device benchmark protocol (fair or it is worthless)

Device `[LOCKED]`: iPhone 12 Pro Max, A14 Bionic, iOS 26.5.2. Export path: ONNX Runtime (iOS) or Core ML.

- **`[LOCKED]` Matched scope.** Same images, same phone. Apple Vision / Tesseract / ML Kit run e2e — match
  that for the e2e comparison; feed **GT-box crops** for the rec-only comparison (§1).
- **`[LOCKED]` Thermal discipline.** The A14 throttles under sustained load (passive cooling). **Rest
  1–2 min between batches**, report **ambient temperature**, warm up before timing, and report **median +
  spread** across runs — never mean, never a single long uninterrupted loop (the last images run ~2× the
  first).
- **`[LOCKED]` Apple Vision firewalls.** Use **`.accurate`** recognitionLevel. **Pin iOS 26.5.2 +
  VNRecognizeTextRequest revision** in every result (a closed, moving baseline — not reproducible across
  OS updates). It is a **black box**: report **WHERE** it fails (diacritic-axis confusion on its own
  outputs), not WHY. Compare **per-axis** — a Vietnamese-specific model most plausibly wins on the
  tone/modifier axes even while losing on detection robustness or latency; that per-axis result is the
  honest, interesting finding, not an overall "we beat Apple."
- **`[LOCKED]` Success is pre-registered as per-axis**, not "beat overall." Apple Vision is mature and
  ANE-optimized; losing overall is a likely and honest outcome, and an honest "within X% overall, ahead
  on tones, on-device" is a strong result.

---

## §10. Contamination firewalls (no exceptions)

- **`[LOCKED]`** Synthetic **text corpus draws ONLY from the train-split labels + Wikipedia (`wiki_vi`)**,
  **never** val/test labels. Drawing short-text from test labels = putting test answers into training =
  silent contamination that inflates exactly the curve this protocol is trying to keep honest.
- **`[LOCKED]`** No synthetic **image** overlaps the test set; the test set is real VinText only.
- **`[LOCKED]`** pbcquoc pretraining verified disjoint from the VinText test set (§6 `[VERIFY]`), or a
  clean held-out is substituted.
- **`[LOCKED]`** Fonts are license-clean (Google Fonts, SIL OFL 1.1); no ambiguous-license aggregator fonts.

---

## §11. Reproducibility manifest (if you cannot reproduce it, you do not have it)

Every result carries: **script + config + data manifest + seed.** The data manifest names *which* real
split, *which* synthetic split and count, *which* fonts (with the per-font stacked-diacritic coverage
verdict — see DATA_ENGINE), and *which* corpus mixture. On-device results add: **phone model + iOS
version + VNRecognizeTextRequest revision + thermal conditions.** Numbers go back to the design brain
(chat) for the protocol/plausibility check before they are believed; training and benchmarking run in
Claude Code / the box + phone.

---

## §12. Amendment rule

Every `[LOCKED]` value holds until a **dated, written amendment appended to this file**, stating what
changed and why. Thresholds are **never** re-tuned *after* seeing the number they gate — that is the
p-hack this protocol exists to prevent. A `[VERIFY→FREEZE @ Stage N]` value, once measured and frozen at
its stage, becomes `[LOCKED]` and follows the same rule.

---

## §13. AMENDMENTS (dated; supersede any conflicting text above)

**[2026-07-10] E1 — §4 instance counts MEASURED and FROZEN (resolves `[VERIFY→FREEZE @ Stage 0]`).**
Source: the shipped VinText `labels/gt_*.txt` (original `x1,y1,…,x4,y4,TRANSCRIPT` format), audited by
`scripts/audit_vintext.py` @ commit of this change. No detector was run (rec-only is scored on GT boxes).

Char counts are over **edge-whitespace-stripped, NFC-normalized** transcripts (E6), re-derived from the
single shared parser by `scripts/freeze_counts.py`. If that script and this table ever disagree, this
table is wrong.

| split | folder | images | total instances | `###` | empty | **READABLE (rec-only scorable)** | GT chars (NFC) |
|---|---|---|---|---|---|---|---|
| train | `train_images` (im0001–1200) | 1200 | 35,094 | 9,300 | 18 | **25,776** | 94,347 |
| val   | `test_image` (im1201–1500)   | 300  | 8,737  | 1,517 | 19 | **7,201**  | 26,839 |
| test  | `unseen_test_images` (im1501–2000) | 500 | 12,253 | 2,167 | 18 | **10,068** | 37,254 |
| ALL   | | 2000 | **56,084** | 12,984 | 55 | 43,045 | 158,440 |

- The 56,084 total **confirms** the figure cited in §4. The splits are contiguous, disjoint, and every
  image has exactly one label file (verified).
- **FROZEN: the scaling curve's rec-only test denominator = 10,068 instances / 37,254 NFC GT characters.**
  This **replaces the "~14k" estimate** in §4, which was ~22% high against total instances and ~39% high
  against scorable ones.
- **FROZEN: the real train recognition set = 25,776 word-crops.** This **replaces the "~33k real
  word-crops" estimate** in §4. The "non-starved real-only baseline" claim in §4 still holds at 25.8k,
  but the doc's number was an over-estimate and the corrected one is what every manifest must cite.

**[2026-07-10] E2 — `###` and empty transcripts EXCLUDED from rec-only scoring (definitional freeze).**
§4 says the curve is scored over "the GT-labeled text instances." VinText marks illegible/do-not-care
regions with the transcript `###` (12,984 instances) and ships **55 instances with an empty transcript**
(a genuine annotation defect, found by audit, not documented upstream). Neither carries a reference
string, so neither can contribute to a CER numerator or denominator.

- **`[LOCKED]` rec-only scoring excludes `###` and empty-transcript instances.** This is the ICDAR/scene-text
  convention and the only coherent one for recognition: there is no reference to score against.
- **`[LOCKED]` For e2e and det-only, `###` regions are `don't care`**: a detection overlapping a `###`
  region is scored as **neither true-positive nor false-positive** (it is removed from the match set
  before P/R/F1). This is the standard VinText/ICDAR treatment and must not silently become an FP —
  doing so would understate detection precision and, through it, the e2e number the curve reports
  alongside its headline.
- Every reported instance count states which convention it uses. `10,068` (scorable) and `12,253`
  (all annotated regions) are **different numbers for different scopes** and are never interchanged.

**[2026-07-10] E3 — Shipped VinText labels are already NFC; normalization is still applied explicitly.**
Audit: of the 43,045 readable transcripts, 25,214 are NFC-and-not-NFD, 17,831 are ASCII-only
(NFC==NFD), and **zero** are NFD or mixed. **No combining codepoints appear anywhere in the label set.**
This is a convenient starting state, **not** a licence to skip §2: the *model's* output is what NFC
normalization actually protects against (a decomposed prediction scored against a precomposed reference
would inflate CER), and any future corpus/synthetic text may arrive NFD. §2 stands unchanged.

**[2026-07-10] E4 — Annotation parsing hazard (recorded so it is never reintroduced).** 756 of the 56,084
label lines contain **10** comma-separated fields, not 9, because **the transcript itself contains a
comma**. The transcript is therefore `",".join(parts[8:])`, never `parts[8]`. All 56,084 lines were
verified to have exactly 8 integer-parseable leading coordinate fields, so the 4-point-quad assumption
holds and the rejoin is unambiguous. A naive `parts[8]` silently truncates 756 GT strings and would
inflate measured CER.

**[2026-07-10] E5 — Split-name trap.** VinText's folder named `test_image` is the **300-image validation**
split; the **500-image test** split is the folder named `unseen_test_images`. §4's "1,200 / 300 / 500"
maps to `train_images` / `test_image` / `unseen_test_images` respectively. Evaluating on the folder
literally called `test_image` would report a **validation** number as the headline test number.

**[2026-07-10] E6 — Transcript whitespace rule (fixes the CER denominator).** 27 readable instances
(17 train / 1 val / 9 test) carry **leading or trailing ASCII spaces** (`'Điện '`, `' phần'`).
- **`[LOCKED]` Transcripts are `.strip()`ed of edge whitespace before scoring; internal spaces are
  preserved.** A recognizer fed a cropped word box cannot produce a leading space the image does not
  contain; charging it a CER insertion/deletion for an annotation artifact is a measurement error.
- **`[LOCKED]` Strip the transcript, never the raw line.** `line.strip()` before splitting removes a
  *trailing* transcript space but leaves a *leading* one — a silent asymmetry that made two of this
  project's own scripts disagree by 7 characters on the test denominator before it was caught.
- Instance counts are unaffected (no transcript becomes empty under stripping). Character counts drop
  by 25 overall; the frozen test denominator is **37,254**, not 37,263 (the pre-strip value, which
  appeared in E1's first draft and is superseded).

**[2026-07-10] E8 — Degenerate GT quads are scored, never dropped (the denominator must not move
with the crop code).** rec-only rectifies each 4-point GT quad by perspective warp. 19 scorable
test-500 instances have quads 2–3 px on a side — real, labelled, microscopic text (`'000'` in 6×3 px,
`'-'` in 4×2, `':'` in 3×10). (train: 32, val: 1.)

- **`[LOCKED]` A GT-scorable instance is NEVER excluded from rec-only scoring.** An unrectifiable crop
  yields an **empty prediction**, scored as all-deletions.
- **Why this is not a detail:** if degenerate crops were *excluded*, the crop function's `min_side`
  threshold would become a silent knob on the **test set**. Raising it 4→8 would drop **250** of the
  hardest test instances and *improve* CER for free. Pinning the rule keeps the denominator at exactly
  the frozen **10,068 instances / 37,254 chars** regardless of crop implementation.
- Verified: with the rule applied, the harness reproduces 10,068 / 37,254 exactly. The 19 degenerate
  instances are all digits/punctuation, so they add 33 chars to CER but **zero** base/tone axis
  positions (digits bear neither) — the axis denominators are unchanged, as they must be.

**[2026-07-10] E9 — §6 `[VERIFY→FREEZE @ Stage 0]` disjointness: NOT PROVABLE; falsification attempted
and failed. Residual risk stated, not hidden.**

§6 asked to "confirm from the pbcquoc repo that the pretraining corpus is disjoint from the VinText
test set." That confirmation **cannot be obtained**, and saying otherwise would be the exact over-claim
this project forbids. What was actually established:

*Documentary evidence (weak — absence of mention):*
- pbcquoc's README describes the 10M pretraining set only as *"ảnh tự phát sinh, chữ viết tay, các văn
  bản scan thực tế"* (synthetic, handwriting, real scanned documents). **No scene-text source is named.**
- The repo contains **zero** references to VinText / VinAI / dict-guided / scene text (grepped).
- **The full 10M manifest is NOT published** (only a ~1M synthetic sample is released) → a set
  intersection is **impossible**. This is the binding limitation.

*Temporal evidence (fails to exonerate):*
- Checkpoint `vgg_transformer.pth` `Last-Modified: 2022-12-03`; VinText released ~May 2021 (archive
  entries dated 2020-06 → 2021-02). **The checkpoint postdates the dataset by ~19 months**, so
  publication dates cannot rule out ingestion.

*Empirical falsification test (the real evidence) — `scripts/probe_contamination.py`, zero fine-tuning,
rec-only on GT-box crops, FULL splits (no sampling):*

| split | n | CER | exact-match | Axis1 base | Axis2 modifier | Axis3 tone |
|---|---|---|---|---|---|---|
| train (seen-if-contaminated) | 25,776 | **25.80%** | 57.84% | 83.70% | 86.92% | 83.97% |
| test-500 (held out) | 10,068 | **21.33%** | 60.83% | 86.41% | 88.49% | 85.88% |

- **Gap (test − train) = −4.47 pp: the held-out split is *easier* than train.** Memorisation of the
  train images would drive train CER far *below* test. The contamination signature is **absent**.
- Absolute zero-shot performance (CER ~21–26%, exact-match ~58–61%) is far below the checkpoint's
  reported **0.88 in-domain full-sequence precision** — consistent with a genuine document→scene
  **domain gap**, i.e. with never having seen scene text.

**Verdict `[FROZEN]`: no evidence of VinText contamination in the pbcquoc checkpoint; set-level
disjointness is unprovable from published artifacts. Firewall 1 proceeds on a falsification-failed
basis, and every write-up must say so** — "no contamination detected by a train-vs-test zero-shot
probe," never "verified disjoint." If the brain judges this insufficient, the fallback in §6 (substitute
a clean held-out) applies.

**[2026-07-10] E7 — Vocab coverage of the locked backbone measured (no irreducible floor on test).**
The pbcquoc `base.yml` vocab (229 chars) vs VinText's readable GT, per `scripts/check_vocab_coverage.py`:

| split | chars | OOV chars | instances with ≥1 OOV |
|---|---|---|---|
| train | 94,347 | 2 (`°` U+00B0, 0.0021%) | 2 |
| val | 26,839 | **0** | 0 |
| **test** | 37,254 | **0** | **0** |

**The test set has zero out-of-vocabulary characters**, so the locked vocab imposes **no irreducible CER
floor** on any headline number. Recorded because the converse would have been a silent constant added to
every curve point — a floor attributable to the vocab, not the recognizer, and one that synthetic data
could never remove. The 2 training `°` instances are left as-is (0.002% of train chars; changing the
locked vocab to chase them would be a confound, not a fix).
