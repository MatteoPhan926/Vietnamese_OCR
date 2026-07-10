# CLAUDE.md — Vietnamese Document Intelligence (OCR · Synthetic Data Engine · On-Device)
### Project anchor + design brain — the ONE file that governs this project

> **What this file is.** The ANCHOR and the DESIGN BRAIN for a Vietnamese OCR system built around a
> **synthetic data engine**. Two jobs: (a) prevent drift (scope creep is the failure mode here — §2),
> and (b) be the place where *method* is reasoned before code is written. It is a **twin** of two
> sibling anchors (a from-scratch inference engine; a 3DGS physics project): same character — serious,
> precise, **no over-claiming**, honest scoping, pre-registration, validate-before-you-claim,
> treat-your-own-numbers-as-leads — instantiated for the failure modes of **data-centric applied ML**.
> In research the trap is manufacturing novelty; in systems it is a fast-but-wrong kernel; **here it is
> a dishonest evaluation and a fake scaling curve.** This file exists to make neither happen.

> **The character, stated once.** A modest, honestly-measured accuracy on **real held-out data** beats
> an impressive number on a contaminated or synthetic test set — always. "The model looks good" is not
> "the model is good": in OCR that difference is *which* metric, on *which* data, under *which* Unicode
> normalization, at *which* pipeline scope. Get those wrong and every downstream claim is fiction. The
> scaling curve is the deliverable, and a scaling curve measured on the wrong test set is worse than no
> curve — it is a confident lie.

---

## §0. LOCKED DECISIONS (made before any code — these do not reopen)

Three decisions were shopped-around in an early draft as "open questions." They are now **locked.**
Re-opening any of them mid-project is the #1 failure mode (§2) and is not allowed without a written,
dated amendment here.

- **L1 — Architecture: DBNet (detection) + fine-tuned VietOCR (recognition). LOCKED.** No PARSeq, no
  TrOCR, no DBNet++, no architecture bake-off. **Rationale (load-bearing, not convenience):** the
  flagship is the *data engine* (§8). Holding the architecture fixed is what lets every accuracy gain
  on real held-out data be **attributed to synthetic data rather than to a stronger model.** If
  architecture and data both changed, no gain could be attributed to either. A locked mediocre-but-honest
  baseline turns "+X% on real data from the data engine alone" into a clean causal claim. Swapping the
  model would *destroy the experiment*, not improve it. Trying other architectures is **future work**,
  never a Stage-0 conjecture.
- **L2 — Domain + primary test: VinText (Vietnamese scene text). LOCKED.** Not VNOnDB (handwriting) —
  they are different problems (different detection, recognition, and synthetic distributions) and must
  not be blurred. VinText is harder and noisier (in-the-wild), which makes generalization the thing
  being proven. VNOnDB is deferred, not a secondary track.
- **L3 — Track priority: (b) synthetic data engine is the flagship. LOCKED.**
  - **(b) Synthetic Data Engine — the flagship. ~60% of effort.** The rare, senior-signal artifact.
  - **(c) On-device INT8 — the finisher. ~30%.** The known-good playbook from the sibling perf project.
  - **(a) Pipeline — the vehicle. ~10%.** Get a working baseline as fast as possible; it exists to be
    measured against, not admired.
  - **Cut order if time runs short: drop (c) first, keep (a)+(b).** (a) is mandatory infrastructure —
    without a pipeline nothing can be measured. (b) is the heart. (c) adds a CV line but is not the
    thesis.

---

## §1. The locked problem (one sentence)

A **Vietnamese scene-text OCR system** — DBNet detection + fine-tuned VietOCR recognition — whose
**central contribution is a synthetic data engine proven by an accuracy-vs-synthetic-count scaling
curve on real VinText held-out data**, plus an **INT8 on-device deployment** (ONNX Runtime Mobile /
TFLite) benchmarked against **ML Kit and Tesseract** — all evaluated with **diacritic-aware,
NFC-normalized, scope-stated** metrics. An **applied-ML / data-centric flagship**, not a framework and
not a research paper.

---

## §2. What it IS / What it is NOT (anti-drift spine)

**IS:** Vietnamese scene text (VinText); DBNet+VietOCR locked; the synthetic data engine + real-data
scaling curve as the centerpiece; INT8 on-device vs ML Kit/Tesseract; diacritic-aware honest evaluation;
a story about **data infrastructure + efficient on-device ML.**

