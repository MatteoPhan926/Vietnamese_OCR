# DATA_ENGINE.md — the synthetic generator (design brain, organized by one thesis)

> **What this file is.** The design of the synthetic data engine — the flagship (CLAUDE.md L3, ~60%
> effort). A **sibling of EVAL_PROTOCOL.md**: that file defines how every number is measured; this file
> defines what the generator produces and *why each knob exists*. Same character — no over-claim, every
> design bet a `[CONJECTURE]` with a real-data kill-test, priorities set by measurement not assumption.
> The generator is not "render Vietnamese text and hope"; it is a domain-transfer instrument whose
> knobs map to the specific ways real scene text differs from what the model already knows.

---

## §1. THE THESIS (organizing principle — everything below follows from it)

The recognizer is **fine-tuned from pbcquoc VietOCR**, which was pretrained on ~10M **document /
handwritten** images. **That prior already reads clean Vietnamese, diacritics included.** Therefore the
synthetic engine's entire marginal value is **domain transfer: document → scene** — perspective,
lighting, textured backgrounds, capture degradation, stylized/low-res fonts. It is **not** teaching
Vietnamese; the prior did that.

Two consequences that reorder the whole engine:

- **`[LOCKED]` The degradation model is THE lever, not one lever.** Clean text on clean backgrounds is
  exactly what the prior already has, so **clean-font-on-Wikipedia-prose synthetic produces a FLAT
  scaling curve** — it teaches the model nothing it doesn't know. Every point of the curve is bought on
  the realism-of-degradation axis and the scene-text-distribution axis, nowhere else.
- **`[LOCKED]` Diagnosis ranks degradation first.** When Gate A is RED (EVAL_PROTOCOL §7), the top
  suspect is *"the synthetic is too clean vs real,"* not *"too little data"* and not *"too few fonts."*
  The re-diagnosis loop (§8) encodes this ranking.

---

## §2. Scope of the engine (right-sized to the locked headline and the 4060)

The headline scaling curve is **rec-only** (EVAL_PROTOCOL §1); the recognizer trains on **word/line
crops**, not full scenes. So:

- **`[LOCKED]` The engine is a crop-level generator.** It produces **(crop image, NFC text label)**
  pairs: rendered text + font + colour + background patch + geometric warp + photometric degradation,
  sized to VietOCR's input (fixed height ~32 px, variable width). This is exactly what the rec curve
  needs and it fits the 4060 (8 GB) — generation is CPU-side rendering, the real bottleneck is disk/throughput,
  not GPU (EVAL_PROTOCOL §7 feasibility probe).
- **`[LOCKED]` Full-scene compositing (SynthText-style depth/segmentation for detection) is secondary /
  future.** Detection is infrastructure (CLAUDE.md L3 tier a), and the curve is a recognition claim.
  Building a full-scene pipeline now is scope creep against the flagship.
- **`[LOCKED]` Label integrity.** Every generated label is **NFC** (matches EVAL_PROTOCOL §2). Per-sample
  safety net: verify each character rendered to a non-`.notdef` glyph before writing the pair — a font
  that silently drops a glyph would otherwise emit an image that does not match its label (training on
  garbage). The font gate (§5) prevents this in bulk; the per-sample check catches the residual.

---

## §3. Entry condition — the engine's first priorities come from measurement, not assumption

**`[LOCKED]` Stage 1 precedes the engine.** Before a single generator knob is tuned, run the **three-axis
error analysis (EVAL_PROTOCOL §3.1) on the real-only baseline** (pretrained + full VinText-real, no
synthetic). That profile — which axis fails, on which crops — sets the engine's initial priorities:

- Tone-axis (Axis 3) failures concentrate on low-res / blurred / small crops → prioritise the
  **resolution + blur** degradations (§6).
- Modifier-axis (Axis 2) failures → a **font-coverage** problem first (§5), not a degradation problem.
- Base-axis (Axis 1) failures on low-contrast / occluded / extreme-perspective crops → prioritise
  **contrast/lighting + geometric** degradations.

Building the engine on a *guessed* failure (the tool-first derailment, CLAUDE.md §9) is the thing this
entry condition exists to prevent. The engine is tuned against the measured gap.

---

## §4. The corpus (scene-leaning, license-clean, contamination-firewalled)

