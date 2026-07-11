# RESULTS.md — the measured-evidence ledger

> Every entry: **real held-out + scope + normalization + three-axis (where a model is involved) +
> reproducible manifest (script · config · seed)**. A number missing any of these is not a result and
> does not belong in this file. Synthetic-test accuracy is never a result (EVAL_PROTOCOL §6, SCALING §6).
>
> `[CONJECTURE]` / `[ESTIMATE]` are allowed **only** when labelled as such. Negative results stay.

---

## Stage 0 — Environment, data, harness

### 0.1 Environment (measured 2026-07-10)

| item | value |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop, 8 GB VRAM, driver 561.09, CUDA 12.6 |
| Python | 3.13.5 (venv `.venv`, created by `uv` 0.10.6) |
| OS | Windows 11 Home 10.0.26200 |
| Backbone (locked) | pbcquoc VietOCR `vgg_transformer` (CLAUDE.md §11 A1, EVAL_PROTOCOL §6) |

### 0.1 Data provenance — VinText (obtained 2026-07-10, real, not fabricated)

| field | value |
|---|---|
| Source | `VinAIResearch/dict-guided` README → "Original" variant |
| URL | Google Drive id `1UUQhNvzgpZy7zXBFQp0Qox-BBjunZ0ml` |
| Archive | `data/raw/vintext_original.zip`, 1,047,550,389 bytes |
| Format | `x1,y1,x2,y2,x3,y3,x4,y4,TRANSCRIPT` per line, UTF-8 |
| Contents | 2,000 images + 2,000 label files + 2 dictionary files |
| Licence | research/educational use only; redistribution prohibited (see dict-guided README) |

**Split integrity (verified, not assumed):** ids are contiguous and the three splits are pairwise
disjoint; every one of the 2,000 images has exactly one label file.

> ⚠ **Split-name trap (EVAL_PROTOCOL §13 E5).** The folder `test_image` is the **300-image validation**
> split. The **500-image test** split is `unseen_test_images`. All headline numbers use the latter.

| protocol role | VinText folder | image ids | images |
|---|---|---|---|
| train | `train_images` | im0001–im1200 | 1,200 |
| validation | `test_image` | im1201–im1500 | 300 |
| **test (headline)** | `unseen_test_images` | im1501–im2000 | 500 |

### 0.4 Instance counts — `[VERIFY→FREEZE @ Stage 0]` RESOLVED BY MEASUREMENT

Scripts: `scripts/audit_vintext.py` (raw audit) · `scripts/freeze_counts.py` (re-derives the frozen
numbers from the single shared parser `scripts/vintext.py`). No model, no detector involved — rec-only is
scored on GT boxes. Frozen into EVAL_PROTOCOL §13 E1/E2/E6/E8. Char counts are over **edge-whitespace-
stripped, NFC-normalized** transcripts (E6).

| split | total instances | `###` (do-not-care) | empty transcript | **READABLE (rec-only scorable)** | GT chars (NFC) | GT words |
|---|---|---|---|---|---|---|
| train-1200 | 35,094 | 9,300 | 18 | **25,776** | 94,347 | 26,155 |
| val-300 | 8,737 | 1,517 | 19 | **7,201** | 26,839 | 7,211 |
| **test-500** | 12,253 | 2,167 | 18 | **10,068** | **37,254** | 10,136 |
| ALL | **56,084** | 12,984 | 55 | 43,045 | 158,440 | 43,502 |

**Findings:**

1. **Total = 56,084 confirms** the figure EVAL_PROTOCOL §4 cites. The dataset is what the doc says it is.
2. **The curve's rec-only test denominator is 10,068 instances / 37,254 characters** — the doc's `~14k`
   was an explicit `[ESTIMATE]` (500 × ~28) and is now **replaced**. It was ~22% high against total
   annotated regions and ~39% high against scorable ones. Char-level denominator (37,254) is comfortably
   in the "tens of thousands" range EVAL_PROTOCOL §4 requires for per-point error bars smaller than
   inter-point gaps.
3. **The real train recognition set is 25,776 word-crops**, replacing the doc's `~33k` `[ESTIMATE]`. The
   §4 "non-starved real-only baseline" claim survives at 25.8k, but every manifest must cite 25,776.
4. **55 instances ship with an empty transcript** — an annotation defect not documented upstream. Found
   by audit; excluded from rec-only scoring alongside `###` (EVAL_PROTOCOL §13 E2).
5. **756 label lines contain a transcript with an embedded comma** (10 fields, not 9). Parsing must
   rejoin `parts[8:]`. A naive `parts[8]` truncates 756 GT strings and inflates measured CER
   (EVAL_PROTOCOL §13 E4).
6. **The shipped labels are already NFC** — 25,214 NFC, 17,831 ASCII-only, **0 NFD, 0 mixed, 0 combining
   codepoints**. NFC normalization is still applied to both sides at scoring time: it exists to protect
   against a *decomposed model prediction*, which this audit says nothing about (EVAL_PROTOCOL §13 E3).
7. Charset of readable transcripts: **228 distinct codepoints**, 134 non-ASCII (the full Vietnamese
   precomposed inventory, upper and lower case, plus `°`).
8. **27 instances carry leading/trailing spaces** (`'Điện '`, `' phần'`). Transcripts are `.strip()`ed
   before scoring; **the transcript is stripped, never the raw line** — `line.strip()` removes a trailing
   transcript space but leaves a leading one, an asymmetry that made two of this project's own scripts
   disagree by 7 characters on the test denominator before it was caught (EVAL_PROTOCOL §13 E6).
9. **Vocab coverage: test-500 has ZERO out-of-vocabulary characters** against the locked 229-char
   pbcquoc vocab → **no irreducible CER floor** on any headline number (§13 E7). Train has 2 (`°`).
