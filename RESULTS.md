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

Script: `scripts/audit_vintext.py` · no model, no detector involved (rec-only is scored on GT boxes).
Frozen into EVAL_PROTOCOL §13 E1/E2.

| split | total instances | `###` (do-not-care) | empty transcript | **READABLE (rec-only scorable)** | GT chars (NFC) | GT words |
|---|---|---|---|---|---|---|
| train-1200 | 35,094 | 9,300 | 18 | **25,776** | 94,364 | 26,155 |
| val-300 | 8,737 | 1,517 | 19 | **7,201** | 26,840 | 7,211 |
| **test-500** | 12,253 | 2,167 | 18 | **10,068** | **37,263** | 10,136 |
| ALL | **56,084** | 12,984 | 55 | 43,045 | 158,467 | 43,502 |

**Findings:**

1. **Total = 56,084 confirms** the figure EVAL_PROTOCOL §4 cites. The dataset is what the doc says it is.
2. **The curve's rec-only test denominator is 10,068 instances / 37,263 characters** — the doc's `~14k`
   was an explicit `[ESTIMATE]` (500 × ~28) and is now **replaced**. It was ~22% high against total
   annotated regions and ~39% high against scorable ones. Char-level denominator (37,263) is comfortably
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

---

## Open `[VERIFY]` still outstanding at Stage 0

| id | owning doc | what it is | status |
|---|---|---|---|
| test-500 rec-only instance count | EVAL_PROTOCOL §4 | ✅ **FROZEN: 10,068 / 37,263 chars** | done (§13 E1) |
| pbcquoc pretrain ⟂ VinText test | EVAL_PROTOCOL §6 | contamination check at checkpoint level | ☐ Step 0.2 |
| Gate-A noise floor (k=3 seed std) | EVAL_PROTOCOL §7 | run-to-run std of real-only baseline | ☐ Step 0.5 |
| gold set exact instance count | EVAL_PROTOCOL §5 | after stratified sample is fixed | ☐ Step 0.6 |

---

## Stage 0 model results

*(empty — no model has been trained. Nothing goes here until the real-only baseline runs at k=3 seeds
with rec-only CER + the three diacritic axes on the real test-500.)*