Two sources, mixed — but weighted per the thesis (the prior already has clean prose, so prose is the
*least* valuable text):

- **Source A — Wikipedia Vietnamese (`wiki_vi`, HuggingFace).** Purpose: the **natural diacritic /
  character frequency** of Vietnamese, so the generator produces the hard stacked characters at realistic
  rates. It is lowercase formal prose → **down-weighted**, used mainly for distribution, not domain.
- **Source B — VinText train-split labels** (shop names, street names, addresses, phone numbers, all-caps
  signage). Purpose: the **scene-text domain** — short, capitalised, proper-noun / numeric. **Up-weighted.**

**`[CONJECTURE]` Mix ratio starts scene-heavy** (e.g. ~60–70% Source-B-style short text / 30–40%
Wikipedia snippets). *Kill-test:* A/B the ratio at 10k on real held-out (EVAL_PROTOCOL §3 metrics). Not a
final number — tuned by measurement.

**`[LOCKED]` Distribution fixes (not decoration):**
- **Case augmentation** — inject UPPERCASE and Title Case. Scene text is caps-heavy; Wikipedia/documents
  are lowercase-dominant, and the prior inherits that bias. Missing this is a Gate-A-RED cause that looks
  like a font/degradation problem but is really *"the model never saw scene-style capitals."*
- **Length matching** — short strings (≈1–4 tokens) to match scene-text length, not Wikipedia sentence
  length.
- **Curriculum over-sampling is measured *and* validated, not assumed** — start at natural diacritic
  frequency; over-sample a specific tone/modifier class **only** if Stage-1 (§3) or a later three-axis
  pass flags it failing, **and** treat the over-sampling itself as a `[CONJECTURE]` with its **own A/B** on
  real held-out (over-sampled vs not, one change, EVAL_PROTOCOL §3). A failing axis *triggering* an
  over-sample is not proof the over-sample *helped* — without the A/B you cannot separate the gain from
  seed noise, the same one-change-at-a-time discipline the whole project runs on.

**`[LOCKED]` Contamination firewall (EVAL_PROTOCOL §10):** Source B draws **only** from the **train
split**. Never val/test labels — that would place test answers into training.

---

## §5. The font pipeline (the Modifier-axis control — clean or it poisons training)

Fonts render the letter-forming marks (breve ă, circumflex â ê ô, horn ơ ư, stroke đ). A font that
mangles or drops these trains the model on **wrong glyphs**, and the damage surfaces as Modifier-axis
(Axis 2) error on real data — indistinguishable from a model failure unless the font is verified first.

- **`[LOCKED]` Source: Google Fonts with `subset=vietnamese`, SIL OFL 1.1** (license-clean, EVAL_PROTOCOL
  §10). No ambiguous-license aggregator fonts.
- **`[LOCKED]` Per-font, per-stacked-diacritic coverage verification** — the method (G6 made concrete),
  run once per candidate font over the **full Vietnamese charset and the ~30 doubly-marked vowels**
  (the ế/ệ, ứ/ữ, ấ/ậ, ắ/ặ, ố/ộ, ớ/ợ families + đ), three checks:
  1. **Glyph exists** — the codepoint maps to a real glyph via the font cmap (not `.notdef` / tofu box).
  2. **Distinctness / round-trip** — render the stacked char, its base-without-tone, and its
     base-without-modifier; confirm the three bitmaps are **pixel-distinct**. A font that renders `ệ`
     identically to `ê` or `e` is **silently dropping a mark** and passes check 1 while still being
     poison.
  3. **Visual audit** — human eye on a fixed stacked-diacritic sample string; reject misplaced,
     wrong-scale, or overlapping marks even when checks 1–2 pass.
- **`[LOCKED]` Output = a per-font verdict** (PASS / FAIL + which codepoints failed), written into the
  **data manifest** (EVAL_PROTOCOL §11). Only PASS fonts generate. **Target 15–20 clean fonts** — quality
  over count.

> **`[LOCKED]` Caveat that pushes work onto §6:** 15–20 clean *digital* Google Fonts **under-represent**
> real signage (hand-painted, LED, embossed, decorative). Font diversity alone cannot close the
> appearance gap — so the **degradation model carries the domain-randomization load**. When Base-axis
> error on real data correlates with font-appearance gaps, the reflex is *not* "add fonts" but "the
> degradation/appearance augmentation is too narrow."