10. **19 test instances have degenerate quads** (2–3 px sides: `'000'` in 6×3 px, `'-'` in 4×2). They are
    **scored as empty predictions, never dropped** — excluding them would make the crop function's
    `min_side` a knob on the test set (4→8 would delete 250 hard instances and improve CER for free).
    The denominator stays pinned at 10,068 / 37,254 (§13 E8).

### 0.3 Eval harness — self-tests PASS (44/44)

`scripts/scorer.py` · self-tests `scripts/test_scorer.py` · **all 44 pass.**
CER/WER/exact-match on NFC; three axes (base / modifier / tone) on NFD; Levenshtein alignment;
per-axis confusion matrices.

**Two Unicode hazards found by measurement, before any model number was trusted:**

1. **`đ`/`Đ` (U+0111/U+0110) have no NFD decomposition.** EVAL_PROTOCOL §3.1 lists `stroke` among the
   modifiers, so it must be injected by hand — otherwise **Axis 2 would never once observe a stroke.**
2. **Combining marks arrive in canonical order, not modifier-then-tone.** `ệ` → `e` + dot-below + circumflex
   (tone first); `ế` → `e` + circumflex + acute (modifier first). Marks are classified **by codepoint**,
   never by position. Reading `nfd[1]` as "the modifier" would label `ệ`'s modifier as a tone.

**The harness demonstrates G2 on demand:** on tone-stripped text (`tiếng Việt có dấu` → `tiêng Viêt co dâu`)
it reports **CER 23.53% while tone-axis accuracy is 42.86%** — overall CER understates the tone damage by
more than 2×. That is the whole reason the three axes exist.

### 0.2 Contamination probe — `[VERIFY→FREEZE @ Stage 0]` RESOLVED (as *not provable*)

> **Headline: no evidence of VinText contamination in the pbcquoc checkpoint. Set-level disjointness is
> NOT provable from published artifacts.** Wording in every downstream doc must be "no contamination
> detected by a zero-shot train-vs-test probe," **never** "verified disjoint." Full reasoning:
> EVAL_PROTOCOL §13 E9. **Flagged for brain adjudication.**

**Provenance.** script `scripts/probe_contamination.py` · config `configs/vgg_transformer_pinned.yml` ·
checkpoint `vgg_transformer.pth` sha256 `380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59`
(151,815,373 B, `Last-Modified: 2022-12-03`) · **zero fine-tuning** · seed 0 · **full splits, no sampling** ·
scope **rec-only (GT boxes)** · NFC (axes NFD) · torch 2.13.0+cu126 / RTX 4060 Laptop.

| split | n | GT chars | CER | WER | exact | Axis1 base | Axis2 modifier | Axis3 tone |
|---|---|---|---|---|---|---|---|---|
| train-1200 | 25,776 | 94,347 | **25.80%** | 43.18% | 57.84% | 83.70% | 86.92% | 83.97% |
| **test-500** | 10,068 | 37,254 | **21.33%** | 40.35% | 60.83% | 86.41% | 88.49% | 85.88% |

- **Gap (test − train) = −4.47 pp.** The held-out split is *easier* than train. Train memorisation would
  drive train CER far below test; that signature is **absent**.
- Zero-shot CER 21–26% vs the checkpoint's reported **0.88 in-domain full-sequence precision** — a large
  document→scene domain gap, consistent with never having seen scene text.
- The full 10M pretraining manifest is unpublished, so a set intersection is **impossible**; the checkpoint
  also **postdates** VinText by ~19 months, so dates cannot exonerate it. This probe can only *fail to
  falsify* disjointness, which is what it did.

> `[LEAD, not a result]` Zero-shot axis ordering is tone (85.88%) < base (86.41%) < modifier (88.49%).
> Suggestive for CLAUDE.md §5's "diacritics dominate" `[CONJECTURE]`, but this is the **un-fine-tuned**
> checkpoint. Stage 1's error analysis runs on the **real-only fine-tuned baseline** and is what decides it.

### Label-noise sighting (motivates the gold set with a real case, not a hypothetical)

`im1501` (first image of test-500), polygon `(389,614,478,613,477,643,394,641)` is annotated `VỰ`.
The polygon demonstrably encloses **`VỰC`** (visually verified against the source image; the crop is
correct). A model that reads it *correctly* is charged a CER insertion. This is EVAL_PROTOCOL §5's premise
made concrete on the very first test image: **raw CER = model error + label error**, and the gold set is
what disentangles them.

### 0.6 Gold reference set — `[VERIFY→FREEZE @ Stage 0]` RESOLVED: **2,437 instances**

`scripts/gold_sample.py` seed 1234 · Gold ⊂ test-500 · disjoint strata, thresholds from the data
(25th pct): small = height < 18 px, low-contrast = Michelson < 0.3593.

| stratum | population | frac | **sampled** | π_incl |
|---|---|---|---|---|
| diacritic_dense (≥1 stacked char) | 2,342 | 0.50 | **1,171** | 0.5000 |
| small (h < 18 px) | 2,086 | 0.30 | **626** | 0.3001 |
| low_contrast | 1,258 | 0.30 | **377** | 0.2997 |
| plain | 4,382 | 0.06 | **263** | 0.0600 |
| **TOTAL** | 10,068 | | **2,437** | |

Captures **50.0% of all stacked-diacritic characters in test-500** (1,171 / 2,342).

**Two methodological points recorded (EVAL_PROTOCOL §13 E10):**

1. **Inclusion probabilities are stored per instance.** Stratified over-sampling means gold is *not* a
   uniform sample of test-500, so the raw disagreement rate estimates the **hard strata's** noise floor,
   not the test set's. The Horvitz–Thompson reweighted rate (`1/π_incl`) estimates the whole test-500's.
   Reporting the raw stratified rate as "the test set's noise floor" would overstate it ~5–8×.
