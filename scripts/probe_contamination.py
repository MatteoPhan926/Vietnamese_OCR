"""Stage 0.2 — EMPIRICAL contamination probe for EVAL_PROTOCOL §6 [VERIFY->FREEZE @ Stage 0].

The published record cannot settle the disjointness question:
  * pbcquoc's README documents the 10M pretraining set only as "synthetic / handwriting /
    real scanned documents" -- no scene-text source named, and no VinText mention anywhere
    in the repo. That is an ABSENCE-OF-MENTION argument, not a set-level proof.
  * The full 10M manifest is NOT published (only a ~1M synthetic sample is released), so a
    set intersection is impossible.
  * The checkpoint is dated 2022-12-03; VinText was released ~May 2021. The checkpoint
    POSTDATES the dataset, so the temporal argument CANNOT exonerate it either.

So we probe it empirically, with ZERO fine-tuning, at rec-only scope on GT-box crops.

The discriminating signal: VinText's train/val/test splits are disjoint IMAGE sets. If the
pretraining corpus had ingested VinText (or its source imagery), the checkpoint would have
seen the train images. Memorised-train-but-not-test shows up as a LARGE train-vs-test gap.
A checkpoint that never saw any of it shows a SMALL gap (both splits are equally out of its
document domain), and an absolute CER consistent with a document->scene domain gap rather
than with its in-domain 0.88 full-sequence precision.

  * large gap (train << test)  -> train contamination; test may still be clean, but the
                                  fine-tuning baseline is compromised. ESCALATE.
  * small gap + high CER       -> consistent with NO VinText exposure. Residual risk stated.
  * small gap + LOW CER        -> alarming: consistent with ALL splits seen. ESCALATE.

This probe cannot PROVE disjointness. It can only fail to falsify it. Reported as such.
"""
import argparse
import json
import random
import sys
import time

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scripts.infer import Recognizer, load_config, predict_instances  # noqa: E402
from scripts.scorer import Score, format_score, score_pair  # noqa: E402
from scripts.vintext import iter_instances  # noqa: E402


def sample(split, n, seed):
    allinst = list(iter_instances(split, scorable_only=True))
    if n <= 0 or n >= len(allinst):
        return allinst  # full split: no sampling noise at all
    rng = random.Random(seed)
    rng.shuffle(allinst)
    return allinst[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch", type=int, default=48)
    args = ap.parse_args()

    cfg = load_config()
    rec = Recognizer(cfg)
    print(f"checkpoint: {cfg['weights']}  device: {cfg['device']}")
    print(f"ZERO-SHOT (no fine-tuning). n={args.n}/split seed={args.seed}\n")

    results = {}
    for split in ("train", "test"):
        insts = sample(split, args.n, args.seed)
        t0 = time.time()
        kept, preds, degen = predict_instances(rec, insts, max_batch=args.batch)
        dt = time.time() - t0

        sc = Score()
        for inst, p in zip(kept, preds):
            score_pair(sc, inst.text, p)

        print(format_score(sc, scope="rec-only (GT boxes)", testset=f"VinText {split} (n={len(kept)})"))
        print(f"  degenerate quads (scored as empty, NOT dropped): {degen}   "
              f"inference: {dt:.1f}s ({1000*dt/max(1,len(kept)):.1f} ms/crop, batched)\n")
        results[split] = dict(cer=sc.cer, wer=sc.wer, exact=sc.exact,
                              base=sc.base_acc, mod=sc.mod_acc, tone=sc.tone_acc,
                              n=len(kept), degenerate=degen, chars=sc.char_ref)

    gap = results["test"]["cer"] - results["train"]["cer"]
    print("=" * 72)
    print(f"train CER {results['train']['cer']*100:.2f}%   "
          f"test CER {results['test']['cer']*100:.2f}%   "
          f"gap (test-train) {gap*100:+.2f} pp")
    print("A large positive gap => the checkpoint saw VinText train. Escalate to brain.")
    print("=" * 72)

    with open("runs/probe_contamination.json", "w", encoding="utf-8") as f:
        json.dump(dict(results=results, gap_pp=gap * 100, seed=args.seed, n=args.n,
                       checkpoint_sha256="380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59"),
                  f, indent=2)


if __name__ == "__main__":
    main()