---

## §6. The degradation model (THE lever — the Tone/Base-axis control)

Where the synthetic earns every point of the curve. Four groups, each mapped to the real
document→scene gap and to the axis it defends. **All parameters are `[CONJECTURE]`, tuned via the §7 audit
and §8 Gate-A loop — never guessed as final.**

- **Geometric** (scene text is not axis-aligned like a scan): perspective homography, rotation, shear,
  mild baseline curvature. Defends **Base-axis** against real viewing angles.
- **Photometric** (scene lighting vs uniform scan): illumination gradients, cast shadows, low-contrast
  text/background colour pairs, specular highlights / glare (glossy signs, LED). Defends **Base-axis** on
  low-contrast and **Tone-axis** where glare washes out marks.
- **Background** (documents are white; scenes are textured — *the biggest single transfer element*):
  composite text onto **real background patches** cropped from scene images without text, via alpha or
  Poisson blending. Defends against the model's document-white prior.
- **Sensor / capture** (phone-camera artifacts, *the Tone-axis killers*): motion blur, defocus (Gaussian)
  blur, JPEG compression, sensor noise, and **downsample→upsample to emulate small/low-res text**. Tones
  are tiny high-frequency marks — they are the **first detail destroyed** by blur / low-res / JPEG, so
  this group is what generates the training signal that makes tones survive real capture. Directly defends
  **Tone-axis (Axis 3)**.

**`[LOCKED]` The mapping is the point:** Modifier-axis is owned by §5 (font correctness); Tone- and
Base-axes are owned by §6 (degradation realism). This is exactly the loop the three-axis metric closes —
a failing axis names the knob to turn.

---

## §7. The synthetic-vs-real crop distribution audit (cheap, run BEFORE Gate A)

Under the thesis, the #1 Gate-A-RED cause is *"synthetic is systematically cleaner than real."* Catch it
**before** spending a training run, with a cheap image-statistics audit over synthetic crops vs real
VinText crops:

- **`[LOCKED]` Statistics:** sharpness (Laplacian variance), contrast, luminance mean/std, crop height /
  resolution, and a background-complexity proxy (e.g. edge density behind text).
- **`[LOCKED]` Pass criterion: the synthetic distribution must COVER the real one** on each statistic —
  same range, comparable spread. If synthetic is systematically sharper / higher-contrast / cleaner /
  higher-res than real, the degradation is too weak and the curve will be flat *before you train*.

This audit operationalizes "degradation realism first": it turns the thesis into a measurement you run at
zero training cost, and it is the first gate the generator must pass.

---

## §8. The Gate-A / re-diagnosis loop (the engine's control loop)

Generate 10k → §7 distribution audit → **Gate A (EVAL_PROTOCOL §7)**.

- **GREEN** (the improvement's CI over k=3 seeds does not overlap the real-only baseline's, on CER **and**
  the Tone-axis — seed-noise significance, EVAL_PROTOCOL §7) → scale the
  curve 10k → 50k → 200k (EVAL_PROTOCOL §4, §6).
- **RED** → **STOP. Do not scale.** Diagnose on **ranked axes** (this ranking *is* the thesis):
  1. **Degradation realism** (top suspect) — does §7's audit show synthetic cleaner than real? Increase
     the failing degradation group to match the real distribution.
  2. **Font / background diversity** — is the appearance range too narrow (§5 caveat)? Widen backgrounds /
     appearance augmentation.
  3. **Corpus distribution** — case, length, char-class matched (§4)? The lowercase-Wikipedia trap.
  4. **Domain fundamental** — a specific real effect crop-synthesis can't capture, named by the failing
     axis (e.g. real motion blur → add it explicitly). Escalate to full-scene compositing (§2) *only* if
     the diagnosis proves a scene-context effect a crop generator cannot produce.
  Fix the **one** specific thing the three-axis metric + §7 audit localize, then **re-run Gate A at 10k.**

**`[LOCKED]` The forbidden move is "add more data."** Red at 10k means the engine's *distribution* is
wrong, not its *volume*; scaling a wrong distribution to 200k is the two-week burn EVAL_PROTOCOL §7 exists
to stop.