2. **No VinText instance carries two stacked-diacritic characters** — the distribution is exactly
   `{0: 7,726, 1: 2,342}`. Vietnamese orthographic words are monosyllabic and VinText boxes are per-word.
   23.3% of test instances carry the hardest glyph class.

> ⚠ **The gold labels do not exist yet, and none were fabricated.** The script writes 2,437 crops and a
> `transcription_sheet.tsv` with `gold_pass1` / `gold_pass2` **empty**. The codepoint-by-codepoint
> double-pass is the user's manual work (§5). Until it is done, **no noise-floor number exists** and none
> is claimed. (Row idx 2 of the sheet is the `VỰ` / `VỰC` instance found above — the human pass will
> catch it independently.)

---

## Stage-0 `[VERIFY]` ledger — ALL RESOLVED

| id | owning doc | what it is | status |
|---|---|---|---|
| test-500 rec-only instance count | EVAL_PROTOCOL §4 | ✅ **FROZEN: 10,068 inst / 37,254 chars** | done (§13 E1/E6/E8) |
| pbcquoc pretrain ⟂ VinText test | EVAL_PROTOCOL §6 | ✅ **RESOLVED as *not provable*; no contamination detected** | done (§13 E9) — 🧠 **brain to adjudicate** |
| Gate-A noise floor (k=3 seed std) | EVAL_PROTOCOL §7 | ✅ **FROZEN: CER std 0.148 pp · tone std 0.113 pp** | done (§13 E11) |
| gold set exact instance count | EVAL_PROTOCOL §5 | ✅ **FROZEN: 2,437 instances** (labels pending, manual) | done (§13 E10) |

---

## Stage 0 model results

### 0.5 REAL-ONLY BASELINE — k=3 seeds (this is the number every curve point is measured against)

**Provenance.** `scripts/train_baseline.py` (seeds 0,1,2) → `scripts/aggregate_baseline.py` ·
config `configs/vgg_transformer_pinned.yml` · pretrain sha256 `380512193a8b…5ea59` ·
operating point = **document-pretrained pbcquoc `vgg_transformer` → fine-tuned on full VinText-real train**
(EVAL_PROTOCOL §6) · train 25,742 crops (lmdb exposed 25,741, §13 E12) · model-selected on **val-300 crops
only** · 12,000 iters, OneCycleLR max_lr 3e-4, AdamW, batch 32 (HP pre-registered *before* training) ·
**scope rec-only (GT boxes)** · **NFC** (axes NFD) · test-500 real held-out at the frozen denominator
**10,068 instances / 37,254 chars** (asserted per seed) · ~27 min/seed on the RTX 4060.

| metric | seed 0 | seed 1 | seed 2 | **median** | **std** | mean | 95% CI ± |
|---|---|---|---|---|---|---|---|
| **CER** ↓ | 9.395 | 9.226 | 9.521 | **9.395** | **0.148** | 9.381 | 0.368 |
| WER ↓ | 18.962 | 19.307 | 19.603 | 19.307 | 0.321 | 19.291 | 0.797 |
| exact-match ↑ | 82.132 | 81.943 | 81.536 | 81.943 | 0.305 | 81.870 | 0.757 |
| **Axis 1 base** ↑ | 94.081 | 94.285 | 93.975 | **94.081** | 0.158 | 94.114 | 0.391 |
| **Axis 2 modifier** ↑ | 96.207 | 96.378 | 96.171 | **96.207** | 0.110 | 96.252 | 0.274 |
| **Axis 3 tone** ↑ | 94.291 | 94.517 | 94.423 | **94.423** | 0.113 | 94.410 | 0.281 |

Reported as **median + spread over k=3**, never best-of-N (EVAL_PROTOCOL §3).

#### `[VERIFY→FREEZE @ Stage 0]` RESOLVED — the Gate-A noise floor (§13 E11)

- **run-to-run std of rec-only CER = 0.148 pp**
- **run-to-run std of Axis-3 tone accuracy = 0.113 pp**

The Gate-A rule (non-overlapping 95% CI on **both** CER and tone) was pre-registered in §7 before this
value existed. Its consequence, stated now so it cannot be softened later: a synthetic-augmented model
must improve CER by roughly **≥0.7 pp absolute** — and move the tone axis — to clear Gate A.

#### Fine-tuning effect vs the zero-shot checkpoint (same scope, same test set, same denominator)

| | CER | exact | Axis 1 base | Axis 2 modifier | Axis 3 tone |
|---|---|---|---|---|---|
| zero-shot (no fine-tune) | 21.33% | 60.83% | 86.41% | 88.49% | 85.88% |
| **real-only baseline (median, k=3)** | **9.395%** | 81.94% | 94.08% | 96.21% | 94.42% |

Fine-tuning on VinText-real more than halves CER. This is the *vehicle* (CLAUDE.md §0 L3), not a result
about the data engine.

> `[LEAD — not a finding, Stage 1 adjudicates]` At the real-only baseline the axis ordering is
> **Axis 1 base (94.08%) ≲ Axis 3 tone (94.42%) < Axis 2 modifier (96.21%)**. The base-letter axis is the
> *weakest*, marginally below tone — so CLAUDE.md §5's `[CONJECTURE]` that "the dominant error class is
> diacritics, not base characters" is **not obviously supported** by these axis accuracies alone. Axis
> accuracy is not the same as share-of-CER: the Stage-1 CER decomposition (ERROR_ANALYSIS §3), not this
> table, is the kill-test. Flagged for the brain; the engine's design forks on it.

**Artifacts for Stage 1:** `runs/baseline_seed{0,1,2}/predictions.tsv` (10,068 GT↔pred pairs each),
`runs/baseline_k3_summary.json`, `runs/baseline_seed{N}/best.pth`.