**IS NOT:**
- **NOT** an architecture bake-off. DBNet+VietOCR is locked (§0 L1); other models are future work.
- **NOT** a general multilingual OCR framework. Vietnamese scene text, locked.
- **NOT** document understanding / layout / tables / KIE / structure. Text det+rec only.
- **NOT** everything-at-once (handwriting + scene + printed + historical). VinText scene text, locked;
  VNOnDB is a different problem, deferred.
- **NOT** a novelty paper. The contribution is a **working system + an honest real-data data-engine
  curve**, not a new architecture.
- **NOT** a cherry-picked "it works" demo. One good image is not evaluation (§6).
- **NOT** three half-projects. "One project, three CV lines" is a guardrail: (a) and (c) serve (b).

---

## §3. HARD GROUND (constraints that channel the work; exacts flagged `[VERIFY]`)

**G1. Two-stage pipeline — scope EVERY number.** Detection (DBNet: find text regions) + recognition
(VietOCR: read them). Every accuracy/latency number must state its scope: **det-only** (IoU
P/R/F1 @ stated threshold), **rec-only** (given ground-truth boxes), or **end-to-end** (det errors
propagate into rec). Comparing across scopes is the most common OCR benchmark cheat — e.g. quoting your
rec-only number against a competitor's end-to-end. Lock the scope per claim, always.

**G2. THE keystone fact (the "physics" of this project — directs everything).** For Vietnamese,
**overall CER/accuracy HIDES diacritic failure.** Tone marks (á à ả ã ạ), modifiers (ă â ê ô ơ ư), and
stacks (ế ệ ữ …) are a small fraction of characters, so a model can post high overall accuracy while
systematically destroying tones. Therefore **diacritic accuracy is a first-class, separately-reported
metric** — never buried in CER. This is the single most load-bearing evaluation decision, and the
error analysis the whole project's credibility rests on.
`[VERIFY: define the exact diacritic metric before measuring anything — e.g. tone-mark accuracy on
diacritic-bearing chars, and a per-diacritic-class confusion breakdown.]`

**G3. Unicode NFC normalization is a correctness prerequisite (fuel; almost always missed).**
Vietnamese characters have multiple Unicode forms (precomposed vs base + combining marks → NFC vs NFD).
Prediction and ground truth **must be NFC-normalized identically** before scoring, or accuracy is
silently inflated or deflated by an encoding mismatch that looks like a model result. Fix normalization
once, globally, and state it in every result.

**G4. The Gold reference set — the closest thing to an oracle this problem has.** Public VinText labels
contain annotation noise, so CER against them measures *model error + label error*, entangled. To
break the entanglement, **hand-verify a frozen gold subset**: `[VERIFY: 200–300 VinText images,
transcribed codepoint-by-codepoint, NFC-normalized, double-passed (transcribe, then re-review a day
later)]`. Two distinct roles, do not conflate:
- **Gold subset = the oracle** for "how noisy is the public test set?" and for **deploy decisions.**
  Report where gold and public labels disagree — that disagreement is itself a finding.
- **Full VinText held-out = the scaling-curve test set** (§0-firewall-3). The gold subset is **too
  small (high CER variance) to carry the curve** — each curve point's error bar would swamp the gaps
  between points. Calibrate the noise floor from gold; measure the curve on the full held-out.