### §8.1 The re-gate BUDGET (closes a p-hacking hole — added 2026-07-11, BEFORE the first re-gate)

An unbounded "fix one thing → re-gate" loop is a **p-hack by iteration**: run it enough times and some
config clears the bar on seed luck (k=3 CIs are wide). The loop is bounded, and it is bounded *now*, before
any re-gate has been attempted:

- **`[LOCKED]` MAX 2 re-gate attempts** at the full-real operating point. Each must (i) name **ONE** fix,
  (ii) state the **mechanism** by which it is expected to move the number, (iii) be **written down before
  the run**. No post-hoc "we also changed X."
- **`[LOCKED]` Bug-checks are NOT attempts.** Ruling out a broken generator / undertraining / corrupted
  labels is measurement hygiene (§8.2). Only a *deliberate engine change* burns an attempt.
  **The line, drawn sharply so "it's just hygiene" cannot become a loophole:** *hygiene* = making the
  generator emit **VALID** data (legible crops, labels matching the image, NFC, in-vocab charset) — a crop
  no human can read is noise, not data, and fixing it is fixing a bug. An *attempt* = changing **WHAT the
  data emphasizes** (strata weighting, degradation targeting, corpus mix, font mix). Validity is free;
  emphasis is budgeted.
- **`[LOCKED]` If both attempts are RED → the finding is "10k synthetic gives no lift at full real data,"**
  and the project moves to the **real-data-budget axis** (EVAL_PROTOCOL §14) — the pre-registered
  contingency, not a post-hoc rescue. The full-real RED is reported at full prominence regardless of what
  the budget axis later shows.

### §8.2 Bug-checks BEFORE any fix (a RED is a claim about the world — first prove it is not a claim about your code)

Cheap, mandatory; none burns a re-gate attempt:
1. **Undertraining / dilution.** At fixed iters, synthetic *dilutes* real gradient steps (10k synth on
   25.7k real → real drops from ~15 to ~11 epochs at equal compute). Read the **val curves in the existing
   logs**: if val accuracy is still climbing at the final iter, the RED is partly a compute artifact →
   re-run **both arms** at scaled iters (compute matched at the higher level), never the synth arm alone.
2. **Legibility.** Eyeball ~50 random synthetic crops against their labels. Illegible crops or misaligned
   labels are training *noise* — which both flattens the mean and **inflates seed variance**.
3. **Label integrity.** Assert every synthetic label is **NFC** and its charset is a **subset of the model
   vocab**. NFD leakage or OOV characters (wiki_vi carries plenty) silently corrupt the target sequence.
4. **Was the synthetic even learned?** Score the synth-trained model on a **held-out synthetic** split. Did
   not learn synth → the data/pipeline is broken. **Learned synth but real did not move → the data is fine
   and it simply does not transfer** — that is the real finding, not a bug. (Synthetic-test accuracy is a
   sanity check only, never a result — SCALING §6.)

### §8.3 Attempt 1, pre-declared: TARGET the failure strata (do not distribution-match)

**Mechanism.** §7's audit checks that synthetic *covers* real's marginal image-statistics — and it
**passed while the gate went RED.** That is itself a finding: **covering the marginals is necessary but not
sufficient.** A generator matched to real's *marginals* reproduces real's *rate* of hard examples, so 10k
synth adds only a few hundred hard-tilt crops on top of the ~1,300 the 25.7k real crops already contain —
a rounding error against real examples that are strictly more informative than rendered ones.

**The fix (ONE change):** re-weight generation to **over-represent the measured failure strata** instead of
matching real's marginals — heavy on **tilt ≥20°, contrast <0.20, height <12 px, 1–2-char crops** (the
strata at 23–30% CER vs 9.4% overall, §12). The synthetic's job is not to look like the *average* real
crop; it is to supply **many more examples of the crops the model actually fails on**. Re-gate at 10k.

---

## §9. Design bets (`[CONJECTURE]`; each kill-test is a real-data measurement)

- **`[CONJECTURE]`** Given the document prior, **degradation realism — not font count, not corpus
  volume — is the dominant lever** for closing the synth-real gap. *Kill-test:* the §8 diagnosis — if
  matching degradation to real (via §7) moves Gate A while adding fonts/data does not, confirmed; if the
  reverse, the thesis is wrong and the engine re-prioritises.
