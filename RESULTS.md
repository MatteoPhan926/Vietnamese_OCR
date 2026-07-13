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

---

## Stage 2c — §14 real-data-budget axis: the LABEL-EFFICIENCY CURVE `[COMPLETE 2026-07-12]`

The pre-registered contingency (EVAL_PROTOCOL §14, frozen §14.1 spec written **before** the first run).
Question: not "does synthetic add on top of ALL my real data?" (answered: **no**, RED) but **"how much real
annotation can synthetic replace?"**

**Protocol (§14.1, unchanged from the frozen spec).** Same document-pretrained pbcquoc `vgg_transformer`
checkpoint; real budget r ∈ {10, 25, 50, 100}% of the train split as **fixed-seed NESTED subsets**
(10 ⊂ 25 ⊂ 50 ⊂ 100, crop-level, subset seed 20260711); arms = **real-only(r)** vs **real(r) + the FROZEN
hygiene-clean synth10k_leg** (same synthetic set at every r — one variable at a time); §6 operating config
(default `image_aug`, fixed HP, iters=12,000, best-val selection on the full val-300); **uniform sampling
over the pooled set** (per §14.1 — the synthetic *fraction* growing as r shrinks IS the phenomenon under
study, not a confound); k=3 seeds {0,1,2}. Eval rec-only, test-500, NFC/axes-NFD, frozen denominator.
r=100% reuses the Stage-0 baseline (real-only) and the hygiene re-gate (leg) run. New compute: 18 runs.
Scripts: `scripts/train_budget.py` + `scripts/aggregate_budget.py`. Curve: `runs/budget_curve_summary.json`.

### The curve (CER ↓, Axis3 tone ↑; mean ± 95% CI over k=3)

| r | n_real | real-only CER | real+synth CER | **ΔCER (gap)** | real-only tone | real+synth tone | **Δtone** | per-point rule (§7) |
|---|---|---|---|---|---|---|---|---|
| **10%** | 2,574 | 16.538 ± 2.350 | **13.181 ± 0.290** | **+3.357** | 89.336 ± 1.704 | **91.987 ± 0.099** | **+2.651** | **GREEN** (both CIs separate) |
| **25%** | 6,436 | 12.373 ± 0.337 | **11.434 ± 0.349** | **+0.939** | 92.432 ± 0.357 | **93.077 ± 0.126** | **+0.645** | **GREEN** (both CIs separate) |
| **50%** | 12,871 | 10.430 ± 0.200 | 10.478 ± 0.807 | −0.047 | 93.869 ± 0.535 | 93.856 ± 0.408 | −0.013 | red (overlap, flat) |
| **100%** | 25,742 | 9.381 ± 0.368 | 9.419 ± 0.237 | −0.038 | 94.410 ± 0.281 | 94.568 ± 0.463 | +0.158 | **red** (overlap, flat) |

**The gap is MONOTONE in r: +3.36 → +0.94 → −0.05 → −0.04.** This is the pre-registered *"gap widens as r
shrinks"* branch of §14 — **synthetic SUBSTITUTES for real labels, and only when real labels are scarce.**

### `[LOCKED]` The pre-registered readout — "synthetic ≈ worth N real crops at budget r"
Invert the real-only curve (linear in log r, **between measured points only, never extrapolated**);
N = (r′ − r) × 25,742:

| r | real+synth CER | matches real-only at r′ | **N (real crops synthetic is worth)** |
|---|---|---|---|
| **10%** | 13.181 | 20.9% | **≈ +2,813 real crops** |
| **25%** | 11.434 | 34.9% | **≈ +2,560 real crops** |
| 50% | 10.478 | 49.2% | ≈ −216 (nil) |
| 100% | 9.419 | 97.5% | ≈ −646 (nil) |

At a scarce budget, **10k synthetic crops buy ~2,600–2,800 real crops' worth of accuracy** — i.e. ~0.27
real crops per synthetic crop — and that purchasing power **decays to zero by r=50%**.

