# BUILD_PLAN.md — the roadmap and the resume state (READ + UPDATE every session)

> **What this file is.** The **stateful build plan** and the **session-resume anchor**. The 4 method docs
> (EVAL_PROTOCOL / DATA_ENGINE / ERROR_ANALYSIS / SCALING) say *what is correct*; CLAUDE.md says *what is
> locked*; **this file says where you are and what to do next.** It exists because a Claude Code session
> can run out of context mid-task — so the plan is written to be picked up cold by a fresh session that
> has read nothing but this file's top block.
>
> **The rule that makes it work:** after every meaningful step you **overwrite the RESUME POINTER**, tick
> the stage STATUS, and **commit to git**. Git history + this pointer are your memory across sessions. A
> step that is done but not written here did not happen, as far as the next session knows.

---

## ▶ RESUME POINTER  (the agent overwrites this block every session — read it FIRST)

```
CURRENT STAGE : Stage 2 — Synthetic engine v0 + Gate A @ 10k.  (Stage 1 core ☑, BRAIN-ADJUDICATED 2026-07-10.)
STAGE-2 PROGRESS (2026-07-11, this session):
  ☑ Font pipeline (engine/fetch_fonts, font_gate, font_sheet, finalize_fonts): 30 Google-Fonts
    (SIL OFL) candidates -> 3-check coverage gate (glyph-exists / distinctness round-trip / visual
    audit of contact_sheet.png). 27/30 PASS checks 1-2 (ptsans/rubik/karla lack precomposed VN);
    all 27 pass visual audit; SELECTED 18 diverse -> data/synth/fonts/fonts_manifest.json.
    (Fixed a false-fail: 30px distinctness tolerance exceeded a nạng dot -> lowered to 6px.)
  ☑ Corpus (engine/corpus): Source B = VinText TRAIN transcripts verbatim (p=0.65, firewall=train
    only, 25,774); Source A = wiki_vi (HF 20231101.vi rev b04c8d1) syllable freq bank (41,386 uniq /
    2.0M tok), case-augmented. Length/case targets MEASURED from train (99% single-tok, char med 3,
    case 68/16/22, 10% digit, 6.6% 1-char) — supersedes §4's '1-4 token' guess. Sampler matches within ~2pp.
  ☑ Generator (engine/render, bgpatches, imstats): render PASS font -> composite onto real train-scene
    bg patch (text-free, train-only, 5000) -> degradation in MEASURED §12 order (geometric->photometric
    ->resolution/blur). Per-sample cmap integrity (§2). ~4 ms/crop (=> 10k ~2min, 200k ~38min feasible).
  ☑ §7 distribution audit (engine/audit) PASS: synthetic reaches real's HARD tail on all 6 stats
    (sharpness/contrast/lum_mean/lum_std/height/bg_edge), centers within ~1 IQR, NONE systematically
    cleaner than real. Refined the verdict from a strict full-envelope test to §7's asymmetric stated
    intent (danger = 'synthetic cleaner than real'; benign under-reach of the EASY extreme is not a fail).
    -> FLAG THIS to brain at Gate A.
LAST DONE     : Stage 1 CER-decomposition (kill-test) + stratifications + detection probe.
                RESULT: CLAUDE.md §5 "diacritics dominate" CONJECTURE **REFUTED** — base-only subs 39.48%
                vs diacritic-only 16.12% of all edits (~2.5×). BUT three-axis metric VINDICATED: tone is
                the most fragile axis per-position (5.577% err vs base 4.881% case-insens); base is the
                largest total contributor (2.5:1 more positions, 32,267 vs 12,875). Only the decomposition
                shows both. Case LEAD resolved: 17.5% of base weakness was pure case; on case-insensitive,
                tone is the worst axis (as G2 predicted).
                REFUTED doc-predictions (do NOT target — DATA_ENGINE §12): hỏi↔ngã confusion is ABSENT
                (tone is DROPPED not confused → resolution/blur = mark visibility); NO horn-drop (horn is
                the BEST modifier); NO tone-cliff-at-small-size (base falls hardest; small text is general
                legibility).
                MEASURED priority (worst strata by CER): GEOMETRIC (tilt≥20° 30.3%) > PHOTOMETRIC
                (contrast<0.2 27.6%) > RESOLUTION/BLUR (height<12px 22.9%). Font coverage = correctness
                prerequisite, NOT the error driver. Recorded in DATA_ENGINE §12.
                BRAIN ADJUDICATIONS (2026-07-10):
                  • "Act on priorities while gold open?" -> YES. Ordering robust (gold only shrinks base
                    share; a flip needs >50% base errors = label noise, implausible). Stage 2 proceeds.
                  • "Fine-tune DBNet now?" -> NO, DEFER. §5 e2e does not block the rec-only flagship.
                    Off-the-shelf db_resnet50 (~48% F1) gives an UPPER bound on detection-induced error —
                    wrong side for the §7 decision, so producing no e2e number was the CORRECT call.
                DATA_ENGINE.md §12 (Stage-1 findings) added by brain. In repo.
STEP-1 BUG-CHECKS DONE (2026-07-11, this session; §8.2 — do NOT burn an attempt):
  (a) undertraining: val end-slopes (8-12k) baseline +.0058/+.0010/+.0013 vs gateA +.0079/+.0009/-.0006
      per-1k -> BOTH plateaued & comparable; dilution-undertraining weakly supported at best.
  (b) legibility: ~13/50 (~26%) synth crops illegibly OVER-DEGRADED (labels correct, signal destroyed)
      = training noise -> explains the 2.4x variance blow-up. (data/synth/_bugcheck_50.png)
  (c) labels: PASS — 0 non-NFC, 0 OOV over 10,000.
  (d) synth-test CER 16-17% (vs 9.4% real), exact 72-74% (vs 82%) -> model did NOT cleanly learn synth;
      illegible fraction is unlearnable noise. (scripts/bugcheck_synthtest.py)
  VERDICT: RED confounded by over-degradation noise (§8.2 HYGIENE defect, NOT yet the §8.3 transfer finding).
  HYGIENE FIX APPLIED (2026-07-11, commit): severity-budget in render.py — per-crop latent sev scales all
  heavy degradations coherently (mild-OR-hard, not all-maxed); glare/motion gated to high sev; low-contrast
  floored 0.42; defocus height-capped. Eyeball illegible ~26% -> ~6%; §7 re-PASS (still reaches hard tail).
  Regenerated set = data/crops/synth10k_leg (kept SEPARATE from the RED synth10k for provenance).
  HYGIENE RE-GATE DONE (k=3, synth10k_leg): STILL RED by the pre-registered rule, but HEALTHY.
    CER  base 9.381±0.368 -> leg 9.419±0.237 (Δ +0.038 FLAT, overlap)   [RED run was 9.521±0.895]
    tone base 94.410±0.281 -> leg 94.568±0.463 (Δ +0.158 improved, overlap)
    base +0.061, mod +0.135, exact +0.255, WER -0.125 -> ALL AXES NOW POSITIVE (were negative/flat).
    per-seed CER 9.320/9.427/9.510 (range 0.19 vs RED's 0.67).
    VARIANCE COLLAPSED: CER 95%CI ±0.895 -> ±0.237 (below baseline's own ±0.368) => bug-check (b) confirmed:
    illegible crops WERE the variance driver. Hygiene worked; it just does not clear the bar.
    => Empirically confirms §8.3's mechanism: marginal-matched synthetic reproduces real's RATE of hard crops
       (a rounding error vs the ~1,300 hard crops already in the 25.7k real). Covering marginals = necessary,
       NOT sufficient. This is exactly what Attempt 1 (over-represent the FAILURE STRATA) is for.
  ⛔ STOPPED AT BRAIN CHECKPOINT. Attempt 1 (§8.3) would spend 1 of only 2 budgeted attempts (§8.1) — the
  budget the brain locked to prevent p-hacking-by-iteration — so it is NOT started unilaterally even though
  pre-declared. AWAITING BRAIN DIRECTION (greenlight Attempt 1 as pre-declared, or adjust given the healthy RED).
  Attempt-1 plan is ready: re-weight generation toward tilt>=20deg, contrast<0.20, height<12px, 1-2 char crops.
NEXT ACTION   : 🧠 ATTEMPT-1 RED ADJUDICATED BY BRAIN 2026-07-11 (3rd checkpoint). Stage 2 at
                full-real is CLOSED — answered, not stuck. Moving to the pre-registered budget axis.
                ADJUDICATIONS:
                  • Comparator stronger-of-{A,B} PER METRIC: APPROVED (strictest, bar-raising reading).
                  • Attempt accounting CONFIRMED: 1 of 2 spent (B was a control; bug-checks free).
                  • ATTEMPT 2: HELD IN RESERVE, NOT spent. Budget = CEILING, not quota. No mechanism-backed
                    full-real hypothesis remains: scale→forbidden + refuted by learned-but-no-transfer;
                    renderer-jump→a new project, and C≈B says hard-crop realism isn't the bottleneck;
                    sequential-pretrain-slot→thin, the model already learns synth fine. Chasing a green at
                    full-real = the §8.1 p-hack. Reopen ONLY if the §14 curve surfaces a new mechanism.
                  • B−A tradeoff is a coherent PATTERN, not yet a claim: per-metric CIs overlap (A's CER CI
                    ±0.368 swallows B). It becomes a write-up claim only after step 1 below.
                  • FINDING (full prominence in every write-up): for a document-pretrained recognizer with
                    25.7k real crops, at matched augmentation, this synthetic engine adds NOTHING (C≈B) —
                    and "just augment harder" is itself a tradeoff, not a free win (B−A pattern).
                NEXT STEPS (in order):
                1) INS/DEL DECOMPOSITION (free, existing predictions.tsv, ALL arms A/B/C): count ins/del/sub
                   per arm. KEY: axes exclude INSERTIONS (CER-only) but deletions DO charge axes — so the
                   "axes up + CER up" B−A pattern points at INSERTIONS specifically. Verify before write-up;
                   if deletions drive it instead, restate the tradeoff.
                2) START the §14 budget axis per the FROZEN §14.1 spec (EVAL_PROTOCOL): r ∈ {10,25,50}%
                   nested fixed-seed subsets × {real-only, real+synth10k_leg} × k=3 = 18 runs (~9h).
                   r=100% REUSED (A + leg run). Default §6 config (NOT strata-aug). UNIFORM pooled sampling
                   (synth fraction growing as r shrinks IS the phenomenon). Full val-300 at every r; report
                   val-curve sanity per r (~150 real-epochs at r=10% real-only; best-val export guards).
                3) Deliverable: the LABEL-EFFICIENCY CURVE (gap vs r) + the pre-registered readout
                   "synthetic ≈ worth N real crops at budget r" (§14.1 interpolation rule). Per-point rule
                   unchanged: non-overlapping CI on CER AND tone. A green at r<100% is a label-efficiency
                   claim ONLY; the r=100% null keeps full prominence everywhere.
STEP-1 DONE (2026-07-11) — INS/DEL/SUB decomposition (free, existing predictions.tsv, k=3):
  arm   sub/100ch     del/100ch     ins/100ch    CER%
  A     6.806±0.326   1.461±0.239   1.114±0.116  9.381
  B     6.926±0.177   1.362±0.020   1.348±0.112  9.637
  C     6.848±0.064   1.365±0.114   1.407±0.130  9.620
  B-A: sub +0.121, del -0.099, ins +0.234, CER +0.256  => the regression is 92% INSERTIONS.
  MECHANISM CONFIRMED + SHARPENED: deletions IMPROVED, and deletions charge EVERY axis (a dropped
  char = all-axes-wrong) while insertions charge NONE -> that is exactly why axes rise as CER falls.
  Strata aug makes the model less willing to DROP a char (axes up) and more willing to HALLUCINATE
  one (CER/WER up). Write-up states INSERTIONS specifically, not vague "length errors". [commit]
  C-B: sub -0.079, del +0.004, ins +0.058, CER -0.017 -> nothing (consistent with the C≈B null).
STEP-2 IN FLIGHT — §14 BUDGET AXIS (per FROZEN §14.1):
  scripts/make_subsets.py: NESTED fixed-seed subsets, seed=20260711 (one shuffle -> prefixes;
    10 sub 25 sub 50 ASSERTED). r10=2,574 | r25=6,436 | r50=12,871 | r100=25,742 (reused).
  scripts/train_budget.py: arms real(r) vs real(r)+synth10k_leg (FROZEN, same set every r).
    §6 operating config: DEFAULT image_aug (NOT strata aug), fixed HP iters=12000, best-val on FULL
    val-300. UNIFORM pooled sampling (synth fraction 28%@r100 -> 79%@r10 = the phenomenon, not a confound).
    Verified at launch: r=10% real-only => ~149.2 epochs (matches §14.1's ~150 prediction).
  RUNS: 3r x 2 arms x 3 seeds = 18 (~9h). r=100% REUSED (real=baseline A; synth=the leg run).
  Batching 2 runs/launch (bg jobs get killed ~60-90min). Batch 1 = r10 real seeds 0,1 (bg b4plq0yfg).
  AGGREGATE (to write): scripts/aggregate_budget.py -> gap-vs-r curve + the PRE-REGISTERED readout
    "synthetic ~ worth N real crops at budget r" (§14.1: interpolate real-only curve linear in log r
    between MEASURED points, never extrapolate; N=(r'-r)x25,742). Per-point rule UNCHANGED:
    non-overlapping 95% CI on CER AND tone. A green at r<100% is a LABEL-EFFICIENCY claim ONLY;
    the r=100% null (C≈B) keeps FULL prominence everywhere.
  ✅ r=10% COMPLETE (k=3 both arms) — CIs NON-OVERLAPPING on BOTH CER and tone (per-point rule MET):
       real-only   CER 16.538±2.350  (17.622/16.108/15.883)   tone 89.336±1.704
       real+synth  CER 13.181±0.290  (13.062/13.185/13.295)   tone 91.987±0.099
       GAP         CER +3.357 pp                              tone +2.651 pp
     => At a SCARCE label budget the synthetic SUBSTITUTES for real labels — the §14 "gap widens as
        r shrinks" outcome. Coherent with §8.2(d): the model LEARNS synth fine; that knowledge is
        REDUNDANT with what 25.7k real crops already teach, so it only pays off when real data is thin.
     ⚠ LABEL-EFFICIENCY CLAIM ONLY, for r=10%. It does NOT rehabilitate the full-real null (C≈B).
        Per §14 the r=100% RED keeps FULL prominence. NEVER claimable: "synthetic improves Vietnamese OCR".
IN-FLIGHT     : §14 budget axis — r10 DONE (6/18). Now r25 real seeds 0,1. Then r25 synth, r50 both arms.
                Attempt 2 HELD IN RESERVE (not spent).
PARALLEL/LATER: (a) GOLD manual double-pass (2,437-instance sheet ready, empty) — needed before the FINAL
                curve numbers + the model-vs-label artifact (§4). NOT blocking Stage 2.
                (b) DBNet fine-tune -> e2e number (§5) — deferred; pipeline-completeness, not the flagship.
BLOCKERS/Q    : HOST: C: drive full (46 MB free); uv cache / TORCH_HOME / TMP / checkpoints -> E:.
NEXT 🧠 CHKPT : Gate A result (green/red + number + provenance). **THE gate.** Brain confirms green is real
                (non-overlapping CI) or reads the red diagnosis (DATA_ENGINE §8, geometric-first).
```

