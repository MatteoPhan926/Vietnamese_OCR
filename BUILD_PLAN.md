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
CURRENT STAGE : Stage 1 — Error analysis Run 0.  (Stage 0 ☑ and BRAIN-ADJUDICATED 2026-07-10.)
LAST DONE     : Stage-0 🧠 brain checkpoint PASSED. Baseline + noise floor accepted; adjudications below.
                REAL-ONLY BASELINE (rec-only, test-500, NFC/axes NFD, n=10,068/37,254, k=3):
                  CER 9.395% (std 0.148pp) | base 94.081% | modifier 96.207% | tone 94.423% (std 0.113pp)
                  WER 19.307% | exact 81.943%.  Gate-A noise floor FROZEN (§13 E11): CER std 0.148pp,
                  tone std 0.113pp  =>  a synth run needs CER improvement ~>=0.7pp AND tone movement to
                  clear §7's non-overlapping-CI rule.
                BRAIN ADJUDICATIONS (2026-07-10):
                  • E2 / E8 / E10 freezes + insertion-handling (CER-only, no axis denominator): APPROVED.
                  • E9 disjointness: APPROVED POSTURE — write "no contamination detected by a zero-shot
                    probe", NEVER "verified disjoint". Lean on DOMAIN-disjointness (document pretrain vs
                    scene test) as PRIMARY; the zero-shot probe is weak, direction-ambiguous corroboration.
                  • Base case-sensitivity: keep BOTH; case-INSENSITIVE is the reference for axis-weakness.
                  • The [LEAD] (base weakest by axis accuracy) is NOT settled — see NEXT ACTION.
                ERROR_ANALYSIS.md is now IN REPO (brain delivered it). CLAUDE.md amendments A1–A4 applied.
                Stage 1 §3 (axes, CER decomposition, confusions, per-class) DONE and §6 (stratifications) DONE.
                ERROR_ANALYSIS.md "RUN 0 REPORT" + RESULTS.md Stage-1 section filled.

                *** THE KILL-TEST ANSWER: CLAUDE.md §5's "diacritics dominate" is REFUTED. ***
                  base-only subs 39.48% of all edits vs diacritic-only 16.12% (~2.5x).
                  BUT tone is still the LEAST ACCURATE axis (err 5.577% vs base(ci) 4.881%) — base
                  positions outnumber tone-bearing 2.5:1 (32,267 vs 12,875). The three-axis metric
                  is what made BOTH facts visible; it is vindicated, not undermined.
                  Also refuted: hoi<->nga confusion is ABSENT (4 and 4) — tone fails by DROP (215) +
                  HALLUCINATION (174), not shape confusion (199). Horn is the BEST modifier (2.87%),
                  not the predicted "horn drop"; breve is worst (11.16%). Tone does NOT fall off a
                  cliff at small size relative to base — base falls hardest (-11.4pp vs -10.0pp).
                  Worst strata: tilt>=20deg CER 30.34% | contrast<0.20 27.55% | 1-char 25.89% |
                  height<12px 22.86%. Base is the worst-hit axis in all but 1-char.
                  PROVISIONAL priority: degradation realism, GEOMETRIC first, then photometric, then
                  resolution/blur. NOT the font-coverage/stacked-diacritic curriculum anticipated.
NEXT ACTION   : Close the two open [LOCKED] sections, then the priority list is final:
                  A. §5 det-vs-rec: DBNet INSTALLED + det evaluator BUILT (scripts/detect_eval.py:
                     polygon IoU, ### = don't care per E2). BLOCKED on FINE-TUNING: off-the-shelf doctr
                     db_resnet50 (English-trained) scores only F1@0.5 ~= 48% on VinText, and input size
                     is RULED OUT as the cause (48.0% @1280, 48.0% @1600, 41.6% @2048). Using it for the
                     attribution would manufacture a false 'detection is the bottleneck' finding and
                     redirect the whole engine. NEXT: fine-tune DBNet on the VinText TRAIN split only,
                     then measure e2e CER - rec-only CER and state the e2e ceiling.
                  B. §4 gold cross-check: BLOCKED on the USER's manual double-pass of the 2,437-instance
                     sheet (data/gold/transcription_sheet.tsv; gold_pass1/gold_pass2 are empty).
                Then STOP at the brain checkpoint with the FINAL ranked priority list.
IN-FLIGHT     : none.
BLOCKERS/Q    : (1) 🧠 §4 gold cross-check BLOCKED — gold labels do not exist; NOT fabricated. Every Run-0
                    number is public-label = model error + label error, ENTANGLED. Label noise inflates
                    base errors + insertions specifically, so the 39.48% base share is an UPPER BOUND.
                    The kill-test must be re-run against gold before it is treated as settled.
                (2) §5 OPEN: DBNet is installed + the det evaluator is written, but the detector is NOT
                    fine-tuned on VinText (F1@0.5 ~= 48%, a real domain gap, not a resolution artifact).
                    NO e2e/attribution number is reported: an un-fine-tuned detector is a LOWER BOUND on
                    detection, so its e2e gap is an UPPER BOUND on detection-induced error -- useless for
                    the decision §7 needs. e2e ceiling remains UNSTATED. Fine-tune on train split first.
                (3) §6 stylized-vs-plain BLOCKED, not dropped: VinText ships no style annotation and no
                    defensible proxy exists without one.
                (4) HOST: C: drive full (46 MB free); uv cache / TORCH_HOME / TMP / checkpoints -> E:.
NEXT 🧠 CHKPT : end of Stage 1 — the FINAL ranked priority list (after §5 closes). The kill-test answer
                above (REFUTED) is the headline; the engine's design forks on it. Brain must also rule on
                whether the priority list may be acted on while §4 (gold) is still open.
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

## Stage 1 — Error analysis Run 0 → the engine's priority list  ◐
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