### Secondary observation (reported, not headlined): synthetic STABILIZES the scarce-budget fit
At r=10% the real-only arm's CER 95% CI is **±2.350**; adding synthetic collapses it to **±0.290** (~8×
tighter; same at tone, ±1.704 → ±0.099). With 2,574 crops the real-only fine-tune is seed-unstable;
the synthetic pool regularizes it. Note this is the **opposite** sign of the Gate-A observation at r=100%
(where synth *raised* variance, ±0.368 → ±0.895) — consistent with the same mechanism: the synthetic pool
matters when real data is thin and is dead weight when it is not.

### `[LOCKED]` Scope — what this does and does NOT license
- **Licensed:** *"At a real-label budget of 2,574 crops (10% of VinText train), adding 10k crops from the
  synthetic engine cuts rec-only CER on real VinText held-out from 16.54 to 13.18 (−3.36 pp, non-overlapping
  95% CI over 3 seeds) and tone accuracy from 89.34 to 91.99 (+2.65 pp) — worth ≈2,800 additional real
  annotations. The effect decays monotonically with the real budget and is NIL at full real data."*
- **NEVER claimable:** *"synthetic improves Vietnamese OCR."* **It did not, at full real data** (r=100%:
  ΔCER −0.038, CIs overlap → RED). Per §14 the r=100% null keeps **full prominence** and is stated in the
  same breath as any label-efficiency claim.
- This is a **label-efficiency** result, not a rehabilitation of the count-scaling thesis. The
  synthetic-count axis (10k→200k at full real) was **never run and is not licensed** — Gate A's RED
  correctly stopped it (§7: a RED means do not scale).
- Coherent with DATA_ENGINE §8.2(d) + the §8.4 three-arm null: the model **learns** the synthetic fine, but
  that knowledge is **REDUNDANT** with what 25,742 real crops already teach. It only pays when real is thin.

> **BRAIN CHECKPOINT — the curve is REPORTED here, not adjudicated here.** Per CLAUDE.md §9.8 the numbers go
> back to the design brain for the protocol/plausibility check before any headline is declared.

### §14.2 (C1) — the STRICT-BANK closure: the corpus-budget confound `[2026-07-12]`

**The defect (caught at brain adjudication, locked as EVAL_PROTOCOL §14.2).** `synth10k_leg`'s Source B
(65% of the corpus text) drew from the **full** train transcript bank. But **transcripts ARE labels**: a
practitioner at real-label budget r holds only r% of them, so the +synth arm was using label-derived text
beyond its stated budget. The eval firewall was intact (no test text/images anywhere) — this is a
**claim-scope** defect, not contamination. Per §14.2, **the headline must quote the strict version.**

**The strict arm.** Source B restricted to the **r-subset's OWN transcripts**
(`data/synth/corpus/scene_phrases_r{r}.txt`, built from `annotation_train_r{r}.txt`). Fonts, degradation
config (`DEFAULT_CFG`), seed (100), and count (10,000) **identical** to `synth10k_leg` — the bank is the
only variable. Sets: `data/crops/synth10k_strict_r{10,25}`. Scripts: `engine/generate.py --strict-bank-r`,
`scripts/train_budget.py --arm strict`, `run_c1.sh`. k=3, rec-only, test-500, frozen denominator.

**Pre-training audits (both PASS — so a null could not be blamed on a degraded generator):**
- **§7 distribution audit: PASS** on both strict sets (reach real's hard tail on all 6 stats; not
  systematically cleaner than real).
- **Budget audit.** Beyond-budget transcript text among the 10k synthetic labels: **r=10% 37.0% → 11.0%**;
  **r=25% 21.3% → 6.0%**. The residual is **not leakage**: **0** labels are unexplained by {the r-subset's
  own bank, free `wiki_vi` tokens, generated 1–2-char strings} — coincidental overlap with **free** text,
  which the §14.2 budget model explicitly permits. Verified, not assumed.

