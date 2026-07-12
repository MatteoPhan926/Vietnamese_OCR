# docs/ — the pre-registration

These are the documents that were written **before** the experiments they govern. They are the reason
any number in the top-level [README](../README.md) is worth reading: the thresholds, the metrics, the
stopping rules and the gate conditions were fixed in advance, in writing, and the git history proves it.

They are reproduced here **unedited**. Where a prediction in them was refuted by measurement, the
refutation is recorded *in place* — struck through, corrected, or annotated — rather than quietly
rewritten. Several of them contain conjectures that turned out to be wrong. That is the point.

## What each file is

| file | what it is |
|---|---|
| **[CLAUDE.md](CLAUDE.md)** | The project anchor. The locked decisions (architecture, domain, priorities), the firewalls, the ladder, and the design bets — each with a kill-test. Written first, before any code. |
| **[EVAL_PROTOCOL.md](EVAL_PROTOCOL.md)** | The measurement ruler. Metric definitions (CER/WER/exact-match on NFC; the three diacritic axes on NFD), pipeline scopes, the frozen test denominator, the Gate-A condition, the k=5 pre-commitment, the §14 budget axis, and the §14.4 attribution control — all fixed before the runs they adjudicate. |
| **[DATA_ENGINE.md](DATA_ENGINE.md)** | The synthetic generator's design: corpus, font coverage gate, degradation model — and §8's pre-declared **budget of 2 re-gate attempts**, which is what stops a red gate from being iterated into a green one. |
| **[ERROR_ANALYSIS.md](ERROR_ANALYSIS.md)** | The Stage-1 error analysis spec and report. The document that refuted this project's own central conjecture (that diacritics dominate the error). |
| **[SCALING.md](SCALING.md)** | The scaling-curve protocol: what is held fixed, what varies, and the rule that the curve's true shape — including a plateau or a decline — gets reported. |
| **[BUILD_PLAN.md](BUILD_PLAN.md)** | The stateful build roadmap and the session-to-session resume pointer. A running log of what was done, in what order, and what was still open. |
| **[PAGE_SPEC.md](PAGE_SPEC.md)** | The spec for the public layer — the narrative spine and the honesty rules the README and project page had to obey (negatives first; every number carries its scope, n, k and CI; no result softened after the fact). |

The measured-evidence ledger — every number, with its provenance — lives at
**[../RESULTS.md](../RESULTS.md)**. It is deliberately *not* in this folder: `docs/` is what was promised,
`RESULTS.md` is what was found.

## Verifying the ordering yourself

The claim "this was pre-registered" is checkable, not rhetorical:

```bash
# when each doc was written, vs. when the run it governs was committed
git log --follow --format='%ad %s' --date=short -- docs/EVAL_PROTOCOL.md
git log --format='%ad %s' --date=short -- RESULTS.md
```

The specific orderings that matter:

- **The Gate-A condition** (non-overlapping 95% CI on *both* CER and tone) was written into
  `EVAL_PROTOCOL.md` §7 before the baseline's seed-variance — the number that sets the bar — had been
  measured, and long before the gate was run. The gate came back RED against a bar it could not have
  been tuned to.
- **The real-label-budget axis** (`EVAL_PROTOCOL.md` §14) was reserved as a contingency *before* Gate A
  ran. The pivot to label-efficiency after the RED was not a post-hoc rescue; it was the branch that had
  already been written down.
- **The k=5 pre-commitment** (`EVAL_PROTOCOL.md` §14.2) states that the extra seeds replace the k=3
  numbers *regardless of direction*. It was committed before those seeds were trained, which is the only
  condition under which adding seeds to a positive result is honest rather than seed-shopping.
- **The clean-render control's readings** (`EVAL_PROTOCOL.md` §14.4(A)) — ≥80% of the gain means the
  realism machinery is not load-bearing; <50% means it is — were fixed before the control was generated.
