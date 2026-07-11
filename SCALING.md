# SCALING.md — the flagship artifact (a curve whose honesty is auditable, or it is a confident lie)

> **What this file is.** The record of the deliverable: the **accuracy-vs-synthetic-count scaling curve
> on real VinText held-out**. A **sibling of EVAL_PROTOCOL / DATA_ENGINE / ERROR_ANALYSIS** — it is the
> *output* of all three, so it inherits their locks and adds the ones specific to a curve. Same
> character, stated sharpest here: **a scaling curve measured on the wrong test set, or with the
> generator changing between points, or reading noise as signal, is worse than no curve — it is a
> confident lie.** This file exists so every point is reproducible and every claim about the curve's
> *shape* survives an auditor who assumes it is fake until the manifest proves otherwise.

---

## §1. What the curve is (exactly)

- **`[LOCKED]` X-axis:** synthetic count — pre-registered anchors **10k → 50k → 200k** (CLAUDE.md §4).
  Intermediate points (e.g. 25k, 100k) **may** be added to resolve shape (cheap once the pipeline exists),
  under the same frozen generator (§2).
- **`[LOCKED]` Y-axis (headline):** **rec-only CER** on the **rec-only instances of the real VinText
  test-500** — exact count read from the GT annotation at Stage 0 (rec-only uses GT boxes; **~14k
  estimated**, not measured — EVAL_PROTOCOL §4) — instance-count, never image-count.
- **`[LOCKED]` Y-axis (co-plotted, the thesis):** **Tone-axis accuracy** at each point (EVAL_PROTOCOL
  §3.1). A CER curve alone cannot show whether the gain is the *scene-robustness* the engine claims (§5).
- **`[LOCKED]` X=0 anchor:** the **real-only baseline** (pretrained + full VinText-real, no synthetic,
  EVAL_PROTOCOL §6). Every "+X%" on this curve is measured against this anchor, and its meaning is
  domain-transfer value (§7).
- **`[LOCKED]` Every point = median + spread over k=3 seeds** (EVAL_PROTOCOL §3). The spread is plotted,
  not hidden — it is what §4 uses to decide whether an inter-point gain is real.

---

## §2. Everything-else-fixed (Firewall 3) — including the generator, which is the subtle one

The curve varies **only** synthetic count. Fixed across all points: the backbone (`vgg_transformer` —
locked with rationale in EVAL_PROTOCOL §6, *not* merely implied by CLAUDE.md L1), hyperparameters, **the
real-data amount (full train split)**, and this evaluation protocol.