| r | arm | CER | ΔCER | tone | Δtone | per-point rule (§7: CER **and** tone) |
|---|---|---|---|---|---|---|
| **10%** | real-only (k=3) | 16.538 ± 2.350 | — | 89.336 ± 1.704 | — | (comparator) |
| | full-bank (§14.1 primary) | 13.181 ± 0.290 | +3.357 | 91.987 ± 0.099 | +2.651 | GREEN |
| | **STRICT (headline)** | **13.728 ± 0.166** | **+2.810** | **91.500 ± 0.363** | **+2.164** | **GREEN** (both separated) |
| **25%** | real-only (k=3) | 12.373 ± 0.337 | — | 92.432 ± 0.357 | — | (comparator) |
| | full-bank (§14.1 primary) | 11.434 ± 0.349 | +0.939 | 93.077 ± 0.126 | +0.645 | GREEN |
| | **STRICT (headline)** | 11.621 ± 0.374 | +0.752 (sep.) | 92.948 ± 0.403 | +0.515 (**overlap**) | **red** |

### `[C1 VERDICT]` The r=10% green SURVIVES; the r=25% green DOES NOT
- **r=10%: GREEN under the strict bank.** Gap +2.810 pp CER (was +3.357), **84% of the full-bank gain
  retained**, both CIs separated. The low-budget value is carried **mostly by the renderer, not by the
  in-domain text bank** — but ~16% of it *was* the bank, and that is now measured rather than assumed.
- **r=25%: RED under the strict bank** — `[NEGATIVE RESULT, reported at full prominence]`. CER still
  separates (+0.752) but **tone does not** (+0.515, CIs overlap), and the pre-registered rule requires
  **both**. The r=25% green in the primary curve **does not survive** the budget-honest bank.
- **`[LOCKED §14.3 — CORRECTS the original wording of this bullet]`** r=25% is **NOT** "carried by the text
  bank." The strict bank costs a roughly **uniform ~16–20% of the gain at BOTH green points** (retention:
  83.6% CER @ r=10%; 80.1% CER / 79.8% tone @ r=25%) — the bank cost at r=25% *matches* r=10%'s. What
  differs is the **remaining effect size vs the two-metric bar.** The correct record: *directionally
  positive under strict (CER separated, +0.752), but below the pre-registered bar (tone overlaps).* The
  original phrasing here — "substantially carried by label-derived text the budget did not entitle it to" —
  **over-read the same numbers and is retracted**, in place, rather than quietly deleted.
- The C1 correction therefore **shrinks the claim to the r=10% point**, and the two-metric green dies
  somewhere in **(10%, 25%]**. The bar was raised after seeing the result (§15 asymmetry permits this); it
  was never lowered.

### `[LOCKED]` The worth-readout, as a RANGE (§14.2 reporting rule — never a 4-digit point)
The +synth arm's 95% CI is propagated through the §14.1 inversion (a lower CER inverts to a higher r′).

| r | arm | CER | worth (mean) | 95% CI range |
|---|---|---|---|---|
| **10%** | full-bank | 13.181 | ≈ +2,813 crops (r′=20.9%) | [+2,480 .. +3,169] |
| **10%** | **STRICT (headline)** | **13.728** | **≈ +2,202 crops (r′=18.6%)** | **[+2,031 .. +2,379]** |
| 25% | full-bank | 11.434 | ≈ +2,560 crops (r′=34.9%) | [+1,508 .. +3,752] |
| 25% | STRICT (**red** — no claim) | 11.621 | ≈ +1,980 crops (r′=32.7%) | [+928 .. +3,181] |

> **Stated limitation:** only the +synth arm's CI is propagated; the real-only curve being inverted is
> taken at its per-point **means** (its own seed spread — notably ±2.350 at r=10% — is not folded in). The
> quoted range is therefore a **lower bound on the true uncertainty**, not a full error budget. **C2 (k=5
> at r=10%, both arms) is running to tighten exactly that anchor.**