---

## How to use this plan

- **Read order at session start:** CLAUDE.md (auto-loaded) → this RESUME POINTER → the doc sections the
  current stage lists under *Obeys* (read only those, not all four docs — save context).
- **STATUS legend:** `☐ NOT STARTED` · `◐ IN PROGRESS` · `☑ DONE`.
- **🧠 BRAIN CHECKPOINT:** at these points STOP, report the number + full provenance to the user, and
  WAIT. Do not self-declare a gate green, do not start the next stage. The design brain (separate chat)
  adjudicates. These are Gate A and the final curve. (The on-device INT8 checkpoint is removed — Stage 4 is cut, see its tombstone.)
- **[VERIFY→FREEZE @ Stage N]:** resolve by **measuring**, then write the frozen value into the owning doc
  as a dated amendment. Never invent or estimate one and move on.
- **Never skip a stage or reorder.** Stage 1 (error analysis) before Stage 2 (engine) is load-bearing:
  the engine is built on the *measured* failure, not a guess (DATA_ENGINE §3, CLAUDE.md §9.3).
- **Git discipline:** commit after each step with the measurement in the message; keep negative results
  and reverted experiments in history (the sibling GPT-2 project's practice). If you are about to run low
  on context: write the RESUME POINTER, commit, THEN stop.

---

## Stage 0 — Environment + measurement harness + honest baseline  ☑
**Goal:** a working measurement rig and a real-only baseline, with every Stage-0 `[VERIFY]` measured and frozen.
**Obeys:** EVAL_PROTOCOL §1–§6, §11; CLAUDE.md §0, §9.1, §9.7.

- 0.1 Env: install `vietocr` (pbcquoc) with the **`vgg_transformer`** config + its public pretrained
  checkpoint; set up DBNet (needed for det/e2e later). Obtain **VinText** (1,200 / 300 / 500). *If the
  VinText source is unreachable from the sandbox network, STOP and ask the user — do not fabricate data.*
- 0.2 Confirm **pbcquoc pretraining is disjoint from the VinText test set** (EVAL_PROTOCOL §6 `[VERIFY]`);
  record the disjointness (and its evidence) in RESULTS.md. Overlap → contamination → escalate to brain.
- 0.3 Build the **eval harness** = EVAL_PROTOCOL made code: the three-axis diacritic scorer (NFD → base /
  modifier / tone, Levenshtein alignment, per-axis confusion matrices, §3.1), CER/WER/exact-match (NFC,
  §2), and det-only / rec-only / e2e scopes (§1). **Unit-test the scorer** on known strings (e.g. `ệ` →
  `e` + circumflex U+0302 + nặng U+0323; `ữ` → `u` + horn + tilde) before trusting any model number.
- 0.4 **Count the exact rec-only instance count of test-500 from the GT annotation** (resolves the "~14k"
  estimate — rec-only uses GT boxes, no DBNet needed). Record it; also the train-crop count.
- 0.5 **Real-only baseline:** fine-tune `vgg_transformer` on the full VinText-real train split, **k=3
  seeds**. Record rec-only CER + the three axes on real held-out (this is ERROR_ANALYSIS Run 0's input).
  Measure the **run-to-run std** across seeds → **freeze it as the Gate-A noise floor** (EVAL_PROTOCOL §7
  `[VERIFY]`).
- 0.6 **Gold set:** build the stratified sample (EVAL_PROTOCOL §5: instances, over-sample diacritic-dense /
  small / low-contrast) and a transcription helper. *NOTE: the codepoint-by-codepoint double-pass is the
  USER's manual work — prepare the tooling + sample; do not fabricate gold labels.* Freeze the exact gold
  instance count once the sample is fixed (EVAL_PROTOCOL §5 `[VERIFY]`).

**Exit gate:** scorer passes self-tests · baseline CER + 3-axis in RESULTS.md · all Stage-0 `[VERIFY]`
frozen via dated amendments · disjointness confirmed.
**🧠 BRAIN CHECKPOINT:** report baseline numbers + the frozen noise floor before Stage 1 interpretation.

---

## Stage 1 — Error analysis Run 0 → the engine's priority list  ☐
**Goal:** the ranked failure profile of the real-only baseline that tells the engine what to generate.
**Obeys:** ERROR_ANALYSIS (all) — especially §3 (three-axis + CER decomposition), §4 (gold cross-check),
§5 (det-vs-rec + e2e ceiling), §6 (stratifications), §7 (findings→priorities).

- Three-axis breakdown + **CER decomposition** (the pure-tone-error share — the quantitative G2 finding) +
  per-axis confusion matrices (§3).
- **Model-vs-label** disentanglement via the gold subset (§4) — do not charge label noise to the model.
- **Det-vs-rec** attribution (e2e − rec-only) and the stated **e2e ceiling** (§5).
- **Stratifications** (§6): crop-height / small-text (the Tone-axis-vs-height curve), contrast, length,
  orientation, stylized-vs-plain.
- Produce the **findings→priorities mapping** (§7): each failure → one DATA_ENGINE knob.

**Exit gate:** ERROR_ANALYSIS Run 0 filled · a ranked priority list (axis / stratum / knob) exists.
**🧠 BRAIN CHECKPOINT:** report the priority list — is diacritics the dominant class (CLAUDE.md §5
`[CONJECTURE]`), or is it detection / small-text? The engine's design forks on this.

---

## Stage 2 — Synthetic engine v0 + Gate A @ 10k  ☐
**Goal:** a domain-transfer generator whose 10k output passes Gate A on real held-out.
**Obeys:** DATA_ENGINE (all); EVAL_PROTOCOL §7 (Gate A), §10 (contamination).

- Corpus: `wiki_vi` + VinText **train-split** labels, scene-leaning, case-augmented (§4). *Corpus draws
  from train labels ONLY — never val/test (§10).*
- Font pipeline: Google Fonts (SIL OFL); the **3-check coverage verification** (glyph-exists /
  distinctness-round-trip / visual-audit) → 15–20 clean fonts; per-font verdict → manifest (§5).
- Degradation model: build the groups **in the priority order from Stage 1** (§6).
- Generate 10k → **distribution audit BEFORE training** (§7: synthetic must COVER real on
  sharpness/contrast/resolution) → fine-tune on top of the baseline → **Gate A** (EVAL_PROTOCOL §7).
- **Time the full 10k loop** (generate→train→eval) = the compute-feasibility probe for 200k.

**Exit gate:** Gate A GREEN → Stage 3. Gate A RED → **STOP**, run the re-diagnosis loop (DATA_ENGINE §8:
ranked axes, degradation-first, ONE fix), **re-gate at 10k**. Do NOT scale on red.
**🧠 BRAIN CHECKPOINT:** report Gate A result (green/red + number + provenance). The brain confirms green
is real (non-overlapping CI, EVAL_PROTOCOL §7) or reads the red diagnosis. **This is THE gate.**

---

## Stage 3 — The scaling curve (flagship)  ☐
**Goal:** the accuracy-vs-synthetic-count curve on real held-out, honest shape, mechanism validated.
**Obeys:** SCALING (all); EVAL_PROTOCOL §4, §6.

- **Freeze generator v1** (Gate-A-green config). The curve varies **count only** against v1 (§2). A later
  generator change = a NEW curve, never a mixed point.
- Run **10k / 50k / 200k** (+ optional intermediate points at k=1, labeled single-seed) — anchors at
  **k=3**. Rec-only CER + **Tone-axis** + **small-text per-axis** (§1, §5); **e2e alongside**.
- **Inter-point gain only if the CIs do not overlap** (§4) — otherwise "plateau", not "still rising".
- Fill the **per-point manifest** (§8) and produce the **ERROR_ANALYSIS before/after per-axis table** (§9).

**Exit gate:** the curve + the before/after table · an honest shape statement (rising / plateau /
help-then-hurt — all are results).
**🧠 BRAIN CHECKPOINT:** report the curve shape + headline number + provenance. Brain checks the honest
headline sentence (domain-transfer framing) and that the per-axis mechanism actually moved (§5).

---

## Stage 4 — On-device (INT8 + Apple Vision)  ✂️ CUT — deferred to future work
**Decision [2026-07-10]:** cut per **CLAUDE.md §0 L3 pre-registered cut-order** ("Cut order if time runs
short: drop (c) first"). Rationale: on-device INT8 + Core ML export + Apple Vision benchmark is *execution
of a known-good playbook, not novelty* (CLAUDE.md L3c), and it is **redundant** with the sibling C/CUDA
GPT-2 engine, which already carries the edge-inference / quantization / batch=1-INT8 signal. The project's
senior-signal contribution is the **data engine + honest evaluation** (L3b); keeping the portfolio as two
*distinct* deep signals (systems/inference in GPT-2, data-centric/evaluation here) beats two that both
touch on-device INT8. **This is recorded, not silently deleted** — the same discipline as keeping reverted
experiments in git history.

**Retained as future-work spec (NOT executed):** EVAL_PROTOCOL §8–9 (INT8 quality+speed gates, Core ML
dispatch, Apple Vision per-axis firewalls) and CLAUDE.md §11 A2. The write-up (Stage 5) frames on-device as
explicit future work and points the edge-inference signal to the sibling engine.

**The cut is NARROW — it does not touch e2e/detection.** DBNet + the det-vs-rec attribution (ERROR_ANALYSIS
§5) and the e2e-alongside numbers **stay**: they are "the pipeline works" (L3a), not the on-device stage.
Technical work now terminates at **Stage 3** (the scaling curve); Stage 5 is the write-up.

---

## Stage 5 — Write-up  ☐
**Goal:** the portfolio artifacts.
**Obeys:** CLAUDE.md §8 (finishing); RESULTS.md.

- Finalize **RESULTS.md** (the measured-evidence ledger: CER/WER/3-axis/det-F1@IoU/scope/splits per run).
- Portfolio README in the **sibling GPT-2 doc style** (numbers with provenance, negative results kept,
  gap honestly explained), with **on-device deployment scoped as explicit future work** (the edge-inference
  signal is carried by the sibling GPT-2 engine — Stage 4 tombstone).
- Final consistency pass: every doc's numbers vs CLAUDE.md and each other; no locked value silently edited.

**Exit gate:** RESULTS.md complete · README done · docs mutually consistent.

---

## Cross-cutting invariants (true at every stage)
- Real held-out is the only test that counts; synthetic-test accuracy is never a result (EVAL_PROTOCOL §6, SCALING §6).
- Every number: real held-out + scope + NFC + three-axis + reproducible manifest — or it is not a result.
- One change at a time; revert changes without a clean, noise-clearing gain.
- Never edit a `[LOCKED]` threshold to match a result; a breach is a finding (EVAL_PROTOCOL §12).
- If you believe a locked decision is wrong, FLAG it to the user (→ brain) — do not act on it yourself.