**`[LOCKED]` The sampler — and why the naive protocol is FATAL at 200k (added 2026-07-11).** With a fixed
iteration budget and **uniform sampling over the pooled (real + synthetic) set**, the synthetic fraction of
every batch grows with the synthetic count: 10k synth on 25.7k real is ~28% synthetic, but **200k synth is
~89%** — real data would collapse from ~15 epochs to **~1.5** at the same compute. The curve would then
decline for a reason that has nothing to do with the data's quality: **the protocol would be starving the
real data, and the curve would be measuring its own sampler.** So every curve point is run with a
**weighted sampler holding the per-batch real:synth ratio FIXED** (at the Gate-A-green config's ratio),
varying only the **size of the synthetic pool**. That isolates the question the curve actually asks —
*does more UNIQUE synthetic data help?* — with real-data exposure and compute both constant. A curve run
under uniform pooled sampling at high synth counts is not a data result.

**`[LOCKED]` The generator config is FROZEN at the Gate-A-green configuration ("v1"), and the curve
varies count only against it.** This is Firewall 3 applied to the engine, and it is the honesty firewall
a sharp reviewer probes first:

- The Gate-A / re-diagnosis loop (DATA_ENGINE §8) runs **at 10k** and improves the generator until green.
  That produces the **frozen v1 config** (fonts + verdicts, corpus mix, degradation params).
- The curve (10k/50k/200k) then uses **v1, unchanged**. Improving the degradation model *and* increasing
  count at the same time confounds "more data" with "better data" and voids the curve.
- **`[LOCKED]`** A later generator improvement ("v2") produces a **new curve**, never a point mixed onto
  the v1 curve. Comparing the v1 and v2 curves is itself a finding (a better generator shifts the curve),
  but no single curve ever contains two generator configs.

---

## §3. The Gate-A record (provenance — the curve was not scaled until it earned it)

**`[LOCKED]`** SCALING.md records the Gate-A history, so the reader sees the curve was gated, not
assumed:

- Was Gate A **green at the first 10k**, or did it take **re-diagnosis iterations** (DATA_ENGINE §8)?
- For each RED iteration: which ranked axis was the cause (degradation realism / font-background / corpus /
  domain-fundamental) and what one thing was fixed.
- The frozen v1 config the green gate produced.

Slot to fill: *"Gate A resolved GREEN at 10k after N re-diagnosis iterations; the curve below uses the
resulting v1 generator."* If Gate A never went green, **there is no curve** — the deliverable is the RED
diagnosis (DATA_ENGINE §8), reported honestly, and the engine needs better domain randomization before
scale.

---

## §4. Reading the shape honestly (all three shapes are results; noise is not signal)

The curve's **shape is the finding** (CLAUDE.md §5). Pre-register that **all** of these are reportable
outcomes, none a failure to bury:

- **Still rising at 200k** → headroom remains; strong and honest. Do **not** extrapolate past 200k (scope).
- **Plateau** → the engine's value is bounded; **an honest plateau is a strong result** — it states
  exactly what the engine buys.
- **Help-then-hurt** (declines at high count) → synthetic begins to hurt (distribution drift / synthetic
  artifacts dominating real signal). A real finding about the synth-real gap, reported, not hidden.

**`[LOCKED]` The inter-point rule (this is where fake curves are made).** A gain from one point to the
next is claimed **only if it clears the seed spread** — the same noise-floor discipline as Gate A
(EVAL_PROTOCOL §7). If 50k→200k improvement is within the k=3 spread, the honest statement is **"plateau
by 50k; 200k not resolvably better,"** never "still rising." Report the **marginal gain per point** with
its spread; overlapping error bars mean the difference is unresolved at this seed count, stated plainly.

> **`[LOCKED]`** The curve on **real** data is the deliverable **regardless of shape.** A flat or
> declining real-data curve is a **true result**, not a null result to hide. The failure mode is not a
> disappointing shape; it is a *pretty* shape that is not real.

---

## §5. Per-axis curves — validating the mechanism, not just the outcome

The thesis (DATA_ENGINE §1) is that the gain is **scene-robustness** on top of a prior that already reads
clean text. So the curve reports **per-axis-vs-count**, not only CER:

- **`[LOCKED]` Tone-axis accuracy vs count** and **small-text error vs count** (crops below the ERROR_ANALYSIS
  §6 height threshold). If the engine is doing what it claims, these improve as count rises.
- **`[LOCKED]` The mechanism cross-check:** if **CER improves but Tone-axis-on-small-crops does not**, the
  gain is **not** the domain-transfer we claimed — it is coming from somewhere else (e.g. overall exposure),
  and the headline sentence (§7) must be corrected to match what actually moved. A CER-only curve cannot
  catch this; the per-axis curve is what keeps the *mechanism* claim honest, not just the *outcome* claim.

---

## §6. The synthetic-test-accuracy trap (named so it is never reported as a result)

**`[LOCKED]`** More synthetic **trivially** raises **synthetic**-test accuracy — that curve is circular
and worthless (EVAL_PROTOCOL Firewall 3). It is **never** the deliverable. If a synthetic-test number is
shown at all, it is **only** as a labeled training-sanity check ("training is converging on its own
distribution"), visually and textually separated from the real-data curve, never plotted as the result.

---

## §7. The honest headline sentence, and what the curve does / does not license

**`[LOCKED]` Headline** (EVAL_PROTOCOL §6): *"+X% CER on real VinText held-out (rec-only) from the
synthetic scene-text engine, on top of a document-pretrained VietOCR fine-tuned on VinText-real"* — where
**X% is the gain from the X=0 anchor to the curve's resolved best point** (§4), not to whichever point
looks highest before noise. Attribution is **domain-transfer value**, not "from scratch."

Does **not** license: an **e2e** promise (this is rec-only; the e2e ceiling is set by detection,
ERROR_ANALYSIS §5); a claim **beyond 200k** (scope); a claim that synthetic **teaches Vietnamese** (the
prior does — the curve measures scene transfer); or a gain **within the seed spread** (§4).

---

## §8. The per-point manifest (the auditable core — this is why the file exists)

**`[LOCKED]`** Each curve point records, so any point is regenerable and the curve's honesty is
inspectable:

- **synthetic count** and **frozen generator v1 config**: font list + per-font coverage verdicts
  (DATA_ENGINE §5), corpus mixture (sources, ratio, case/length, DATA_ENGINE §4), degradation config
  (per-group parameter ranges, DATA_ENGINE §6);
- **real-data amount** (full train split — fixed, §2), **hyperparameters**, **checkpoint id**, **seeds**;
- **contamination confirmations** (EVAL_PROTOCOL §10): synthetic corpus from **train labels + Wikipedia
  only**; **no synthetic image** overlaps the test set; **pretrained verified disjoint** from the test set.

**`[LOCKED]` Compute-vs-rigor note (4060, 8 GB).** Each point × k=3 seeds is a full fine-tune; 200k ≈ ~20×
the 10k cost (EVAL_PROTOCOL §7 probe). If compute is tight: run the **three anchor points at k=3**
(headline-grade), and add **intermediate points at k=1** *labeled as single-seed, lower-confidence,
shape-resolving only* — never mixed into a headline gain claim. Honest about the seed count beats a dense
curve of unreproducible points.

---

## §9. This file does not stand alone

**`[LOCKED]`** The curve is reported **with** the ERROR_ANALYSIS §8 **before/after per-axis table** (Run 0
→ shipped model, per targeted stratum). The curve shows *that* accuracy rose; the before/after shows the
rise landed on the axes the engine targeted (tones on small crops), which is the mechanism claim (§5). A
curve without the per-axis before/after is an outcome without a mechanism — half the result.

---

## §10. Scope / validity

**In:** a rec-only, real-VinText-held-out scaling curve (CER headline + Tone-axis + small-text per-axis)
over synthetic count 10k→200k, under a frozen v1 generator, gated by Gate A, with a fully auditable
per-point manifest. **Not claimed:** an e2e curve, a curve beyond 200k, a curve under a changing generator,
a synthetic-test curve, or any inter-point gain within the seed spread. The deliverable is a true curve of
this engine's domain-transfer value on this data — whatever shape it turns out to be.

---

## §11. WHAT WAS ACTUALLY DELIVERED — read this before §1–§10 `[2026-07-12]`

**§1–§10 above spec the SYNTHETIC-COUNT curve (10k → 50k → 200k at full real data). That curve was NEVER
RUN, and it is not a deliverable of this project.** Gate A came back **RED** at 10k (RESULTS "Gate A"), and
the protocol's answer to a RED is unambiguous: **STOP, do not scale** (EVAL_PROTOCOL §7; CLAUDE.md §4
Stage-2 "ONLY if Gate A is green"). Two engine fixes and a three-arm hygiene re-gate (DATA_ENGINE §8.2–§8.4)
did not turn it green: **at matched augmentation, synthetic contributes nothing on top of the full 25,742
real crops.** Scaling to 200k would have bought a more expensive null. **The gate did its job — this is the
gate working, not the project failing**, and the §1–§10 spec is retained above as the (unused) pre-registration
it was, so a reviewer can see the curve was designed honestly *before* it was cancelled honestly.

**The curve that WAS delivered is the LABEL-EFFICIENCY curve** — the pre-registered contingency axis
(EVAL_PROTOCOL §14, frozen §14.1, written **before** its first run). It varies the **real-label budget**
r ∈ {10, 25, 50, 100}% with the synthetic set held **frozen** at the hygiene-clean 10k, k=3 seeds, 18 runs.
**Full protocol, table, and readout: RESULTS "Stage 2c".** The headline shape:

| r (real budget) | n_real | **ΔCER (real+synth − real-only)** | **Δtone** | per-point rule (§7) |
|---|---|---|---|---|
| **10%** | 2,574 | **+3.357 pp better** | **+2.651 pp** | **GREEN** |
| **25%** | 6,436 | **+0.939 pp better** | **+0.645 pp** | **GREEN** |
| 50% | 12,871 | −0.047 (flat) | −0.013 | red |
| **100%** | 25,742 | **−0.038 (flat)** | +0.158 | **red** |

**The gap is monotone in r.** Pre-registered readout: synthetic is **worth ≈2,800 real crops at r=10%** and
**≈0 at r≥50%**. Per §14's pre-committed reading, *gap-widens-as-r-shrinks* = **synthetic SUBSTITUTES for
real labels** — but only where labels are scarce.

**The honest headline (and the sentence that must always travel with it):** *"On real VinText held-out
(rec-only, NFC, k=3), the synthetic engine is worth ≈2,800 real annotations at a 2,574-crop label budget
(CER 16.54 → 13.18; tone 89.34 → 91.99; non-overlapping 95% CIs). Its value decays monotonically with the
real budget and is **NIL at full real data**, where it does not beat a real-only baseline."* The r=100% null
keeps **full prominence** (§14) — it is not a footnote to the green points. **Never claimable:** "synthetic
improves Vietnamese OCR."

**Why §7's headline sentence is void.** §7 pre-committed to *"+X% CER from the synthetic engine on top of a
VinText-real fine-tune."* **X = 0.** That sentence is retired, not reworded to survive; the label-efficiency
statement above replaces it, at a different and explicitly-stated operating point.
