# ERROR_ANALYSIS.md — the diagnostic instrument (measure before you optimize)

> **What this file is.** The error-analysis method **and** the report template it fills — a **sibling of
> EVAL_PROTOCOL.md and DATA_ENGINE.md**. EVAL_PROTOCOL *defines* the metrics; this file *uses* them to
> localize failure: **where** errors concentrate, **on which axis**, **on which crops**, **driven by
> what**. It is the most credible single artifact the project produces (CLAUDE.md §10) and the Stage-1
> instrument that sets the engine's priorities (DATA_ENGINE §3). Same character: report the full
> breakdown, never the flattering slice; every finding names a specific knob; nothing is optimized before
> it is measured.
>
> **The one job.** Turn "the model is X% accurate" into "the model fails *here*, for *this* reason, which
> the engine fixes with *that* knob." A number that does not localize a fix is not error analysis.

---

## §1. Place in the ladder, and the recurring role

Error analysis is **Stage 1** (CLAUDE.md §4) — it runs **before** the synthetic engine exists, and it
recurs:

- **Run 0 (the load-bearing one) — on the real-only baseline** (pretrained + full VinText-real, **no
  synthetic**, EVAL_PROTOCOL §6 operating point). Its output **is** DATA_ENGINE §3's priority list.
  Building the engine before this run is the tool-first derailment (CLAUDE.md §9).
- **Runs 1..k — at each Gate-A RED diagnosis** (DATA_ENGINE §8): localizes what the engine still misses,
  on the ranked axes.
- **Final run — on the shipped model.** The **per-axis before/after** (Run 0 → final) is the flagship's
  proof: the engine was built to fix specific axes on specific crops; this table shows it did (or did
  not). Pre-register that the final model is judged on **moving the axes it targeted**, not on overall CER
  alone.

---

## §2. What it runs on, and the anti-cherry-pick rule