- **`[CONJECTURE]`** A **crop-level generator suffices** for the rec-only curve. *Kill-test:* the rec-only
  curve rises under crop synthesis; a plateau whose diagnosis points to scene-context effects → escalate
  to full-scene.
- **`[CONJECTURE]`** A **scene-leaning corpus + case augmentation** beats Wikipedia-heavy. *Kill-test:*
  A/B the mix at 10k on real held-out.
- **`[CONJECTURE]`** **15–20 clean fonts + heavy degradation** cover the real appearance range well
  enough. *Kill-test:* if Base/Modifier-axis error on real data correlates with font-appearance gaps, widen
  appearance augmentation (§5 caveat), not raw font count.

> **No synthetic recipe is validated until the real-data, rec-only, protocol-clean curve backs it.** A
> generator that raises *synthetic*-test accuracy has proven nothing (EVAL_PROTOCOL Firewall 3).

---

## §10. Reproducibility (the generator is a script, not a mood)

**`[LOCKED]`** Every synthetic set = **generation script + config + seed**, plus the **data manifest**
(EVAL_PROTOCOL §11) recording: the **font list + per-font coverage verdict** (§5), the **corpus mixture**
(sources, ratio, case/length settings) (§4), the **degradation config** (per-group parameter ranges)
(§6), and the **synthetic count**. Any curve point must be regenerable byte-for-recipe from its manifest,
or the curve's honesty is unauditable.

---

## §11. Scope / validity (claim only within)

**In:** a crop-level Vietnamese scene-text synthetic generator (corpus + verified fonts + degradation)
whose value is **document→scene domain transfer**, proven by the rec-only real-VinText scaling curve.
**Not claimed:** a general synthetic-text framework, full-scene detection synthesis (secondary/future),
other languages, other domains (handwriting/historical), or that synthetic teaches Vietnamese from
scratch (the prior does). The engine's contribution is scene realism on top of a document prior —
stated exactly, nothing more.

---

## §12. Stage-1 findings — the MEASURED priorities supersede §3/§5's anticipations (2026-07-10)

Stage-1 error analysis (Run 0, real-only baseline, public labels, k=3) ran and **refuted several
predictions baked into this doc**. Per §3 ("priorities come from Stage 1, not assumption"), the engine is
built on the measurement below, not the anticipations it corrects.

**`[LOCKED]` Measured priority order** (by CER-share of the worst strata; overall CER 9.40%), replacing
the font-coverage / stacked-diacritic-curriculum focus §3/§5 anticipated:
1. **Geometric (tilt / perspective) FIRST** — worst stratum, tilt ≥20° = **30.34%** CER.
2. **Photometric (contrast / lighting)** — contrast <0.20 = **27.55%**.
3. **Resolution / blur** — height <12 px = **22.86%**, and the mechanism behind tone failure (below).

Font coverage is **demoted to a correctness prerequisite** (generation must render ệ/ữ or it poisons
training, §5) but is **NOT where the error lives** — do not spend the degradation budget there.

**`[LOCKED]` Corrected mechanisms (refuted predictions — do NOT target these):**
- **Tone failure is DROP, not confusion.** hỏi↔ngã (the "canonical confusion" §3.3/ERROR_ANALYSIS §3.3
  predicted) is essentially absent (4+4 pairs); tone error is presence/absence (215 drops + 174
  hallucinations vs 199 tone-to-tone). → the resolution/blur fix is about **mark VISIBILITY** (the mark
  surviving real capture), NOT similar-tone over-sampling.
- **No "horn drop."** Horn (ơ ư) is the BEST modifier class (2.87% error); §5's horn-drop signature is
  refuted. Worst modifier is breve (ă, 11.16%) but on only 242 positions (wide error bar) — do not
  over-index on it.
- **Small text is a GENERAL legibility failure, not tone-specific.** Base falls hardest at small size
  (−11.4 pp vs tone −10.0 pp), refuting §3's "tone falls off a cliff at small sizes." Isolated 1-char
  crops destroy letter identity (tone untouched at 94.57%) → **include very short / 1-char crops** in
  generation.
- **Case-augmentation validated:** pure-case is 8.88% of all edits — the model makes real case errors, so
  §4's UPPERCASE / Title-case augmentation earns its place.

