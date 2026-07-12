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
NEXT ACTION   : 🧠 C1/C2 ADJUDICATED BY BRAIN 2026-07-12 (5th checkpoint). Verified independently:
                worth-point reproduces (N=2,195 under §14.1 with the k=5 anchor); daylight 1.75pp real.
                  • Q1 ACCEPTED: the claim NARROWS TO r=10% (single point). r=25% recorded at full
                    prominence as "directionally positive under strict (CER +0.752, separated) but below
                    the pre-registered two-metric bar (tone overlaps)" — NOT "bank-carried": bank cost is
                    uniform ~16-20% at BOTH points (EVAL_PROTOCOL §14.3). Green dies in (10%,25%].
                  • Q2 NO: die-off mapping (r=15/20%) deferred — new axis, not a closure; optional
                    post-write-up polish, pre-registered if ever run.
                  • t(dof) fix RATIFIED (no prior number affected — all earlier runs k=3).
                  • N-RANGE CORRECTED (§14.3): both-arm corner propagation -> ≈ +2.2k, range [1.68k,2.55k].
                    The quoted [2,095..2,297] under-propagated (anchor held fixed). Use the wide range.
                QUEUE:
                1) C4 NOW (analysis-only, free — predictions.tsv for both k=5 arms exist): ERROR_ANALYSIS
                   §8 per-axis before/after at r=10%, real-only(k=5) vs strict-synth(k=5): which axes and
                   strata carry the +2.78pp? Tone/small-crops = mechanism confirmed; uniform = generic-
                   prior story. The curve without this is half a result (SCALING §9).
                2) C3 GOLD = the USER's manual double-pass (2,437-instance sheet) — now THE critical path;
                   all remaining GPU work is done or analysis-only.
                3) Stage 5 write-up draft after C4, gold slots marked pending.
§14.3 AMENDMENTS APPLIED (2026-07-12, this session):
  • N-range CORRECTED to both-arm corner propagation (aggregate_budget.worth). Headline now
    ≈ +2,195, both-arm 95% range [+1,678 .. +2,553] — REPRODUCES the brain's [1.68k, 2.55k] exactly.
    The old synth-only [+2,095..+2,297] held the anchor fixed and UNDER-propagated -> superseded,
    marked [SUPERSEDED] in RESULTS rather than quietly deleted. Point estimate unchanged.
  • r=25% FRAMING CORRECTED in RESULTS + SCALING + the aggregator. My earlier wording ("substantially
    carried by label-derived text the budget did not entitle it to") OVER-READ the numbers and is
    RETRACTED IN PLACE. Correct record: bank cost is uniform ~16-20% at BOTH green points; r=25% is
    directionally positive under strict (CER +0.752, separated) but BELOW the two-metric bar (tone
    overlaps). Green dies in (10%, 25%].
  • t(dof) fix ratified (no earlier number affected — all prior runs were k=3).

C4 ✅ COMPLETE (2026-07-12) — THE MECHANISM, and it is NOT the one the engine was built for.
  scripts/c4_before_after.py -> runs/c4_before_after_r10.json. Analysis-only (k=5 predictions existed).
  BEFORE real-only(r10) k=5 vs AFTER +strict-synth k=5. Question pre-stated (tone/small/tilted =
  mechanism confirmed | uniform = generic prior). ALL THREE AXES move ~equally:
    CER +2.783±0.938 | base +1.605±0.577 | modifier +1.808±0.678 | tone +2.033±0.655  (all clear noise)
  1,037 chars fixed. WHERE THE GAIN LIVES (share of those 1,037):
    tilt>=20deg (DATA_ENGINE §12 RANK-1 driver): +1.60±1.94 -> DOES NOT CLEAR NOISE, only 2.8% of gain.
    tilt<5deg (the EASY, common case): 77.1% of the gain.  height>=48px: 20.4%.
    LONG CROPS (>=9 chars, only 296/10,068 instances): 54.3% OF THE ENTIRE GAIN. Length was NEVER a
      targeted knob (synth corpus is 99% single-token, median 3 chars).
  MECHANISM MEASURED (not inferred): the scarce-budget decoder TRUNCATES. On >=9-char crops, mean pred
    length 8.37 vs GT 11.19, 24.7% severely truncated -> with synth: 10.25, 6.9%. Premature <eos> on
    long strings (phone numbers/URLs). A DELETION charges EVERY axis -> that is exactly why all three
    axes rise together instead of tone alone.
  => Lands on the GENERIC-PRIOR side of the pre-stated fork: "at a scarce budget, more crops of almost
     any kind fix decoder under-training." The +2.783pp is REAL (survives strict + k=5), but this
     WEAKENS the domain-transfer/realism-knobs framing. LIVE THREAT: a cheap non-scene control (same
     10k rendered WITHOUT the degradation stack) might buy much of the same gain. NOT RUN — brain's call.
IN-FLIGHT     : none. GPU free.
PARALLEL/LATER: (a) GOLD manual double-pass (2,437-instance sheet ready, empty) — needed before the FINAL
                curve numbers + the model-vs-label artifact (§4). NOT blocking Stage 2.
                (b) DBNet fine-tune -> e2e number (§5) — deferred; pipeline-completeness, not the flagship.
BLOCKERS/Q    : HOST: C: drive full (46 MB free); uv cache / TORCH_HOME / TMP / checkpoints -> E:.
NEXT 🧠 CHKPT : ⬅ **NOW (6th).** C4 is done and it CHANGES THE STORY. Reported, NOT adjudicated.
                THE ONE THING THE BRAIN MUST RULE ON:
                  The +2.783pp is REAL (survives the strict bank AND k=5; all three axes clear noise).
                  But the MECHANISM is NOT domain transfer: 54.3% of the gain is long-crop TRUNCATION
                  repair (a decoder under-training effect), the rank-1 targeted stratum (tilt>=20deg)
                  shows NO significant gain (+1.60±1.94) and carries 2.8%, and 77% of the gain sits in
                  the EASY tilt<5deg bin. On the PRE-STATED fork this is the GENERIC-PRIOR branch, not
                  "the realism knobs worked."
                  Q: does the write-up (a) claim LABEL-EFFICIENCY ONLY and drop the domain-transfer
                  mechanism claim; or (b) spend ~1h GPU on the CONTROL that decides it — regenerate 10k
                  with the DEGRADATION STACK OFF (clean renders; same corpus/fonts/strict bank/seed)
                  and retrain at r=10%, k=3? If the clean control buys most of the +2.78pp, the
                  engine's realism machinery is NOT what paid and the write-up must say so; if it does
                  not, the degradations ARE load-bearing and the domain-transfer claim survives.
                  The control is a NEW RUN (pre-registerable), so it is NOT started unilaterally.
                (Gate A RED: adjudicated. Attempt-1 RED: adjudicated. §14 curve: adjudicated -> C1-C4.
                C1+C2: adjudicated 2026-07-12 -> §14.3 applied. This checkpoint is C4.)
                THEN: C3 gold double-pass (USER's manual work — the remaining critical path) + the
                Stage-5 write-up with gold slots marked pending.
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