**Provenance correction (metadata only, no measured quantity changed):** `train_crops`/`val_crops` were
hardcoded `25744/7200` in the run-time manifest, stale by 2 after the OOV filter. Corrected post-hoc from
the annotation files to `25742/7200`; the script now counts them instead of hardcoding.

---

## Stage 1 — ERROR_ANALYSIS Run 0 (real-only baseline)

**Provenance.** `scripts/error_analysis.py` + `scripts/stratify.py` · inputs
`runs/baseline_seed{0,1,2}/predictions.tsv` · scope **rec-only (GT boxes)** · NFC (axes NFD) ·
test-500 real held-out, 10,068 instances / 37,254 chars · k=3 median · **public labels only**
(gold cross-check BLOCKED) · base axis **case-insensitive** (brain adjudication).
Full report: `ERROR_ANALYSIS.md` -> "RUN 0 REPORT".

### The kill-test (ERROR_ANALYSIS §3.2) — CLAUDE.md §5's conjecture is **REFUTED**

CLAUDE.md §5 `[CONJECTURE]`: *"The dominant error class is diacritics, not base characters or detection."*

| share of ALL character edits | value |
|---|---|
| **base-only substitutions** (case-insens; mod+tone correct) | **39.48%** |
| **diacritic-only substitutions** (tone or modifier wrong, base correct) | **16.12%** |
| pure-tone substitutions | 10.40% |
| pure-case substitutions | 8.88% |
| pure-modifier substitutions | 3.37% |
| mixed (>1 axis) | 10.91% |
| deletions / insertions | 15.51% / 11.51% |

**Base outweighs diacritics ~2.5×.** Any-base-involved 47.75% vs any-diacritic-involved 24.50%.