- **`[LOCKED]`** Real VinText held-out, **NFC** (CER/WER) and **NFD** (diacritic axes), per EVAL_PROTOCOL
  §2. Rec-only is the primary lens (the curve's scope); e2e is analyzed in §5.
- **`[LOCKED]` Both label sources.** Every breakdown is computed against **public labels** (entangled:
  model + label error) **and** the **gold subset** (clean, EVAL_PROTOCOL §5). The **difference is a
  finding** (§4).
- **`[LOCKED]` Median + spread over k=3 seeds** wherever the model varies.
- **`[LOCKED]` The full breakdown set below is pre-registered and all of it is reported.** Error analysis
  is where cherry-picking creeps in (show the clean confusion matrix, bury the messy one). No breakdown in
  §3–§6 is dropped because it is unflattering — an unflattering breakdown is the most useful one.

---

## §3. Centerpiece — the three-axis diacritic breakdown (CER hides tone failure, made quantitative)

The single most credible artifact. It takes EVAL_PROTOCOL §3.1's three axes and reports their **values,
their relationship to CER, and their internal confusions.**

**§3.1 Per-axis accuracy** — Base (Axis 1), Modifier (Axis 2), Tone (Axis 3), on tone/modifier-bearing
positions. Slots to fill (real held-out, gold cross-checked):

| axis | accuracy | error rate | notes |
|---|---|---|---|
| Base letter | … | … | expected highest — the prior reads letters well |
| Modifier (ă â ê ô ơ ư, đ) | … | … | font-driven when it fails (§ DATA_ENGINE §5) |
| Tone (sắc/huyền/hỏi/ngã/nặng) | … | … | capture-driven — the fragile axis |

**`[LOCKED]` §3.2 Decompose CER into the axes — THE headline finding.** For each character-substitution
error (aligned pred ≠ GT), NFD-decompose both and attribute the error to which axis/axes differ. Report:
- the share of all character errors that involve a **tone** difference vs **modifier** vs **base**;
- the share that are **pure-tone errors** — base and modifier correct, only the tone wrong (GT `ệ` →
  pred `ê`: right `e`, right circumflex, wrong tone). A large pure-tone share is the **quantitative proof
  of G2**: a model with a respectable CER can be systematically destroying tones, and only this
  decomposition sees it. If Tone-axis error rate ≫ Base-axis error rate, say so in one sentence — that
  sentence is the project's thesis in numbers.

**`[LOCKED]` §3.3 Per-axis confusion matrices** (deliverables, not diagnostics-only):
- **Tone:** the **hỏi (̉) ↔ ngã (~)** confusion (canonical — visually near-identical small marks above);
  **sắc/huyền** slant confusion; and **tone-drop** (any tone → none) under blur/low-res.
- **Modifier:** systematic **mark-drop** — horn (`ư→u`, `ơ→o`), circumflex (`â→a`, `ê→e`, `ô→o`), breve
  (`ă→a`), stroke (`đ→d`). On real data these are capture-driven; the same pattern from synthetic training
  is a **font-coverage leak** (§4, DATA_ENGINE §5).

**`[LOCKED]` §3.4 Per-class breakdown** — which specific tones and modifiers fail most, ranked. This ranked
list is what DATA_ENGINE curriculum over-sampling (only what is measured to fail) consumes.

---

## §4. Model-vs-label disentanglement (the gold cross-check earns its keep here)

Raw CER against public labels = **model error + label error**, entangled. Run every §3 breakdown against
**both** the public labels and the gold subset (EVAL_PROTOCOL §5):

- **`[LOCKED]`** Report **gold − public** per axis. Where the model's "error" against public labels
  disappears against gold, that error was **label noise**, not model failure — and it quantifies the
  public test set's noise floor (the number the whole curve is calibrated against).
- **`[LOCKED]`** A tone/modifier "error" that is really a **public-label diacritic mistake** must not be
  charged to the model or used to prioritize the engine. This is exactly why the gold set is verified
  codepoint-by-codepoint: Vietnamese public labels miss and mistype tones, and un-caught label noise would
  send the engine chasing a failure that isn't the model's.

---

## §5. Det-vs-rec attribution (where do e2e errors come from — and the e2e ceiling)

- **`[LOCKED]` The attribution number = e2e CER − rec-only CER** (rec-only given GT boxes, EVAL_PROTOCOL
  §1). The gap is **detection-induced error**.
- **`[LOCKED]` Categorize detection failures:** missed boxes (recall failures — text the recognizer never
  sees), false boxes, and **boundary errors that clip characters** (a box cutting off a leading/trailing
  glyph, which then reads as a recognition error but is a detection cause).
- **`[LOCKED]` State the e2e ceiling.** The synthetic engine helps **recognition**; if detection is the
  bottleneck, the engine's effect on **e2e** is capped regardless of how good recognition gets. This is
  *why* the headline curve is rec-only (EVAL_PROTOCOL §1) and must be stated so the rec-only gain is not
  mistaken for an e2e promise.

---

## §6. Stratifications (pre-registered set; each maps to a generator knob)

Error is stratified along the axes that name a DATA_ENGINE §6 knob. All reported; none dropped.

- **`[LOCKED]` Crop height / resolution (the small-text analysis, CLAUDE.md §10).** Error vs crop height,
  **per axis** — the Tone-axis-vs-height curve is expected to fall off a cliff at small sizes (tones are
  tiny high-frequency marks). → drives the **downsample→upsample + blur** degradations (DATA_ENGINE §6),
  and confirms/refutes DATA_ENGINE §3's assumption that tone failures concentrate on small crops.
- **`[LOCKED]` Contrast / lighting.** Error on low-contrast crops, per axis. → **photometric** degradation.
- **`[LOCKED]` Text length.** Error vs string length (long strings accumulate). → generation length
  distribution (DATA_ENGINE §4).
- **`[LOCKED]` Orientation / perspective.** Error on rotated / angled text. → **geometric** degradation.
- **`[LOCKED]` Stylized vs plain appearance** (proxy: visual-style cluster or a plain/stylized flag). →
  tests DATA_ENGINE §5's caveat that clean digital fonts under-represent signage (if stylized crops fail
  disproportionately, widen appearance augmentation, not raw font count).

---

## §7. Findings → priorities (the whole point — a measured failure names a fix)

Each localized failure maps to exactly one owner, so the engine is tuned against measurement, not a guess:

- **Tone-axis fails, concentrated on small/low-res crops** → resolution + blur degradation (DATA_ENGINE §6).
- **Modifier-axis fails (mark-drop)** → font coverage first (DATA_ENGINE §5), not degradation.
- **Base-axis fails on low-contrast / occluded / angled crops** → photometric + geometric degradation (§6).
- **Stylized crops fail disproportionately** → widen appearance augmentation (§5 caveat).
- **Detection is the bottleneck (large §5 gap)** → **out of the engine's scope**; note the e2e ceiling,
  do not spend synthetic budget on a recognition fix for a detection problem.

> **`[LOCKED]`** A finding that does not name an owner above is not actionable and is not used to
> prioritize the engine. "Errors exist" is not error analysis; "Tone-axis is 18 points below Base-axis and
> the gap is 3× worse below 20 px crop height" is.

---

## §8. The recurring runs and the before/after proof

- **`[LOCKED]`** Run 0 (real-only baseline) → the priority list (§7) → engine built.
- **`[LOCKED]`** Runs 1..k (Gate-A RED diagnoses) → the ranked-axis localization DATA_ENGINE §8 consumes.
- **`[LOCKED]` Final before/after table** — Run 0 vs the shipped model, **per axis and per targeted
  stratum** (e.g. Tone-axis accuracy on <20 px crops, before → after). This is the flagship's proof and
  the reviewer's first question answered in advance: the engine targeted specific failures; here is the
  measured movement on exactly those. Overall CER before/after is reported too, but the **per-axis
  movement on targeted strata is the claim**.

---

## §9. Reproducibility

**`[LOCKED]`** Every analysis run = **script + config + model checkpoint id + data manifest + seed**, with
**both** gold and public results reported. The confusion matrices and stratified tables are regenerable
from the checkpoint + held-out split named in the manifest (EVAL_PROTOCOL §11). An error breakdown you
cannot regenerate is an anecdote, not a finding.

---

## §10. Scope / validity

**In:** three-axis diacritic breakdown (+ CER decomposition + confusions + per-class ranking), model-vs-label
disentanglement via gold, det-vs-rec attribution, and the pre-registered stratifications — all on real
VinText held-out, rec-only primary, e2e in §5. **Not claimed:** an analysis of other domains/languages, a
linguistic study of Vietnamese orthography beyond what the axes measure, or any error attribution not
backed by the gold cross-check. The instrument localizes *this* model's failures on *this* data to *this*
engine's knobs — nothing wider.

---

# ══════════ RUN 0 REPORT — real-only baseline (filled 2026-07-10) ══════════

**Manifest (§9).** `scripts/error_analysis.py` + `scripts/stratify.py` · inputs
`runs/baseline_seed{0,1,2}/predictions.tsv` (10,068 GT↔pred pairs each) · model = real-only baseline,
k=3 seeds, EVAL_PROTOCOL §6 operating point · scope **rec-only (GT boxes)** · **NFC** (CER/WER), **NFD**
(axes) · test-500 real held-out, denominator 10,068 instances / 37,254 chars · **public labels**
(gold cross-check §4 is BLOCKED, see below) · base axis reported **case-insensitively** (brain
adjudication 2026-07-10), case-sensitive retained as a diagnostic.

## §3.1 Per-axis accuracy (k=3 median)

| axis | accuracy | **error rate** | doc's prior expectation | verdict |
|---|---|---|---|---|
| Base letter (case-insens) | 95.119% | 4.881% | "expected highest — the prior reads letters well" | **REFUTED** — not the highest |
| Base letter (case-sens) | 94.081% | 5.919% | — | 17.5% of base error is pure case |
| Modifier | 96.207% | 3.793% | "font-driven when it fails" | **highest** accuracy |
| Tone | 94.423% | **5.577%** | "capture-driven — the fragile axis" | **CONFIRMED** — least accurate axis |

Tone is the least-accurate axis. But accuracy is not share-of-CER — the axes have very different
denominators (base 32,267 positions; tone 12,875; modifier 11,126). §3.2 measures the share directly.

## §3.2 CER decomposition — **THE KILL-TEST** (k=3 median, share of ALL character edits)

Total edits ≈ 3,500 per seed [3,437–3,547].

| edit class | share of ALL edits |
|---|---|
| substitutions | 72.62% |
| deletions | 15.51% |
| insertions | 11.51% |

Substitutions partitioned by **which axes differ** (these sum to 100% of substitutions):