> **Stated limitation (§14.2):** one fixed nested subset draw per r → **training-seed variance only**;
> **subset-draw variance is unquantified.** Standard for label-efficiency curves, but said out loud.

> **BRAIN CHECKPOINT — reported, NOT adjudicated.** No headline sentence is written until C2 lands.

### §14.2 (C2) — k=5 at the headline point, BOTH arms `[2026-07-12]`

Pre-committed (§14.2): **the k=5 numbers REPLACE the k=3 numbers regardless of direction.** Adding seeds
after a green is honest only under that pre-commitment — it can *kill* the green; it cannot shop for one.
Seeds {3,4} added to real-only(r=10%) and strict(r=10%). Driver: `run_c2.sh`. Aggregator t-statistic is
now keyed by dof (t(4)=2.776 at k=5; the previously-hardcoded t(2)=4.303 would have inflated the k=5 CI
by ~55%).

| r=10% arm | k=3 (superseded) | **k=5 (REPLACES it)** | per-seed CER |
|---|---|---|---|
| real-only | 16.538 ± 2.350 | **16.509 ± 0.933** | 17.622 / 16.108 / 15.883 / 15.980 / 16.950 |
| **strict (headline)** | 13.728 ± 0.166 | **13.726 ± 0.096** | 13.690 / 13.690 / 13.810 / 13.810 / 13.640 |
| **gap** | +2.810 CER / +2.164 tone | **+2.783 CER / +2.033 tone** | — |
| verdict | GREEN | **GREEN — both CIs separated** | — |

**The green SURVIVES k=5.** The means barely moved (real-only −0.03, strict −0.00); what changed is the
anchor's spread, which **collapsed from ±2.350 to ±0.933** — the k=3 anchor was simply under-sampled, not
biased. The two arms are separated by ~2.8 pp with the nearest CI edges (15.58 vs 13.82) **1.75 pp apart**,
so the separation is not marginal.

### `[LOCKED]` The headline worth-readout, k=5, strict bank, as a RANGE — **§14.3 CORRECTED**
**≈ +2,195 real crops (r′=18.5%), both-arm 95% range [+1,678 .. +2,553].**
(Full-bank, for comparison: ≈ +2,807, range [+2,126 .. +3,286].)

> **`[SUPERSEDED]`** The range first reported here, **[+2,095 .. +2,297]**, propagated only the **+synth**
> arm's CI and held the real-only **anchor fixed at its mean** — which under-propagates, since the anchor
> is exactly the noisy quantity C2 was run to tighten. §14.3 corrects the rule to **min/max over BOTH
> arms' CI corners**, widening the range roughly 3×. The **point estimate is unchanged** (+2,195); only its
> honesty about uncertainty improved. Independently reproduced against the brain's value.

> **Remaining limitations** (stated, not hidden): the curve's *other* interpolation endpoints are still
> held at their means; and **subset-draw variance is unquantified** (one fixed nested draw per r —
> training-seed variance only).

> **BRAIN CHECKPOINT — reported, NOT adjudicated.** C1+C2 are complete; no headline sentence is written
> until the brain rules. Remaining closures: **C3** (gold double-pass — the USER's manual work, now
> genuinely blocking the final numbers) and **C4** (ERROR_ANALYSIS §8 per-axis before/after at r=10% — the
> mechanism half; per SCALING §9 the curve without it is half a result).

---

## C4 — ERROR_ANALYSIS §8 before/after at r=10%: THE MECHANISM `[2026-07-12]`

The mechanism half of the flagship (SCALING §9: a curve without it is half a result). **BEFORE** =
real-only(r=10%), k=5. **AFTER** = real(r=10%) + 10k **strict-bank** synthetic, k=5. Analysis-only (the
`predictions.tsv` of both k=5 arms already existed). Script: `scripts/c4_before_after.py`; artifact:
`runs/c4_before_after_r10.json`. Rec-only, test-500, NFC (CER) / NFD (axes), frozen denominator, base axis
case-insensitive. Δ = unpaired 95% CI on the difference of two k=5 means.