This *vindicates* the three-axis metric rather than undermining it. Tone is still the **least accurate**
axis (5.577% error vs base's 4.881%) exactly as G2 predicts — but base positions outnumber tone-bearing
positions 2.5:1 (32,267 vs 12,875), so base contributes far more total error. **Only the three-axis
decomposition can show both facts at once.** A single "diacritic accuracy" number would have shown neither.

### Three further refutations of pre-registered expectations

1. **hỏi ↔ ngã is essentially absent** (`hoi→nga` = 4, `nga→hoi` = 4). ERROR_ANALYSIS §3.3 called it
   "the canonical Vietnamese tone confusion." Tone failure is **presence/absence**: 215 drops + 174
   hallucinations vs 199 tone-to-tone confusions. The model does not *see* the mark; it does not
   *mistake* one mark for another. → resolution/blur, **not** similar-tone over-sampling.
2. **Horn (`ơ ư`) is the *most* accurate modifier class** (2.87% error), not the signature drop §3.3 and
   DATA_ENGINE §5 predicted. Worst modifier is **breve (`ă`, 11.16%)**, ~4× horn (widest error bar: only
   242 positions).
3. **Tone does not fall off a cliff at small sizes relative to other axes — base falls hardest.**
   ≥24 px plateau → <12 px: base −11.4 pp, tone −10.0 pp, modifier −8.8 pp. Small text is a *general*
   legibility failure. Refutes DATA_ENGINE §3's assumption.

### Worst strata (k=3 median, rec-only)

| stratum | n | CER | base(ci) | modifier | tone |
|---|---|---|---|---|---|
| **tilt ≥20°** | 490 | **30.34%** | 78.40% | 87.93% | 86.23% |
| **contrast <0.20** | 468 | **27.55%** | 82.28% | 86.47% | 83.55% |
| **1-char instances** | 560 | **25.89%** | 80.54% | 93.15% | 94.57% |
| **height <12 px** | 953 | **22.86%** | 85.08% | 88.33% | 85.88% |
| (overall) | 10,068 | 9.395% | 95.12% | 96.21% | 94.42% |

Geometry is the single most damaging stratum. In every one of them **base is the worst-hit axis** —
except 1-char, where tone is untouched at 94.57% (isolated glyphs destroy letter identity, not tones).

### Provisional priority list (ERROR_ANALYSIS §7)

1. Base-letter error dominates → **geometric + photometric degradation** (not font coverage)
2. Angled text ≥20° → **geometric degradation**
3. Low contrast → **photometric degradation**
4. Small crops → **downsample→upsample + blur**
5. Tone drop/hallucinate → **resolution + blur**
6. Modifier (breve worst) → **font coverage**, low priority (only 3.37% of edits)
7. 1-char instances → **generation length distribution**

> **The engine's priority is degradation realism — geometric first — NOT the font-coverage /
> stacked-diacritic curriculum CLAUDE.md §5 and DATA_ENGINE §5 anticipated.** Font coverage stays a
> *correctness prerequisite* for generation (a font that cannot render `ệ` poisons training) but is not
> where the measured error lives.

### ⚠ The list is PROVISIONAL — two `[LOCKED]` sections are open

- **§4 gold cross-check BLOCKED.** Gold labels do not exist (user's manual double-pass). All Run-0
  numbers are against **public labels** = model error + label error, entangled. Label noise inflates
  *base* errors and *insertions* specifically (verified case: `im1501` public `VỰ` vs image `VỰC`), so
  **39.48% is an upper bound** on the model's true base share. The kill-test must be re-run against gold
  before it is treated as settled.
- **§5 det-vs-rec DEFERRED.** DBNet not set up; `e2e CER − rec-only CER` unmeasured, e2e ceiling
  unstated. §7 requires it: if detection is the bottleneck, the engine's e2e effect is capped.
- **§6 stylized-vs-plain BLOCKED, not dropped.** VinText ships no style annotation; no defensible proxy
  exists without one.

### Stage 1 §5 — det-vs-rec: DBNet setup + why the attribution is NOT yet measurable

`scripts/detect_eval.py` · doctr `db_resnet50` **pretrained on English/Latin, NOT fine-tuned on VinText**
· polygon-vs-quad IoU via shapely (never axis-aligned-box-vs-quad: §6 measured tilt as the most damaging
stratum, so that bias would be large) · `###` regions treated as **don't care**, neither TP nor FP
(EVAL_PROTOCOL §13 E2) · first 20 test images (probe, not a result).

**det-only F1 @ IoU 0.5, vs detector input size:**

| input size | P | R | **F1@0.5** |
|---|---|---|---|
| 1024 | 42.27% | 51.74% | 46.52% |
| 1280 | 46.85% | 49.21% | **48.00%** |
| 1600 | 48.10% | 47.95% | **48.03%** |
| 2048 | 39.77% | 43.53% | 41.57% |

> `[NEGATIVE RESULT — recorded, not buried]` **Input resolution is not the cause.** F1@0.5 plateaus at
> ~48% across 1024→1600 and *degrades* at 2048. The obvious confound (VinText text is tiny — 953 test
> crops are <12 px — so downsampling 1600×1200 to 1024² could have destroyed recall) is **ruled out by
> measurement**. The ~48% F1 is a genuine **domain gap** of an English-trained detector on Vietnamese
> scene text.

> ### ⚠ Why no e2e / attribution number is reported here
> ERROR_ANALYSIS §7 uses the detection bottleneck to decide whether synthetic budget goes to recognition
> **at all**. Computing `e2e CER − rec-only CER` with a detector at 48% F1 that is **not the system's
> detector** would manufacture a large, false "detection is the bottleneck" finding and redirect the
> entire engine. An un-fine-tuned detector is a **lower bound on detection quality**, so the e2e gap it
> produces is an **upper bound on detection-induced error** — useless for the decision §7 needs.
>
> **§5 therefore stays OPEN.** It closes only after DBNet is fine-tuned on the VinText **train** split
> (never val/test) and re-evaluated. Until then the e2e ceiling is **unstated**, and the §7 priority list
> is **provisional**.

---

## Stage 2 — Synthetic engine v0 + Gate A @ 10k

### Engine v0 (DATA_ENGINE §4–§6; measured §12 priorities) — built 2026-07-11
- **Fonts (§5):** 30 Google-Fonts (SIL OFL, vietnamese subset) candidates → 3-check coverage gate
  (glyph-exists / distinctness round-trip / visual audit). 27/30 PASS checks 1–2; all 27 pass visual
  audit; **18 selected** for type diversity → `data/synth/fonts/fonts_manifest.json`.
- **Corpus (§4):** Source B = VinText **train** transcripts verbatim (p=0.65, firewall=train only);
  Source A = wiki_vi (HF `20231101.vi` rev b04c8d1) syllable freq bank (41,386 uniq / 2.0M tok),
  case-augmented. Length/case targets **measured** from train (99% single-token, char median 3,
  case 68/16/22, 10% digit, 6.6% 1-char) — supersedes §4's "1–4 token" guess.
- **Generator (§6, §12 order):** render PASS font → composite on real train-scene bg patch (text-free,
  train-only) → degradation GEOMETRIC → PHOTOMETRIC → RESOLUTION/BLUR. ~4.5 ms/crop (200k ≈ 15 min).
- **§7 distribution audit (before any training): PASS** — synthetic reaches real's hard tail on all 6
  stats (sharpness/contrast/lum_mean/lum_std/height/bg_edge), centers within ~1 IQR, **none
  systematically cleaner than real**. (Verdict encodes §7's asymmetric stated intent — the danger is
  "synthetic cleaner than real"; benign under-reach of the *easy* extreme is not a fail. Raw percentiles
  in `data/crops/synth10k/manifest.json` for audit.)

### Gate A — `[NEGATIVE RESULT — RED, recorded not buried]` (2026-07-11)
Operating point (EVAL_PROTOCOL §6): document-pretrained pbcquoc `vgg_transformer` → fine-tuned on full
VinText-real train (25,742 crops) **+ 10,000 synthetic** = 35,742. **Firewall 3: SAME pre-registered HP,
iters=12,000 FIXED** (= baseline's training compute; only synthetic count varies). k=3 seeds {0,1,2}.
Eval rec-only, test-500, NFC/axes-NFD, frozen denominator **10,068 / 37,254**.
Scripts: `scripts/train_gateA.py` + `scripts/aggregate_gateA.py`. Manifest: `data/crops/synth10k/manifest.json`.

| metric | baseline mean ± 95%CI | **gateA mean ± 95%CI** | Δ (gate−base) | CIs |
|---|---|---|---|---|
| **CER** | 9.381 ± 0.368 | **9.521 ± 0.895** | **+0.140** (worse) | OVERLAP |
| WER | 19.291 ± 0.797 | 19.353 ± 1.000 | +0.062 | OVERLAP |
| exact-match | 81.870 ± 0.757 | 81.850 ± 0.838 | −0.020 | OVERLAP |
| Axis1 base | 94.114 ± 0.391 | 94.041 ± 0.656 | −0.072 | OVERLAP |
| Axis2 modifier | 96.252 ± 0.274 | 96.252 ± 0.600 | +0.000 | OVERLAP |
| **Axis3 tone** | 94.410 ± 0.281 | **94.374 ± 0.553** | **−0.036** (flat) | OVERLAP |

Per-seed CER — gateA: 9.373 / 9.932 / 9.258 (median **9.373**); baseline: 9.395 / 9.226 / 9.521
(median **9.395**). Two of three synth seeds are marginally *better* than baseline median; seed1 (9.932)
inflates the mean + variance.

- **Pre-registered GATE-A condition (EVAL_PROTOCOL §7): NOT met.** Non-overlapping 95% CI on **both** CER
  and tone is required; **neither** separates (both OVERLAP), and neither improves. → **RED.**
- **Added instability:** the synth-augmented CER 95%CI (±0.895) is **~2.4× the baseline's** (±0.368) —
  adding 10k synthetic *raised* run-to-run variance rather than lowering error.
- **The §7 audit passed but Gate A is flat** — matching marginal crop image-statistics did **not**
  translate into a real-data recognition gain. This is the key diagnostic the brain adjudicates (§8):
  coverage of image statistics is necessary-but-not-sufficient; candidates include (a) at fixed compute,
  10k synth dilutes real data without adding signal the document prior lacks; (b) degradation realism
  matches *statistics* but not the *mechanism* real capture destroys; (c) the domain-transfer thesis
  needs scale/curriculum not reachable at 10k.

> **BRAIN CHECKPOINT — reported, NOT self-adjudicated.** Per BUILD_PLAN Stage 2 + EVAL_PROTOCOL §7, a RED
> means **STOP, do not scale to 200k**; the design brain reads the red diagnosis and picks the ONE §8 fix
> (degradation-first) before a re-gate at 10k. No engine change or re-gate was made unilaterally.

### Gate-A RED — bug-checks (DATA_ENGINE §8.2, do NOT burn a re-gate attempt) — 2026-07-11
Brain adjudicated the RED (2026-07-11) as correctly called; ordered the §8.2 bug-checks before any fix.

| check | method | result |
|---|---|---|
| **(a) undertraining / dilution** | end-slope of val full-seq acc over iters 8k–12k, both arms, k=3 (`train.log`) | baseline slopes +0.0058/+0.0010/+0.0013, gateA +0.0079/+0.0009/−0.0006 per-1k-iters. **Both plateaued and COMPARABLE** — gateA is not climbing steeper than baseline, so dilution-undertraining is weakly supported at best. |
| **(b) legibility** | eyeball 50 random `synth10k` crops vs labels (seed 42) → `data/synth/_bugcheck_50.png` | **~13/50 (~26%) illegibly over-degraded.** Labels are CORRECT (not misaligned); the degradation stack destroyed all recoverable text signal (e.g. `3000`, `TIỆM`, `GIÁP`, `NAM` are pure blur). **Training noise.** |
| **(c) label integrity** | assert every `synth10k` label NFC ∧ charset ⊆ model vocab | **PASS** — 0 non-NFC, 0 OOV over 10,000 labels. |
| **(d) was synth learned?** | score each gateA model on held-out synthetic (seed 777, n=2000, disjoint from train) — `scripts/bugcheck_synthtest.py` | synth-test CER **16.0–17.0%** (vs 9.4% on real), exact-match **72–74%** (vs 82% real). Model did **NOT** cleanly learn synthetic — the illegible fraction is unlearnable noise. |

**Bug-check verdict:** the RED is substantially confounded by **over-degradation → ~26% illegible crops =
training noise** (a §8.2 hygiene defect), which also explains the **2.4× seed-variance inflation** (§8.2 predicted
exactly this). The §7 audit passed because it measures aggregate image-statistics, not per-crop legibility.
Per §8.2, fixing legibility is **hygiene, not a re-gate attempt.** Next: cap over-degradation so crops are
**hard-but-legible** (preserve §7 hard-tail coverage), re-audit §7, re-gate at 10k. Judgment flagged for brain:
treating legibility as §8.2 hygiene (not the §8.3 Attempt-1 strata-targeting, which stays available).

### Gate-A HYGIENE RE-GATE (`synth10k_leg`, legibility-fixed) — still RED, but HEALTHY — 2026-07-11
Fix applied (§8.2 hygiene, does **not** burn a re-gate attempt): per-crop **severity budget** in
`engine/render.py` — one latent `sev` scales photometric+sensor degradations coherently (mild-OR-hard, never
independently-maxed on every axis); glare/motion gated to high sev; low-contrast floored at 0.42; defocus
height-capped. **Eyeball illegible ~26% → ~6%**; **§7 audit re-PASS** (still reaches real's hard tail on all
6 stats, none systematically cleaner). Set regenerated as `synth10k_leg` (the RED `synth10k` is preserved).
Everything else identical: same HP, **iters=12,000 FIXED**, k=3 seeds, rec-only test-500, frozen denominator.
Scripts: `scripts/train_gateA.py --synth synth10k_leg` · `aggregate_gateA.py --dataset gateA_synth10k_leg`.

| metric | baseline mean ± 95%CI | **RED run** (over-degraded) | **leg run** (legibility-fixed) | Δ leg−base | CIs |
|---|---|---|---|---|---|
| **CER** | 9.381 ± 0.368 | 9.521 ± 0.895 | **9.419 ± 0.237** | **+0.038** (flat) | OVERLAP |
| WER | 19.291 ± 0.797 | 19.353 ± 1.000 | 19.166 ± 0.079 | −0.125 ✓ | OVERLAP |
| exact-match | 81.870 ± 0.757 | 81.850 ± 0.838 | 82.125 ± 0.284 | +0.255 ✓ | OVERLAP |
| Axis1 base | 94.114 ± 0.391 | 94.041 ± 0.656 | 94.175 ± 0.278 | +0.061 ✓ | OVERLAP |
| Axis2 modifier | 96.252 ± 0.274 | 96.252 ± 0.600 | 96.387 ± 0.280 | +0.135 ✓ | OVERLAP |
| **Axis3 tone** | 94.410 ± 0.281 | 94.374 ± 0.553 | **94.568 ± 0.463** | **+0.158** ✓ | OVERLAP |

Per-seed CER — leg: **9.320 / 9.427 / 9.510** (range 0.19); RED: 9.373 / 9.932 / 9.258 (range 0.67);
baseline: 9.395 / 9.226 / 9.521 (range 0.30).

- **Pre-registered GATE-A condition (EVAL_PROTOCOL §7): STILL NOT MET → RED.** CER Δ is +0.038 (flat, vs the
  ~≥0.7 pp the frozen floor requires); tone improved (+0.158) but its CI overlaps baseline's.
- **The hygiene fix worked, exactly as bug-check (b) predicted:** seed **variance collapsed** — CER 95%CI
  **±0.895 → ±0.237**, now *below* the baseline's own ±0.368. The illegible-crop noise was the variance driver.
- **Every axis flipped from negative/flat to positive** (tone, modifier, base, exact, WER all improve). The
  synthetic now *trends* helpful — but the magnitude is a rounding error against the pre-registered bar.
- **This is the §8.3 mechanism showing up empirically:** clean, legible, **marginal-matched** synthetic
  reproduces real's *rate* of hard crops, so 10k adds only a few hundred hard examples on top of the ~1,300
  the 25.7k real crops already contain. Covering the marginals is **necessary but not sufficient** — which is
  precisely what §8.3's pre-declared Attempt 1 (over-represent the *failure strata*) exists to fix.

> **BRAIN CHECKPOINT — reported, NOT self-adjudicated.** A Gate-A number was produced, so I STOP here.
> Attempt 1 (§8.3) would spend **1 of only 2** pre-registered re-gate attempts (§8.1) — a budget the brain
> locked specifically to prevent p-hacking by iteration — so it is **not** started unilaterally, even though
> it is pre-declared. Awaiting brain direction.

### STEP 0 (DATA_ENGINE §8.4 + §8.2d) — the AUGMENTATION CONFOUND, verified — 2026-07-11

**(i) `[VERIFY→RESOLVED BY MEASUREMENT]` What `image_aug=True` actually applies.** §8.4 locked "VERIFY
FIRST, do not assume." Measured from the **installed** vietocr (`vietocr/loader/aug.py::ImgAugTransformV2`,
albumentations **2.0.8**), dumped via `Compose.to_dict()`:

| transform | p | strength (exact) |
|---|---|---|
| `InvertImg` | 0.2 | colour inversion |
| `ColorJitter` | 0.2 | brightness/contrast/saturation (0.8, 1.2); hue (−0.5, 0.5) |
| `MotionBlur` | 0.2 | **blur_limit (3, 3)** — fixed 3-px kernel |
| `RandomBrightnessContrast` | 0.2 | brightness_limit **(−0.2, 0.2)**; contrast_limit **(−0.2, 0.2)** |
| `Perspective` | 0.5 | **scale (0.01, 0.05)** — tiny corner jitter |
| `RandomDottedLine` (vietocr) | 0.5 | 1 random dotted/dashed/solid line drawn over the crop |

**ABSENT: rotation, shear, Gaussian/defocus blur, noise, JPEG compression, downsample/resolution.**

> **`[FINDING — partially REFUTES §8.4's stated premise]`** §8.4 asserted the default augmentation "already
> applies blur, motion blur, noise, JPEG compression, perspective and affine/shear," making the §6
> degradation model "largely redundant." **It does not.** Noise, JPEG, shear/rotation and Gaussian blur are
> absent; blur and perspective exist only in very mild form. So the **redundancy** mechanism is *not* what
> flattened Gate A.
>
> **But §8.4's DESIGN gets stronger, not weaker** (and §8.4 explicitly branched on this verification, so no
> `[LOCKED]` decision is invalidated): the baseline is **under-augmented on exactly the measured failure
> strata** — tilt ≥20° (30.3% CER) is untouched by a 0.01–0.05 perspective; contrast <0.20 (27.6%) is barely
> moved by ±0.2; height <12 px (22.9%) is never manufactured. **Arm B therefore has large headroom**, and
> §15's raised comparator is essential: a "+X% from synthetic" claim measured against *this* baseline would
> be a strawman.

**(ii) §8.2(d) on the leg models — the transfer verdict.** Held-out synthetic (seed 777, n=2000, disjoint
from the 10k train set), `scripts/bugcheck_synthtest.py`:

| model | synth-test CER | exact-match | tone | real-test CER |
|---|---|---|---|---|
| **A — baseline** (never saw synthetic) | **26.4%** (26.65/26.79/25.82) | 58.4% | 80.6% | 9.381 |
| **leg** (trained on 10k synthetic) | **16.0%** (15.74/16.08/16.19) | 74.2% | 88.6% | 9.419 |

> **`[THE FINDING]` The model LEARNED the synthetic distribution decisively** — synth-test CER **26.4 → 16.0**
> (−39% relative), exact-match +15.8 pp, tone +8.0 pp — **while real-test CER did not move at all**
> (9.381 → 9.419). Per §8.2(4) this is the clean verdict: **the data and pipeline are fine; the synthetic
> simply DOES NOT TRANSFER to real VinText.** Not a bug — the real result. (Synthetic-test accuracy is a
> sanity check only, never a result — SCALING §6.)
>
> This is precisely what §8.4's mechanism predicts: **a REAL crop degraded to be hard is strictly more
> informative than a RENDERED crop degraded to be hard.** It motivates the three-arm test directly.

### ATTEMPT 1 (1 of max 2, §8.1) — the THREE-ARM experiment (§8.4) — **RED** — 2026-07-11

k=3 seeds per arm · rec-only · VinText test-500 · NFC (axes NFD) · frozen denominator 10,068 / 37,254 ·
**iters=12,000 FIXED** (= baseline compute) · `scripts/train_arm.py`, `scripts/aggregate_arms.py`.
**B and C use the IDENTICAL augmentor** (`engine/strata_aug.py`), so `C − B` isolates the synthetic.

- **A** = real + **default** aug (Stage-0 baseline).
- **B** = real + **strata-targeted** aug, **NO synthetic** (CONTROL — not a re-gate attempt).
- **C** = real + the same strata aug + **10k strata-targeted synthetic** (`synth10k_strata`, §8.3).

| metric | A (baseline) | B (strata aug) | C (aug + synth) | **B − A** | **C − B** |
|---|---|---|---|---|---|
| **CER** | 9.381 ± 0.368 | 9.637 ± 0.074 | 9.620 ± 0.191 | **+0.256** | **−0.017** |
| WER | 19.291 ± 0.797 | 19.626 ± 0.392 | 19.462 ± 0.551 | +0.335 | −0.164 |
| exact-match | 81.870 ± 0.757 | 81.751 ± 0.333 | 81.777 ± 0.307 | −0.119 | +0.026 |
| Axis1 base | 94.114 ± 0.391 | 94.189 ± 0.220 | 94.195 ± 0.174 | +0.075 | +0.006 |
| Axis2 modifier | 96.252 ± 0.274 | 96.366 ± 0.259 | 96.354 ± 0.182 | +0.114 | −0.012 |
| **Axis3 tone** | 94.410 ± 0.281 | 94.542 ± 0.142 | 94.493 ± 0.117 | **+0.132** | **−0.049** |

Per-seed CER — B: 9.631/9.610/9.669 · C: 9.626/9.693/9.540.

**Finding 1 — `B − A`: "just augment harder" is NOT a free win.** Strata-targeted augmentation of *real*
crops improves **all three per-position axes** (base +0.075, modifier +0.114, **tone +0.132**) but
**worsens CER (+0.256), WER (+0.335) and exact-match (−0.119)**. Mechanism: the axes score *aligned*
positions, while CER/WER also charge insertions/deletions — heavy augmentation buys **per-character
robustness at the cost of length errors** (dropped/hallucinated characters). Consequently **B is NOT
uniformly stronger than A**, which breaks an assumption in §15; the strictest honest comparator is
therefore the **better of {A, B} per metric** (C must beat **A's CER** *and* **B's tone**).

**Finding 2 — `C − B`: at MATCHED augmentation the synthetic contributes NOTHING.** Every metric moves by
**|Δ| < 0.17 pp** with **all CIs overlapping**: CER **−0.017**, tone **−0.049**, base +0.006, modifier
−0.012. This is the **§8.4 "C ≈ B"** outcome — *aggressive augmentation of real data captures everything
this synthetic engine provides.* It is the honest answer to the question practitioners actually face and
almost nobody tests: **"is synthetic data worth generating, or should you just augment harder?"** Here, for
a document-pretrained recognizer with 25.7k real crops: **generating it was not worth it.**

- **Pre-registered GATE-A condition (§7, unchanged): NOT met on either CER or tone → RED.**
  (C vs A on CER: +0.239, no gain, CIs overlap. C vs B on tone: −0.049, no gain, CIs overlap.)
- **Attempt 1 of max 2 is now SPENT (§8.1).** Bug-checks and the control arm B did not consume attempts.
- Consistent with §8.2(d): the model **learns** the synthetic (synth-test CER 26.4 → 16.0) but it **does
  not transfer** — and now we know it adds nothing even when the failure strata are over-represented AND
  the comparator is augmentation-matched.

> **BRAIN CHECKPOINT — reported, NOT self-adjudicated.** Per §8.1, one attempt remains. If Attempt 2 is
> also RED, the finding is *"10k synthetic gives no lift at full real data"* (reported at full prominence)
> and the project moves to the **pre-registered** real-data-budget axis (EVAL_PROTOCOL §14) —
> a contingency reserved before Stage 0, not a post-hoc rescue.

### INS/DEL/SUB decomposition — the B−A tradeoff MECHANISM, verified — 2026-07-11
`scripts/insdel_decomp.py` (reuses the single `scorer.align`) over the existing `predictions.tsv` of all
three arms, k=3. **Why it matters:** the three axes are scored on *matched* positions — a **substitution or
deletion charges the axes**, but an **insertion has no reference position and charges CER/WER only**. So the
odd "axes UP while CER UP" pattern in arm B *must* be insertion-driven, or the tradeoff story is wrong.

| arm | sub /100ch | del /100ch | ins /100ch | CER% |
|---|---|---|---|---|
| A (baseline) | 6.806 ± 0.326 | 1.461 ± 0.239 | 1.114 ± 0.116 | 9.381 |
| B (strata aug) | 6.926 ± 0.177 | **1.362 ± 0.020** | **1.348 ± 0.112** | 9.637 |
| C (aug + synth) | 6.848 ± 0.064 | 1.365 ± 0.114 | 1.407 ± 0.130 | 9.620 |

**`B − A`: sub +0.121 · del −0.099 · ins +0.234 · CER +0.256** → the CER regression is **92% insertions**.

> **`[MECHANISM CONFIRMED, and sharpened]`** Deletions *improved* (−0.099) and insertions *worsened*
> (+0.234). Because a **deletion charges every applicable axis** (a dropped character is all-axes-wrong)
> while an **insertion charges none**, this is precisely why the axes rise while CER falls: strata
> augmentation makes the recognizer **less willing to DROP a character** (axes up: base +0.075, modifier
> +0.114, tone +0.132) but **more willing to HALLUCINATE one** (CER +0.256, WER +0.335). The write-up claim
> is therefore stated as **insertions**, not the vaguer "length errors": *aggressive augmentation buys
> per-character robustness and pays for it in hallucinated characters.*

**`C − B`** (synthetic's effect on the error mix at matched augmentation): sub −0.079 · del +0.004 ·
ins +0.058 · **CER −0.017** — i.e. nothing, consistent with the C≈B null above.