**Robustness caveat (§4 still open):** base-dominates-diacritics (base-only 39.48% vs diacritic-only
16.12% of edits, ~2.5×) is on **public labels** — an *upper bound* on the model's base share (label noise
inflates base errors). Gold (§4, pending manual pass) can only **shrink** the base share; a flip would need
>50% of base errors to be label noise, implausible → the **ordering is robust**, Stage 2 proceeds on it,
and gold re-runs the decomposition before the final numbers are believed.

### §8.4 The AUGMENTATION CONFOUND — Attempt 1 must carry a control arm (added 2026-07-11; a design-brain miss)

**The thing none of these docs caught.** The baseline trains with `image_aug=True` — vietocr's built-in
augmentor, which already applies blur, motion blur, noise, JPEG compression, perspective and affine/shear
**to the REAL crops, every epoch.** So the baseline has *already* been manufacturing hard examples out of
real data, and much of the degradation model (§6) is **redundant with an augmentation pipeline the
comparator already runs.** Worse for the synthetic: **a REAL crop degraded to be hard is strictly more
informative than a RENDERED crop degraded to be hard** — same degradation, better content underneath.

This explains the flat Gate A better than any ranked §8 suspect, and it has a hard consequence:

- **`[LOCKED]` VERIFY FIRST (do not assume):** read what `image_aug=True` actually applies in the installed
  vietocr, and record the exact transform list + strength ranges in the manifest. If it already covers
  geometric + photometric + blur, the synthetic's degradations are *duplicating* it.
- **`[LOCKED]` The comparator must be the STRONGEST real-only model, not the default-augmented one.**
  Comparing synthetic against an *under-augmented* baseline is a **strawman**: a reviewer's first question
  is "would cranking augmentation have done the same?" — and if it would, the "+X% from synthetic" claim is
  void. A baseline that is non-starved on **data** (25.7k crops, Stage 0) is not automatically non-starved
  on **augmentation**.
- **`[LOCKED]` Attempt 1 is therefore a THREE-ARM experiment**, k=3 seeds each:
  - **A** = baseline (real + default aug) — already measured.
  - **B** = real + **strata-targeted AUGMENTATION**, NO synthetic — augmentation cranked to manufacture the
    measured failure strata (tilt ≥20°, contrast <0.20, height <12 px) *from real crops*.
  - **C** = real + the same strata-targeted augmentation + **strata-targeted SYNTHETIC** (§8.3).
  **Judge C against B, not against A.** `B − A` = what augmentation alone buys. `C − B` = **the pure
  synthetic contribution at matched augmentation** — the only number that honestly answers "was generating
  synthetic data worth it?"
- **`[LOCKED]` The control arm B is NOT a re-gate attempt.** It changes no synthetic engine knob; it
  removes a confound and raises the comparator. **Raising the bar is always permitted; lowering it never
  is.**

**Every outcome is a real finding**, which is why this is worth the compute:
- **C > B** → synthetic supplies something augmentation cannot manufacture (content/letterform diversity).
- **C ≈ B > A** → **"aggressive augmentation of real data captures everything this synthetic engine
  provides"** — a strong, useful, senior negative result, and the project's own baseline improves.
- **C ≈ B ≈ A** → the failure strata are hard for reasons *neither* more hard examples nor synthesis
  addresses. Also a finding, and it points at the label-efficiency axis (EVAL_PROTOCOL §14).

This sharpens the project's central question from *"does synthetic data help?"* to the one practitioners
actually face and almost nobody tests honestly: **"is synthetic data worth generating, or should you just
augment harder?"**

> **§8.4 OUTCOME (2026-07-11): measured C ≈ B.** Every metric |Δ| < 0.17 pp, all CIs overlap; combined
> with §8.2(d) (synth-test 26.4 → 16.0 = learned; real flat = no transfer), the full-real question is
> **closed**: at matched augmentation, this synthetic engine adds nothing on top of 25.7k real crops.
> Attempt 1 of 2 spent; Attempt 2 held in reserve (ceiling, not quota). The project proceeds on the
> pre-registered real-data-budget axis — EVAL_PROTOCOL §14/§14.1. The B−A augmentation-tradeoff pattern
> (axes up, sequence metrics down) becomes a write-up claim only after the ins/del decomposition.