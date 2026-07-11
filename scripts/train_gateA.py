"""Gate A (EVAL_PROTOCOL §7 / DATA_ENGINE §8) — fine-tune on real + 10k synthetic, k=3.

Operating point (EVAL_PROTOCOL §6): document-pretrained pbcquoc vgg_transformer -> fine-tuned
on the FULL VinText-real train split -> synthetic ADDED ON TOP at 10k. Everything else is the
real-only baseline's, unchanged (Firewall 3: vary ONLY synthetic count):

  * SAME pre-registered HP as scripts/train_baseline.py (imported, not re-specified) — crucially
    iters=12000 is held FIXED, so Gate A uses the SAME training compute as the baseline and the
    only difference is the presence of 10k synthetic crops. This is the conservative choice
    against a false-GREEN (equal compute); the alternative (epoch-constant, more iters for the
    larger set) would give synthetic extra compute and is a Stage-3-curve policy question flagged
    to the brain.
  * SAME val set + model-selection rule, SAME eval (rec-only test-500, frozen denom 10,068/37,254).

The combined train annotation = real train crops (25,742) + synth (10,000) = 35,742. A DISTINCT
dataset name builds a FRESH lmdb (vietocr reuses train_<name>/ if present).

k=3 seeds {0,1,2}. Aggregation + the non-overlapping-CI comparison is scripts/aggregate_gateA.py.
This script trains + evaluates one seed and writes result.json; it does NOT declare the gate.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

import scripts.compat  # noqa: E402,F401
from scripts.infer import load_config  # noqa: E402
from scripts.train_baseline import HP, count_ann, evaluate, set_seed  # noqa: E402
from scripts.scorer import format_score  # noqa: E402

SYNTH = "synth10k"        # overridden by --synth
DATASET = f"gateA_{SYNTH}"
COMBINED_ANN = f"annotation_train_{SYNTH}.txt"


def build_combined_annotation():
    """real train crops + synth crops -> one annotation (paths relative to data/crops/)."""
    root = "data/crops"
    out = os.path.join(root, COMBINED_ANN)
    real = [ln for ln in open(os.path.join(root, "annotation_train.txt"), encoding="utf-8") if ln.strip()]
    syn = [ln for ln in open(os.path.join(root, f"annotation_{SYNTH}.txt"), encoding="utf-8") if ln.strip()]
    with open(out, "w", encoding="utf-8") as f:
        f.writelines(l if l.endswith("\n") else l + "\n" for l in real + syn)
    print(f"combined annotation: {len(real)} real + {len(syn)} synth = {len(real)+len(syn)} -> {out}")
    return len(real), len(syn)


def build_cfg(seed, iters):
    cfg = load_config()
    cfg["dataset"] = dict(
        name=DATASET,                      # distinct -> fresh lmdb from the combined annotation
        data_root="./data/crops/",
        train_annotation=COMBINED_ANN,
        valid_annotation="annotation_val.txt",   # SAME val set as the baseline
        image_height=HP["image_height"],
        image_min_width=HP["image_min_width"],
        image_max_width=HP["image_max_width"],
    )
    cfg["trainer"] = dict(
        batch_size=HP["batch_size"], print_every=200, valid_every=HP["valid_every"],
        iters=iters,
        export=f"runs/{DATASET}_seed{seed}/best.pth",
        checkpoint=f"runs/{DATASET}_seed{seed}/ckpt.pth",
        log=f"runs/{DATASET}_seed{seed}/train.log",
        metrics=HP["metrics"],
    )
    cfg["optimizer"] = dict(max_lr=HP["max_lr"], pct_start=HP["pct_start"])
    cfg["aug"] = dict(image_aug=HP["image_aug"], masked_language_model=HP["masked_language_model"])
    cfg["dataloader"] = dict(num_workers=0, pin_memory=True)
    cfg["pretrain"] = "weights/vgg_transformer.pth"
    cfg["weights"] = "weights/vgg_transformer.pth"
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--synth", type=str, default="synth10k", help="synth set name under data/crops/")
    ap.add_argument("--iters", type=int, default=HP["iters"])  # FIXED = baseline's 12000
    ap.add_argument("--eval-only", action="store_true")
    args = ap.parse_args()

    global SYNTH, DATASET, COMBINED_ANN
    SYNTH = args.synth
    DATASET = f"gateA_{SYNTH}"
    COMBINED_ANN = f"annotation_train_{SYNTH}.txt"

    outdir = f"runs/{DATASET}_seed{args.seed}"
    os.makedirs(outdir, exist_ok=True)
    n_real, n_syn = build_combined_annotation()
    set_seed(args.seed)
    cfg = build_cfg(args.seed, args.iters)
    best = cfg["trainer"]["export"]

    if not args.eval_only:
        from vietocr.model.trainer import Trainer
        print(f"=== Gate A fine-tune seed={args.seed} iters={args.iters} "
              f"(real {n_real} + synth {n_syn}) ===")
        print(f"HP (fixed = baseline): {json.dumps(HP)}")
        t0 = time.time()
        trainer = Trainer(cfg, pretrained=True)
        trainer.train()
        train_s = time.time() - t0
        print(f"training wall time: {train_s/60:.1f} min")
    else:
        train_s = None

    if not os.path.exists(best):
        raise SystemExit(f"no exported weights at {best} -- val acc never improved?")

    sc, degen, pairs = evaluate(cfg, best, "test")
    print()
    print(format_score(sc, scope="rec-only (GT boxes)", testset="VinText test-500 (real held-out)"))
    print(f"  degenerate quads scored as empty (not dropped): {degen}")

    res = dict(
        seed=args.seed, iters=args.iters, hp=HP, train_seconds=train_s,
        condition=f"real+{SYNTH}", n_real=n_real, n_synth=n_syn,
        scope="rec-only", testset="VinText test-500 (unseen_test_images)",
        normalization="NFC (axes: NFD)",
        n_instances=sc.n_samples, n_chars=sc.char_ref,
        cer=sc.cer, wer=sc.wer, exact=sc.exact,
        axis1_base=sc.base_acc, axis2_modifier=sc.mod_acc, axis3_tone=sc.tone_acc,
        axis_n=dict(base=sc.base_n, modifier=sc.mod_n, tone=sc.tone_n),
        degenerate=degen,
        synth_manifest=f"data/crops/{SYNTH}/manifest.json",
    )
    with open(f"{outdir}/result.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    with open(f"{outdir}/predictions.tsv", "w", encoding="utf-8") as f:
        for gt, pr in pairs:
            f.write(f"{gt}\t{pr}\n")
    print(f"\nwrote {outdir}/result.json")


if __name__ == "__main__":
    main()
