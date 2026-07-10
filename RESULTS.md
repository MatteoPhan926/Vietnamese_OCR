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

---

## Open `[VERIFY]` still outstanding at Stage 0

| id | owning doc | what it is | status |
|---|---|---|---|
| test-500 rec-only instance count | EVAL_PROTOCOL §4 | ✅ **FROZEN: 10,068 inst / 37,254 chars** | done (§13 E1/E6/E8) |
| pbcquoc pretrain ⟂ VinText test | EVAL_PROTOCOL §6 | ✅ **RESOLVED as *not provable*; no contamination detected** | done (§13 E9) — 🧠 **brain to adjudicate** |
| Gate-A noise floor (k=3 seed std) | EVAL_PROTOCOL §7 | run-to-run std of real-only baseline | ☐ Step 0.5 |
| gold set exact instance count | EVAL_PROTOCOL §5 | after stratified sample is fixed | ☐ Step 0.6 |

---

## Stage 0 model results

*(empty — no model has been trained. Nothing goes here until the real-only baseline runs at k=3 seeds
with rec-only CER + the three diacritic axes on the real test-500.)*
