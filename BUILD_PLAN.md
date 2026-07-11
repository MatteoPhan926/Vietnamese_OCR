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
STEP-0 DONE (2026-07-11, §8.4 + §8.2d) — committed:
  (i) [VERIFY->RESOLVED] installed vietocr image_aug = ImgAugTransformV2 (albumentations 2.0.8):
      InvertImg p.2 | ColorJitter p.2 | MotionBlur blur_limit(3,3) p.2 | RandomBrightnessContrast +-0.2 p.2
      | Perspective scale(0.01,0.05) p.5 | RandomDottedLine p.5.
      ABSENT: rotation, shear, gaussian blur, NOISE, JPEG, downsample/resolution.
      => FINDING: partially REFUTES §8.4's "largely redundant" premise. BUT §8.4's DESIGN gets STRONGER:
         baseline is UNDER-AUGMENTED on exactly the measured failure strata -> arm B has big headroom;
         §15's raised comparator is essential. No [LOCKED] decision invalidated (§8.4 branched on this).
  (ii) §8.2(d) THE FINDING: model LEARNED synthetic decisively but it DOES NOT TRANSFER.
      held-out synth (n=2000): baseline CER 26.4% -> leg 16.0% (-39% rel), exact 58.4->74.2, tone 80.6->88.6,
      while REAL test CER stayed FLAT (9.381 -> 9.419). Data/pipeline fine; TRANSFER is the failure.
STEP-1 IN FLIGHT (Attempt 1 of max 2, as the §8.4 THREE-ARM experiment; B is a CONTROL, not an attempt):
  engine/strata_aug.py = StrataAugment: manufactures the measured strata FROM REAL CROPS (perspective+shear
    +rotation / contrast crushed <0.20 / downsample 8-12px), one stratum at a time, ON TOP of the exact
    default aug (arm B = strict SUPERSET of A's aug; bar RAISED never lowered). SAME augmentor in B and C.
    Measured on real crops: contrast<0.20 6.3%->23.3%, sharpness<200 9.7%->28.7%.
  data/crops/synth10k_strata = §8.3 strata-targeted synth (over-represent strata, NOT marginal-match;
    corpus short_rate 0.20). Legibility guard (§8.2 lesson): first pass sev .35-.75 gave ~50% illegible ->
    stratum carries difficulty, rest MILD (sev .05-.30). Objective: baseline-model CER 41.8%/exact 43%
    (vs leg 27.6%/57.5%) = +14pp over the synthetic domain gap, in line with real strata (+13..+21pp).
    HARD-BUT-LEARNABLE, not noise.
  RUN: scripts/train_arm.py --arm B|C --seed {0,1,2}; FIXED HP iters=12000; rec-only test-500 frozen denom.
  AGGREGATE: B-A = what augmentation alone buys. C-B = PURE synthetic contribution at matched augmentation.
    JUDGE C AGAINST B (§15). Outcomes: C>B = synth adds what aug cannot; C~B>A = "just augment harder"
    (strong negative result); C~B~A = strata resist both -> EVAL_PROTOCOL §14 label-efficiency axis.
  STATUS: arm B seeds 0,1 launched (bg br523cmoj). Then B seed2, then C seeds 0,1,2. ~30 min/run.
  NOTE flagged to brain: crops are perspective-RECTIFIED by crop_quad at BOTH train and test, so a literal
    >=20deg rotation is not what the model ever sees; "geometric" is manufactured as strong perspective+
    shear+moderate rotation (residual distortion). C-B is robust to this choice since B and C share the aug.
NEXT ACTION   : 🧠 HYGIENE RE-GATE ADJUDICATED BY BRAIN 2026-07-11 (2nd checkpoint).
                VERDICT: the legibility fix WAS legitimate hygiene, NOT a re-gate attempt (0 of 2 spent).
                  Reason it is principled: §8.2 PREDICTED the signature (illegible crops = noise = inflated
                  seed variance). The fix removed exactly that signature: CER CI +/-0.895 -> +/-0.237, now
                  TIGHTER than the baseline's own +/-0.368. A falsifiable prediction, confirmed.
                RED still correct: CER delta +0.038 (noise). BUT the picture CHANGED materially — all five
                  non-CER metrics moved positive (WER -0.125, exact +0.255, base +0.061, mod +0.135, tone
                  +0.158 with 3/3 seeds positive). Synthetic is no longer HARMFUL, only INSUFFICIENT.
                  Checked and recorded: even a PAIRED test (more powerful than the pre-registered rule)
                  fails — CER t=+0.46, tone t=+2.05 vs t_crit 4.30 (2 dof). The conservative rule is NOT
                  what produced the RED. (Rule NOT changed — that would be goalpost-moving.)
                *** THE BRAIN'S OWN MISS, now locked as DATA_ENGINE §8.4: the AUGMENTATION CONFOUND. ***
                  The baseline runs image_aug=True — vietocr already applies blur/motion-blur/noise/JPEG/
                  perspective/affine TO THE REAL CROPS every epoch. So the degradation model (§6) is largely
                  REDUNDANT with an augmentation pipeline the comparator already has — and a REAL crop
                  degraded hard beats a RENDERED crop degraded hard. This explains the flatness better than
                  any ranked §8 suspect, and no doc caught it.
NEXT STEPS (in order):
                STEP 0 (free, DATA_ENGINE §8.2d + §8.4):
                  (i) VERIFY what image_aug actually applies in the installed vietocr (exact transform list
                      + strength ranges) -> record in the manifest. Do NOT assume.
                  (ii) Score the leg model on HELD-OUT SYNTHETIC (the one §8.2 check never run). Learned
                      synth but real flat => data is fine, it DOES NOT TRANSFER = the real finding. Didn't
                      learn synth => still broken.
                STEP 1 — ATTEMPT 1 APPROVED (1 of max 2), but as a THREE-ARM experiment (§8.4), k=3 each:
                  A = baseline (real + default aug) — HAVE IT.
                  B = real + STRATA-TARGETED AUGMENTATION, NO synth (tilt>=20deg, contrast<0.20, height
                      <12px manufactured FROM REAL CROPS). *** B is a CONTROL, not an attempt. ***
                  C = real + same strata-targeted aug + STRATA-TARGETED SYNTHETIC (§8.3).
                  JUDGE C AGAINST B, NOT A. B-A = what augmentation alone buys. C-B = the PURE synthetic
                  contribution at matched augmentation — the only honest answer to "was generating the
                  synthetic worth it?" Comparing C to an under-augmented A is a STRAWMAN (EVAL_PROTOCOL §15:
                  the comparator is the STRONGEST real-only config; the bar may be RAISED, never lowered).
                  Every outcome is a finding: C>B = synth adds what aug cannot; C~B>A = "just augment
                  harder" (strong negative result); C~B~A = the strata resist both -> go to §14.
                STEP 2 — if Attempt 2 also RED: finding = "10k synthetic gives no lift at full real data"
                  (reported at FULL prominence), then the PRE-REGISTERED real-data-budget axis
                  (EVAL_PROTOCOL §14): r in {10,25,50,100}% real x {with,without} synth -> label-efficiency
                  curve. Reserved in §6 BEFORE Stage 0 — a contingency, NOT a post-hoc rescue.
                STILL LOCKED (SCALING §2): the curve needs a WEIGHTED SAMPLER holding per-batch real:synth
                  ratio FIXED. Uniform pooled sampling at fixed iters => 200k synth = 89% of every batch
                  (real collapses ~15 -> ~1.5 epochs); the curve would measure its own sampler.
IN-FLIGHT     : none. All 3 Gate-A seeds complete; engine v0 + Gate-A scripts committed.
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