**The question was pre-stated so the answer could not be shopped:** gain concentrated on **tone + small /
low-contrast / tilted** crops → the engine hit the DATA_ENGINE §12 failure strata (**mechanism confirmed**);
gain **uniform** → the synthetic is a **generic prior** at a scarce budget, not targeted domain transfer
(a real gain, but a *different* mechanism, and the write-up must say so).

### The three axes all move, and by similar amounts

| metric | before | after | Δ (95% CI) | clears noise? |
|---|---|---|---|---|
| CER | 16.509 ± 0.933 | 13.726 ± 0.096 | **+2.783 ± 0.938** | YES |
| Axis1 base (ci) | 91.206 ± 0.570 | 92.811 ± 0.090 | **+1.605 ± 0.577** | YES |
| Axis2 modifier | 92.385 ± 0.677 | 94.194 ± 0.024 | **+1.808 ± 0.678** | YES |
| Axis3 tone | 89.463 ± 0.641 | 91.497 ± 0.134 | **+2.033 ± 0.655** | YES |

Tone moves most, but **base and modifier move nearly as much** — this is not a tone-specific repair. Total
character errors: **6,150 → 5,113 (1,037 chars fixed**, mean over 5 seeds).

### `[FINDING — the engine's targeted strata are NOT what carries the gain]`
Share of the 1,037 fixed characters, by stratum (`*` = ΔCER clears its own 95% CI):

| stratum (DATA_ENGINE §12 rank) | bin | ΔCER | share of gain |
|---|---|---|---|
| **geometric (rank 1)** | **tilt ≥20°** | **+1.60 ± 1.94 — does NOT clear noise** | **2.8%** |
| photometric (rank 2) | contrast <0.20 | +4.89 ± 2.97 `*` | 8.4% |
| resolution (rank 3) | height <12px | +5.30 ± 2.47 `*` | 18.3% |
| — | tilt <5° (the easy, common case) | +3.04 ± 0.99 `*` | **77.1%** |
| **length (NOT a targeted knob)** | **9–12 chars** | **+16.79 ± 4.13** `*` | **41.9%** |
| **length** | **≥13 chars** | **+17.66 ± 3.30** `*` | **12.4%** |
| length | 1 char | −1.54 ± 6.51 (worse, within noise) | −0.8% |

- **The #1 measured failure driver — geometric tilt ≥20° — did NOT significantly improve** (+1.60 ± 1.94,
  CI includes zero) and contributes **2.8%** of the gain. The engine's geometric degradation, built because
  Stage 1 ranked tilt the worst stratum, **is not what paid.**
- **54.3% of the entire gain comes from long crops (≥9 chars)** — only 296 of 10,068 instances. Length was
  **never a targeted knob** (the synthetic corpus is 99% single-token, char median 3).
- Gains are otherwise **broad and roughly uniform** across height, contrast and tilt bins — including the
  *easy* bins (77.1% of the gain sits at tilt <5°; 20.4% at height ≥48px).

### `[MECHANISM — measured, not inferred]` The scarce-budget model TRUNCATES; the synthetic fixes it
Long crops (≥9 chars, n=296), predicted vs GT length over k=5:

| arm | mean GT length | mean predicted length | severely truncated (<60% of GT) |
|---|---|---|---|
| real-only (2,574 crops) | 11.19 | **8.37** | **24.7%** |
| + strict synthetic | 11.19 | **10.25** | **6.9%** |

Examples (GT | real-only | +synth): `0583.871197` | `0587.87` | `0583.871197` · `0905.871198` | `09.87` |
`0905.87198` · `0913.889124` | `09.88` | `0913.889124`.