| pure class | share of subs | **share of ALL edits** |
|---|---|---|
| **pure base** (case-insens; mod+tone right) | 54.29% | **39.48%** |
| mixed (>1 axis) | 14.94% | 10.91% |
| **PURE TONE** (base+mod right, tone wrong) | 14.44% | **10.40%** |
| pure case (only letter case differs) | 12.16% | 8.88% |
| pure modifier | 4.68% | 3.37% |

Rolled up over all edits: **base-only substitutions 39.48%** vs **diacritic-only substitutions 16.12%**;
any-base-involved 47.75% vs any-diacritic-involved 24.50%.

> ### `[FINDING — REFUTES CLAUDE.md §5]`
> **The dominant error class is base characters, not diacritics.** Base-only substitutions account for
> **39.48%** of all character edits; diacritic-only (tone *or* modifier) substitutions account for
> **16.12%** — base outweighs diacritics by ~2.5×. Base errors are involved in **47.75%** of edits vs
> **24.50%** for diacritics.
>
> This does **not** invalidate G2 or the three-axis metric — it *vindicates* them. Tone remains the
> **least accurate** axis (5.577% error vs base's 4.881%), exactly as G2 predicts, and only the three-axis
> decomposition can show both facts at once: **tone is the most fragile axis per-opportunity, while base
> is the largest contributor to total error, because base positions outnumber tone-bearing positions
> 2.5:1.** A single "diacritic accuracy" number would have shown neither. The pure-tone share (10.40% of
> all edits) is real and non-trivial, but it is not the dominant class.

## §3.3 Per-axis confusion matrices (seed 0)

**Tone** — decomposed by failure *mechanism*, which is the actionable cut:

| mechanism | count |
|---|---|
| real tone → **ngang** (tone DROP) | 215 |
| **ngang → spurious tone** (hallucinated mark) | 174 |
| real tone → other real tone (discrimination error) | 199 |

Top cells: `ngang→<del>` 133, `huyen→ngang` 70, `sac→ngang` 65, `ngang→sac` 62, `ngang→huyen` 54,
`hoi→ngang` 36, `nang→ngang` 34.

> ### `[FINDING — REFUTES this doc's own §3.3 expectation]`
> **The canonical hỏi ↔ ngã confusion is essentially absent.** `hoi→nga` = **4**, `nga→hoi` = **4**
> (4.6% of hỏi errors, 10.0% of ngã errors). §3.3 named it "the canonical Vietnamese tone confusion";
> on this data it is a rounding error.
>
> Tone failure is instead **presence/absence, not shape discrimination**: 215 drops + 174 hallucinations
> = 389 events vs 199 tone-to-tone confusions. The model fails to *see* the mark; it does not *mistake*
> one mark for another. **Knob consequence:** this points at resolution/blur/photometric degradation
> (making marks hard to see), **not** at over-sampling visually-similar tone pairs.

**Modifier** — same drop/hallucinate signature: `circumflex→none` 78, `none→circumflex` 63,
`none→horn` 40, `stroke→none` 30, `horn→none` 25, `breve→none` 15, `none→breve` 12.

**Base (case-insens)** — confusable letter shapes: `a→o` 30, `a→n` 19, `m→n` 19, `g→c` 17, `o→a` 17,
`i→a` 15, `o→u` 15, `e→a` 13, `a→u` 13, `u→o` 12.

## §3.4 Per-class ranking (seed 0) — what curriculum over-sampling consumes

| tone class | errors | positions | **error rate** |
|---|---|---|---|
| **hỏi** | 90 | 617 | **14.59%** |
| **ngã** | 40 | 296 | **13.51%** |
| huyền | 122 | 1,310 | 9.31% |
| sắc | 114 | 1,461 | 7.80% |
| nặng | 62 | 1,233 | 5.03% |
| ngang (none) | 307 | 7,958 | 3.86% |

| modifier class | errors | positions | **error rate** |
|---|---|---|---|
| **breve (ă)** | 27 | 242 | **11.16%** |
| stroke (đ) | 35 | 667 | 5.25% |
| circumflex (â ê ô) | 100 | 2,161 | 4.63% |
| none | 223 | 6,766 | 3.30% |
| **horn (ơ ư)** | 37 | 1,290 | **2.87%** |

> `[FINDING]` **hỏi and ngã are the two worst tone classes by error rate** (14.59%, 13.51%) — the doc's
> intuition about *which classes* are fragile is right even though its account of *how* they fail
> (mutual confusion) is wrong. They fail by being dropped, not by being swapped for each other.
>
> `[FINDING — REFUTES §3.3 expectation]` **Horn (`ơ ư`) is the *most* accurate modifier class (2.87%
> error), not a systematic drop.** §3.3 and DATA_ENGINE §5 single out "horn drop" as the signature
> failure. On real data the worst modifier is **breve (`ă`, 11.16%)**, ~4× horn's rate. Note breve has
> the smallest denominator (242 positions), so its rate carries the widest error bar of the five.

## §4 Model-vs-label disentanglement — **BLOCKED, not skipped**

`[LOCKED]` §4 requires every §3 breakdown against **both** public labels and the gold subset. **The gold
labels do not exist yet**: the 2,437-instance stratified sample and transcription sheet are built
(EVAL_PROTOCOL §13 E10) but the codepoint-by-codepoint double-pass is the user's manual work and was
**not fabricated**. Every number in this Run-0 report is therefore against **public labels only** and is
**entangled: model error + label error**.

This matters concretely and directionally: label noise inflates *base* errors (a mis-transcribed word)
and *insertions* (public `VỰ` vs image `VỰC` — a real, verified case on `im1501`, test-500's first image).
The 39.48% pure-base share is therefore an **upper bound** on the model's true base-error share.
**The §3.2 finding must be re-run against gold before it is treated as settled.**

## §5 Det-vs-rec attribution — **DEFERRED within Stage 1**

DBNet is not yet set up, so `e2e CER − rec-only CER` is unmeasured and the **e2e ceiling is unstated**.
Per §7 this is load-bearing: if detection is the bottleneck, the engine's e2e effect is capped regardless
of recognition gains. Must be closed before the priority list is final.

## §6 Stratifications (k=3 median; all reported, none dropped)

Base is reported case-insensitively.

**Crop height** → knob: downsample→upsample + blur

| bin | n | CER | base | modifier | tone |
|---|---|---|---|---|---|
| <12 px | 953 | **22.86%** | 85.08% | 88.33% | 85.88% |
| 12–15 | 1,090 | 10.30% | 94.70% | 95.23% | 93.05% |
| 16–19 | 876 | 8.25% | 96.34% | 97.46% | 94.93% |
| 20–23 | 851 | 8.08% | 96.74% | 97.14% | 94.46% |
| 24–31 | 1,532 | 7.32% | 96.55% | 97.07% | 95.90% |
| 32–47 | 1,795 | 7.18% | 96.49% | 97.24% | 95.62% |
| ≥48 | 2,971 | 7.61% | 96.11% | 97.44% | 95.74% |

**Contrast (Michelson)** → knob: photometric degradation

| bin | n | CER | base | modifier | tone |
|---|---|---|---|---|---|
| <0.20 | 468 | **27.55%** | 82.28% | 86.47% | 83.55% |
| 0.20–0.29 | 997 | 14.04% | 91.22% | 93.32% | 91.16% |
| 0.30–0.39 | 1,906 | 8.18% | 96.00% | 96.24% | 94.66% |
| 0.40–0.49 | 1,877 | 8.66% | 95.90% | 97.33% | 94.81% |
| 0.50–0.64 | 2,582 | 8.21% | 95.60% | 97.23% | 95.52% |
| ≥0.65 | 2,238 | 6.54% | 97.54% | 97.52% | 96.36% |

**Text length** → knob: generation length distribution

| bin | n | CER | base | modifier | tone |
|---|---|---|---|---|---|
| 1 char | 560 | **25.89%** | 80.54% | 93.15% | 94.57% |
| 2–3 | 4,762 | 10.19% | 95.40% | 95.90% | 93.27% |
| 4–5 | 3,681 | 7.21% | 96.58% | 96.94% | 95.32% |
| 6–8 | 769 | 10.95% | 91.77% | 95.50% | 94.85% |
| 9–12 | 251 | 9.78% | 94.90% | 97.74% | 97.91% |
| ≥13 | 45 | 18.73% | 83.26% | 89.57% | 87.23% |

**Orientation (tilt of top edge)** → knob: geometric degradation

| bin | n | CER | base | modifier | tone |
|---|---|---|---|---|---|
| <2° | 4,229 | 7.40% | 96.44% | 97.20% | 95.63% |
| 2–5° | 2,743 | 7.95% | 96.66% | 96.94% | 95.01% |
| 5–10° | 1,605 | 10.20% | 94.80% | 95.66% | 92.93% |
| 10–20° | 1,001 | 11.05% | 93.97% | 95.45% | 94.01% |
| **≥20°** | 490 | **30.34%** | 78.40% | 87.93% | 86.23% |

**Stylized vs plain** — **BLOCKED, not dropped.** VinText ships no style annotation, and no defensible
proxy exists without one. A fabricated proxy would be worse than a stated gap.

> ### `[FINDING — REFUTES DATA_ENGINE §3's assumption]`
> **Tone does not fall off a cliff at small sizes relative to the other axes — every axis does, and base
> falls hardest.** From the ≥24 px plateau to <12 px: base −11.4 pp (96.5→85.1), tone −10.0 pp
> (95.9→85.9), modifier −8.8 pp (97.1→88.3). §6 pre-registered the expectation that "the Tone-axis-vs-
> height curve falls off a cliff"; it does fall, but **not disproportionately**. Small text is a
> *general* legibility failure, not a specifically-diacritic one.
>
> The same holds for contrast (<0.20: base 82.28% vs tone 83.55% — base is *worse*) and, most sharply,
> for orientation (≥20°: base **78.40%** vs tone 86.23%). **Geometry is the single most damaging
> stratum measured** (CER 30.34%), narrowly ahead of low contrast (27.55%) and tiny crops (22.86%).
>
> `[FINDING]` **1-character instances are an outlier**: CER 25.89% with base at 80.54% but tone at
> 94.57%. Isolated glyphs destroy base-letter identity (no lexical context) while leaving tone intact.

## §7 Findings → priorities (ranked; each names exactly one owner)

Ranked by **share of total character error × tractability by a data knob**. Detection (§5) is unmeasured,
so this list is **provisional** and cannot be final until §5 and the §4 gold cross-check close.

| # | measured failure | evidence | owner (DATA_ENGINE knob) |
|---|---|---|---|
| 1 | **Base-letter error dominates** (39.48% of edits) and collapses under geometry, low contrast, small size | §3.2, §6 | **geometric + photometric degradation** (§6) — *not* font coverage |
| 2 | **Angled text (≥20°) is the worst stratum**: CER 30.34%, base 78.40% | §6 | **geometric degradation** (perspective/rotation) (§6) |
| 3 | **Low contrast (<0.20)**: CER 27.55%, all axes ≈ −13 pp | §6 | **photometric degradation** (§6) |
| 4 | **Small crops (<12 px)**: CER 22.86%, all axes fall together | §6 | **downsample→upsample + blur** (§6) |
| 5 | **Tone failure = drop/hallucinate (389 events) not confusion (199)**; hỏi 14.59% / ngã 13.51% worst classes | §3.3, §3.4 | **resolution + blur** (§6) — *not* similar-tone over-sampling |
| 6 | **Modifier: breve (ă) worst at 11.16%**; horn is *best* (2.87%) | §3.4 | **font coverage** (§5) — but low priority: modifier is only 3.37% of edits |
| 7 | 1-char instances: CER 25.89%, base 80.54% | §6 | **generation length distribution** (§4) — include short/isolated glyphs |
| — | detection bottleneck? | **UNMEASURED** | §5, blocked on DBNet |

> **The headline for the brain.** The engine's priority is **degradation realism — geometric first, then
> photometric, then resolution/blur** — and **not** the font-coverage / stacked-diacritic curriculum that
> CLAUDE.md §5 and DATA_ENGINE §5 anticipated. The diacritic machinery was not wasted: it is precisely
> what proved diacritics are *not* the dominant class, and it still localises tone failure to a
> *mechanism* (mark drop) that the same degradation knobs address. Font coverage remains a **correctness
> prerequisite** for generation (a font that cannot render `ệ` poisons training) but is **not** where the
> measured error is.