> **Honest limit (state it, don't hide it):** the gold set is *human*-verified, not "absolute." The
> transcriber makes diacritic errors too; the double-pass reduces but does not eliminate them. It is a
> **high-confidence gold reference**, and the claim is calibration + rigor, never infallibility.

**G5. Metrics — report the relevant one and say which.** CER, WER, sequence/exact-match differ hugely;
do not quietly pick the flattering one. Plus the G2 diacritic metrics, always separate. Detection:
IoU-based P/R/F1 at a stated threshold. Report median + spread wherever there is run-to-run variance.

**G6. The synthetic data engine (the flagship, tier b).** SynthText-style: a Vietnamese **corpus**
(news text → the real diacritic distribution) + **fonts with verified full diacritic coverage**
(⚠ many fonts render stacked marks ế/ệ/ữ wrong or drop them → you would train on garbage glyphs;
**verify coverage per font, per stacked-diacritic character**, before generating) + backgrounds +
realistic degradations (blur, noise, perspective, lighting, occlusion). **Deliverable = a scaling
curve on real VinText held-out** (accuracy vs 10k / 50k / 200k synthetic), everything else fixed.

**G7. On-device (the finisher, tier c).** INT8 quantize → export ONNX Runtime Mobile / TFLite →
measure **ms/image on your phone** vs **ML Kit** and **Tesseract**. Fair-benchmark constraints (from
the sibling perf project): same images, same phone, **matched pipeline scope** (ML Kit/Tesseract run
end-to-end — match that), **thermal state controlled** (phones throttle — cool down between runs,
report conditions), warmed up, median + spread. AND **report accuracy-after-INT8, including the
diacritic metric** — quantization can hurt exactly the hard cases (tones, small text); a fast model
that lost tone accuracy is the "fast-but-wrong" trap in this domain.

---

## §3.5. THE FIREWALLS (no exceptions — the data-centric analog of the sibling projects' three)

1. **Real-data evaluation before any claim.** All accuracy — and *especially* the scaling curve — is
   reported on **real VinText held-out**, with **diacritic-aware metrics**, **NFC normalization**, and
   **strict train/test separation** (no synthetic or training data overlapping the test set). A number
   on synthetic or contaminated data is **not a result.**
2. **Evaluation honesty.** State **which metric** (CER/WER/exact-match — they differ), **the pipeline
   scope** (det-only / rec-only / end-to-end — never compare mismatched scopes), and **report diacritic
   accuracy separately** (overall CER hides tone failure — G2). Median + spread where there's variance.
3. **Synthetic-to-real discipline.** The scaling curve is measured on **real** test data — more
   synthetic trivially raises *synthetic*-test accuracy, and that curve is circular and worthless. Hold
   **everything else fixed** (architecture per L1, hyperparams, real-data amount, eval protocol); vary
   **only** synthetic count. **Report the true curve shape** — a plateau or a help-then-hurt at 200k is
   a real finding, not something to bury.

> **Launder nothing.** Any accuracy/curve/speedup stays a `[CONJECTURE]` until a real-data,
> protocol-clean, reproducible measurement backs it. Leaderboard/paper/blog numbers are **leads to
> verify on Vietnamese data**, not facts — a model that tops an English or scene-text leaderboard may
> lose on Vietnamese diacritics.

---

## §4. THE LADDER (locked sequence — note the make-or-break gate in the middle)

Unlike a linear systems ladder, this project has a **decision gate that must resolve before the
flagship work scales.** Building the 200k-scale engine before proving synthetic helps at 10k is the
tool-first derailment (§9) — machinery built on an untested assumption.

- **Stage 0 — Pipeline baseline + evaluation harness + Gold set.** Fine-tune VietOCR, stand up DBNet,
  get an end-to-end baseline running on VinText. **Build the CER/WER + diacritic-metric harness with
  correct NFC normalization, and hand-verify the gold subset (G4).** This is the oracle + the ruler.
  Like Stage 0 of the sibling engine: slow, correct, the reference everything is judged against.
  Nothing downstream means anything until this exists. **~10% effort (the vehicle).**
- **Stage 1 — Error analysis (measure before you optimize).** *Before* building synthetic, find where
  errors concentrate: diacritics specifically (which tones/stacks)? small text? certain fonts/
  backgrounds? detection failures vs recognition failures? **The error analysis decides what the
  synthetic engine must generate** — generating blindly and hoping is the derailment. The diacritic
  breakdown here is the most credible single artifact the project produces.
- **★ GATE A — Does synthetic data close the real gap AT ALL?** Generate a **small batch (~10k)**, train,
  and **test on real VinText held-out**. Measure the synth→real improvement.
  - **GREEN** (synthetic-augmented lifts real accuracy above real-only) → proceed to Stage 2.
  - **RED** (no real lift) → **STOP. Do not scale to 200k.** Diagnose the synth-real gap (font realism?
    degradation realism? background distribution? domain mismatch vs scene text?), fix the engine, and
    **re-run Gate A at 10k.** Red-at-10k is cheap; red-discovered-at-200k is two wasted weeks. This gate
    is the whole reason the project can't quietly fail. Track (b) is not dead on red — it means the
    engine needs better domain randomization *before* scale, not more data.
- **Stage 2 — The scaling curve (ONLY if Gate A is green).** Now 10k → 50k → 200k, **each point tested
  on the full real VinText held-out** (not the gold subset — G4), everything else fixed (firewall 3).
  Plot the curve; **its shape is the finding** (still rising? plateau? help-then-hurt?). This is the
  flagship artifact. **~60% effort (the flagship).**
- **Stage 3 — On-device INT8.** The sibling perf playbook: INT8 quantize → ONNX Mobile/TFLite → measure
  ms/image on your phone vs ML Kit and Tesseract, matched scope, thermal-controlled. **Quality gate:
  accuracy (incl. diacritics) after INT8 within the pre-registered bound (§5).** **~30% effort (the
  finisher); cut first if time runs short.**

---

## §5. DESIGN BETS (labeled `[CONJECTURE]`; each kill-test is a MEASUREMENT on real data)

- **[CONJECTURE]** Synthetic data raises real-VinText accuracy, with a curve still rising at 200k.
  *Kill-test:* the real-data scaling curve. Plateau/decline → **report it**; it bounds the engine's
  value honestly, and an honest plateau is still a strong result.
- **[CONJECTURE]** Synthetic-pretrain + small real fine-tune ≥ real-only training. *Kill-test:* both on
  real held-out, same scope, same metric.
- **[CONJECTURE]** INT8 holds accuracy within `[pre-register: e.g. CER +0.5 absolute, diacritic
  accuracy −1%]` vs fp32. *Kill-test:* real-test accuracy incl. diacritic metric, before/after. Exceeds
  → per-channel quant, or keep sensitive layers (recognition head; small-text-critical layers) fp16.
- **[CONJECTURE]** The dominant error class is diacritics, not base characters or detection.
  *Kill-test:* Stage-1 error analysis on real data. (If it's actually detection or small-text, the
  synthetic engine's priorities change — which is exactly why Stage 1 precedes the engine.)

> **No accuracy or curve is a result until a real-data, protocol-clean, reproducible measurement backs it.**

---

## §6. The central validation gates (make-or-break, purely empirical)

- **ACCURACY gate (every model/claim):** real VinText held-out, **diacritic metric reported
  separately**, **NFC-normalized**, **train/test clean**, **pipeline scope stated**. Missing any one →
  not a result. Cherry-picked demo images are never evaluation.
- **DATA-ENGINE gate (Gate A + the curve):** Gate A tested on real data at 10k before any scaling; the
  curve on **real** test data with **everything else fixed** and the **true shape** reported (including
  diminishing returns). A curve on synthetic test data, or with confounded changes, proves nothing.
- **ON-DEVICE gate:** fair benchmark (same images/phone, **matched scope**, thermal-controlled, warmed,
  median + spread) **AND accuracy-after-INT8 reported** (latency without the accuracy delta is half the
  truth, and the missing half is where diacritics die).

---

## §7. Scope / validity (claim only within)

**In:** Vietnamese scene-text det+rec (DBNet+VietOCR) on VinText; the synthetic data engine + real-data
scaling curve; INT8 on-device on your phone; ML Kit + Tesseract baselines. **Deferred (future work, no
claim):** other architectures, other languages, VNOnDB/handwriting, printed/historical domains,
layout/table/KIE/structure, other devices, training-time optimization, a general framework.

---

## §8. Goal alignment (scope/finishing only — NOT a steer on evaluation honesty)

Narrative: **Infrastructure & Data.** A **synthetic data engine** is literally the track's language, and
synthetic-data thinking is **Omniverse / simulation** thinking — programmatic, controlled data
generation to solve a real-world perception problem. On-device INT8 maps to **Qualcomm / edge
inference**. The three tiers are three coherent CV lines (data, modeling, deployment) with the data
engine as the senior-signal centerpiece: it moves the story from "AI user" to "AI infrastructure
builder." **Guardrail:** these goals decide *what to build and finish* — they must **never** relax the
diacritic metric, present a synthetic-only curve as if it were real, contaminate the test set, weaken
the gold-verification, or excuse an unfair on-device comparison. A reviewer will probe exactly the
evaluation methodology; **honesty is the moat** — the entire pitch is "+X% on real data, attributable
to the data engine, measured against a gold reference I built myself." That sentence is only worth
anything if every word survives scrutiny.

---

## §9. Process rules

1. **Evaluation protocol before modeling.** Fix the metric (incl. diacritics), NFC normalization,
   splits, gold set, and pipeline scope **first** — then train. A wrong protocol makes every later
   number meaningless.
2. **Real-data measurement before any claim** — especially Gate A and the scaling curve.
3. **Error analysis before optimization.** Fix the *measured* failure (diacritics? detection? fonts?),
   not a guessed one. Stage 1 exists to prevent building the engine on a guess.
4. **One change at a time**, with a real-data before/after. Revert changes without a real, clean gain.
5. **Commit; don't thrash.** The architecture (L1), domain (L2), and priorities (L3) are locked. Do not
   expand to layout/KIE/handwriting/multilingual or swap models to chase scope.
6. **Treat your own numbers — and every leaderboard/blog claim — as LEADS** to verify on Vietnamese real
   data, at the right scope, with the right metric.
7. **Reproducibility.** Every result = a script + config + **data manifest** (which real/synthetic split,
   which fonts, which corpus) + seed. On-device: + phone model + thermal conditions. If you can't
   reproduce it, you don't have it.
8. **Numbers go back to the brain** (chat) for the protocol/plausibility check before they're believed;
   train and benchmark in Claude Code / your box + phone.

---

## §10. Pointers (sibling docs — draft separately)

The methodology deserves its own files, kept beside this anchor. Draft them in a separate conversation
(to avoid cross-project drift), then hard-check them against this anchor:
- `RESULTS.md` — per model/stage: real-VinText CER/WER, **diacritic accuracy (separate)**, det F1@IoU,
  pipeline scope, splits used. The measured-evidence ledger.
- `ERROR_ANALYSIS.md` — the diacritic breakdown as centerpiece (the most credible artifact you'll
  produce), plus det-vs-rec and small-text analysis.
- `SCALING.md` — the real-data synthetic scaling curve with the full protocol (fonts, corpus, degradations,
  fixed variables, Gate-A result) noted, so the curve is reproducible and its honesty is auditable.
- `DATA_ENGINE.md` — the synthetic generator's design: corpus source, per-font diacritic-coverage
  verification, degradation model, and the Gate-A / re-diagnosis loop.
- Optional `ocr_eval_store.md` — durable domain facts (Vietnamese diacritic structure, NFC/NFD, metric
  definitions, synth-to-real pitfalls, font-coverage gotchas) — build only if the reasoning repeats.

  ## §11. AMENDMENTS (dated; supersede any conflicting text above)

**[2026-07-10] A1 — L1 backbone pinned.** L1 locked "fine-tuned VietOCR" but not the config. Backbone is
now explicitly **pbcquoc `vgg_transformer`** (VGG CNN encoder + Transformer decoder), NOT `vgg_seq2seq`.
Rationale + terminology guard: EVAL_PROTOCOL §6. Reason: the two configs give different INT8 stories, so
exactly one must be named in every file.

**[2026-07-10] A2 — On-device target corrected to iOS.** §1/§2/§4-Stage3/§6/§7 name TFLite / ML Kit /
Android-style deployment. The locked device is **iPhone 12 Pro Max (A14, iOS 26.5.2)**; export path
**Core ML or ONNX Runtime for iOS**; the primary on-device baseline is **Apple Vision Framework**
(Vietnamese-supported, confirmed on-device), Tesseract optional. ML Kit / TFLite (Android) are dropped.
Full on-device protocol: EVAL_PROTOCOL §8–9. INT8 now carries BOTH a quality gate AND a **speed gate +
Core ML compute-unit dispatch instrumentation** (EVAL_PROTOCOL §8) — the sibling GPT-2 project showed INT8
can buy ~1.00× at batch=1 on a small model.

**[2026-07-10] A3 — Doc suite + pointers.** The §10 methodology docs were drafted and hard-checked against
this anchor. Add to the pointer list: **`EVAL_PROTOCOL.md`** (the concrete instantiation of §9.1 — metrics,
gates, gold spec; the measurement ruler) and **`BUILD_PLAN.md`** (the stateful, resumable build roadmap —
read + update every session). `RESULTS.md` is created and filled by the implementation agent during build.