At a 2,574-crop budget the **decoder terminates early** — it emits `<eos>` before finishing long strings
(phone numbers, URLs), losing ~25% of the sequence. Adding 10k synthetic crops of *any* kind supplies the
decoder training signal that fixes premature termination. **A deletion charges every axis** (a dropped
character is all-axes-wrong), which is exactly why **all three axes rise together** rather than tone alone.

> **`[HONEST READING — reported, NOT declared]`** On the pre-stated fork this lands on the **"generic
> prior"** side, not "targeted domain transfer": the gain is broad, is dominated by a **sequence-length /
> premature-termination** effect the engine never targeted, and is **absent on the geometric stratum the
> engine was designed around.** The +2.783 pp is real, survives the strict bank, and survives k=5 — but the
> honest causal story is *"at a scarce label budget, more crops of almost any kind fix decoder
> under-training,"* which **weakens the claim that the engine's realism knobs are what did the work.**
> This is a `[BRAIN CHECKPOINT]`. It is not self-adjudicated, and it is a live threat to the
> domain-transfer framing — including the possibility that a **cheap non-scene control** (e.g. the same 10k
> rendered without the degradation stack) would buy much of the same gain. That control was **not run**;
> whether to run it is the brain's call.

---

## §16 — CONTEXT BASELINES: off-the-shelf Vietnamese OCR on the same test set `[2026-07-13]`

**CONTEXT, NOT A CONTEST.** These systems were **not trained on VinText**; ours was. This table measures
**the task's difficulty** and demonstrates the three-axis scorer on systems that are not mine. It is
**not** a superiority claim and must never be written as one.

**Protocol (EVAL_PROTOCOL §16, pre-registered and committed BEFORE the first run — commit `1f8b6bf`).**
Scope **rec-only** on GT-box crops via `scripts.infer.crops_for` (**the eval's own crop code path**;
degenerate quads become empty predictions, never exclusions) · same **test-500**, frozen denominator
**10,068 instances / 37,254 chars** (asserted at run time) · NFC · scored by **our** three-axis scorer ·
`scripts/context_baselines.py` · single deterministic inference pass per system (**k=1** — no training
seeds involved, so no CI: these are not trained models).

**§16 smoke test (20 easy high-contrast crops) — PASS.** 0/20 empty returns from both systems before the
full run, so the recognition-only API mode is correct and no system is being strawmanned by being fed a
word crop through an end-to-end pipeline.

| system | version / model | CER ↓ | exact ↑ | Axis1 base ↑ | Axis2 modifier ↑ | Axis3 tone ↑ | empty |
|---|---|---|---|---|---|---|---|
| **EasyOCR** | 1.7.2, `vi` (latin_g2 rec) | 38.46 | 37.95 | 68.11 | 74.02 | 72.75 | 51 |
| **PaddleOCR** | 3.7.0, `latin_PP-OCRv5_mobile_rec` | 22.53 | 43.55 | **88.59** | **66.03** | **68.89** | 55 |
| **Tesseract-vie** | — | **[FAILED]** | | | | | |
| pbcquoc `vgg_transformer` **zero-shot** (the free row) | no fine-tune | 21.33 | 60.83 | 86.41 | 88.49 | 85.88 | — |
| **ours** @ r=10% (2,574 real + 10k synth) | k=5 mean | 13.73 | — | — | — | 91.50 | — |
| **ours** @ full real data (25,742 crops) | k=3 mean | **9.38** | 81.87 | 94.11 | 96.25 | 94.41 | — |

### `[FAILURE, reported as a failure — no row is faked]` Tesseract-vie
Not run. The `pytesseract` wrapper installs from pip but the **Tesseract binary does not**: it needs a
system installer, and both `winget install UB-Mannheim.TesseractOCR` and a direct silent install of the
NSIS package failed with **installer exit code 2 (requires elevation)** in this non-interactive shell.
§16 says report install failures as failures. It is reported. An elevated
`winget install UB-Mannheim.TesseractOCR` would close it.

