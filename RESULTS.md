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