### `[THE FINDING — and it is the scorer's, not the CER's]` PaddleOCR cannot *represent* Vietnamese tones

PaddleOCR ships **no Vietnamese recognizer**; the nearest available is the multilingual **latin** model.
I inspected its output charset instead of reading its errors as if they were accuracy:

> **`latin_PP-OCRv5_mobile_rec` output charset = 772 characters. ALL 90/90 of the Vietnamese precomposed
> block (U+1EA0–U+1EF9: ạ ả ấ ầ ệ ự …) are ABSENT from it.** Those characters **cannot be emitted**. Its
> tone axis is **structurally capped, not merely inaccurate.**

The measured error confirms the charset exactly: PaddleOCR's tone confusions are overwhelmingly
**tone → `ngang`** (the unmarked tone) or outright deletion — `nang→ngang` 853, `huyen→ngang` 696,
`sac→ngang` 616, `nang→<del>` 368. It is not *mistaking* one tone for another; it is *unable to write one*.

**This is exactly the failure a single CER hides, and exactly what the three axes exist to expose.**
Compare PaddleOCR with the zero-shot pbcquoc checkpoint. Their **CERs are nearly the same** (22.53 vs
21.33) — a CER-only leaderboard would call them equivalent. They are not remotely equivalent:

| | base | modifier | tone | what it actually is |
|---|---|---|---|---|
| PaddleOCR (latin) | **88.59** | 66.03 | 68.89 | **reads the letters better, cannot write the marks** |
| pbcquoc zero-shot | 86.41 | **88.49** | **85.88** | reads the marks, weaker on letters (domain gap) |

Two systems, one CER, opposite failure modes. **A single number would have reported them as the same
result.** That is the entire argument for the three-axis metric, made on systems that are not mine.

> **Scope, stated plainly:** ours is the only system here trained on VinText, and the only one measured
> with seeds and CIs. The gap between rows is **not** evidence that our method is better than EasyOCR's or
> PaddleOCR's — it is evidence that **in-domain training data matters**, and that **an off-the-shelf
> multilingual model may not even encode the language you are pointing it at.** The second of those is the
> more useful warning.

---

## §14.4(A) — THE CLEAN-RENDER CONTROL: the engine's own thesis, refuted `[2026-07-13, ADJUDICATED]`

Pre-registered readings (EVAL_PROTOCOL §14.4(A), written **before** the control was generated): clean buys
**≥ ~80%** of the +2.783 → the realism machinery is **not load-bearing**; **< ~50%** → the degradations are
load-bearing and the domain-transfer framing survives; between → report the split.

**Provenance.** `data/crops/synth10k_clean_r10` (`engine/generate.py --no-degrade`): render → real-bg
composite → plain resize. NO geometric, NO photometric, NO blur/JPEG. **Same corpus, fonts, strict bank
(r10), generation seed (100)** as `synth10k_strict_r10` — and the two sets' **label sets are IDENTICAL**
(227 items ≥9 chars, 44 ≥13, max len 18), so **the only difference between them is pixels.** r=10%, k=3,
same HP/iters. `run_control.sh` → `scripts/aggregate_control.py` → `runs/control_clean_summary.json`.
§7 audit on the clean set: **FAIL** (cleaner than real — by design; recorded, non-gating, not a training-set
candidate). Rec-only, test-500, NFC, frozen denominator.

| arm (r=10%) | k | CER ↓ | tone ↑ | gain vs real-only |
|---|---|---|---|---|
| real-only | 5 | 16.509 ± 0.933 | 89.463 ± 0.641 | — |
| **+ STRICT synth (shipped, degradation ON)** | 5 | **13.726 ± 0.096** | **91.497 ± 0.134** | **+2.783 / +2.033** |
| **+ CLEAN synth (degradation OFF)** | 3 | **13.900 ± 0.155** | **91.231 ± 0.242** | **+2.609 / +1.768** |

- **Clean recovers 93.7% of the CER gain and 86.9% of the tone gain.**
- **shipped − clean = 0.174 CER / 0.266 tone — CIs OVERLAP, not separable from zero.**
- Both arms separate from real-only. → **the pre-registered ≥80% branch fires.**

> **`[VERDICT — the pre-registered ≥80% branch]`** The realism machinery is **NOT load-bearing at this
> operating point.** What the engine supplies at a scarce label budget is **sequence-level training signal**
> — (text, length) pairs that teach the decoder not to terminate early — **not domain realism.** This is the
> third of three independent measurements saying the same thing (§8.4 C≈B at full real; C4's 2.8%
> not-significant geometric stratum vs 54.3% from long crops; this ablation). **DATA_ENGINE §1's thesis
> ("the degradation model is THE lever") is REFUTED by this project's own measurements** — recorded as
> DATA_ENGINE §13. The headline (+2.783) is unmoved: this is an attribution ablation, not a re-gate, and no
> §8.1 attempt was spent.

### `[SCOPE LIMIT — verified in the training code, not assumed]` What "degradation OFF" does and does not mean

**Question asked before the claim was written: was vietocr's `image_aug` applied to the synthetic crops
during training?** **YES — measured, not assumed.** `configs/vgg_transformer_pinned.yml` sets
`aug.image_aug: true`; `third_party/vietocr/vietocr/model/trainer.py:80` passes `transform=augmentor` to
the **train** generator only; `third_party/vietocr/vietocr/loader/dataloader.py:121` applies it to **every**
training image **with no branch on real-vs-synthetic**. `scripts/train_budget.py` pools real + synthetic
into ONE annotation file / LMDB, so **the clean-render crops received vietocr's default augmentation every
epoch**: InvertImg (p=.2), ColorJitter (.2), MotionBlur (fixed 3-px, .2), RandomBrightnessContrast (±0.2,
.2), Perspective (0.01–0.05, .5), RandomDottedLine (.5). (Absent from that default: rotation, shear,
Gaussian/defocus blur, noise, JPEG, downsampling — measured at STEP 0.)

**Consequence for the claim — the bound is SHARPENED, not merely stated.** The floor is **identical in
every arm** (same config, same loader, same pooled LMDB), so it is **not a confound**; the 93.7%
attribution stands. And because the floor is present in both arms, the contrast the control actually
measures is **mild → aggressive**, which is the decision a practitioner faces:

| | the FLOOR (vietocr `image_aug`) — in **both** arms | the ENGINE's stack (`engine/render.py` `DEFAULT_CFG`) — **shipped arm only** |
|---|---|---|
| character | mild, generic, **document**-oriented | aggressive **scene-realism** |
| geometric | perspective 0.01–0.05; **no** rotation, **no** shear | rotation ±15° (`rot_deg=15.0`), perspective `persp_jitter=0.08`, shear 0.18, curve |
| blur | fixed 3-px motion blur | motion blur `motion_len=8`, defocus `defocus_sigma=1.5` |
| photometric | brightness/contrast ±0.2 | illumination gradients 0.32, contrast floor 0.42, glare, shadow |
| sensor | — | JPEG `qmin=34`–93, Gaussian noise σ 9.0 |
| background | — | composited onto **real scene backgrounds** (`p_real_bg=0.82`) |

> **`[THE LICENSED SENTENCE]`** *"A **mild, generic, document-oriented augmentation floor is sufficient**;
> the **aggressive scene-realism stack on top of it bought ~6%**, not separable from zero."*

This marginal **mild→aggressive** value is **more informative than a zero-augmentation arm** would have
been — nobody trains an OCR recognizer with no augmentation at all, so "is realism worth it *from zero*" is
not a decision anyone actually faces. **Scope, explicit: a true zero-augmentation arm was NEVER RUN and is
NOT being run.** The claim *"pixel realism is irrelevant from zero"* is **not licensed** and is not made.
