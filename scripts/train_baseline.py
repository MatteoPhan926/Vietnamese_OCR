"""Stage 0.5 — the real-only baseline: fine-tune vgg_transformer on VinText-real train.

This is the operating point EVAL_PROTOCOL §6 locks:
    document-pretrained pbcquoc VietOCR  ->  fine-tuned on the FULL VinText-real train split
and it is the point every future synthetic curve point is measured against. So its
hyperparameters are PRE-REGISTERED here (see HP below) and fixed for every later run.

Trained on: 25,744 real train crops (train_images, im0001-1200).
Model-selected on: 7,200 val crops (test_image, im1201-1500)  -- NEVER the test set.
Evaluated on: test-500 (unseen_test_images), rec-only, in-memory from GT annotation,
              denominator pinned at 10,068 / 37,254 (EVAL_PROTOCOL §13 E8).

k=3 seeds. The run-to-run std of test CER across seeds is the Gate-A NOISE FLOOR
(EVAL_PROTOCOL §7 [VERIFY->FREEZE @ Stage 0]).
"""
import argparse
import json
import os
import random
import sys
import time

import numpy as np
import torch

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

import scripts.compat  # noqa: E402,F401  (numpy-2 shims; must precede vietocr import)
from scripts.infer import Recognizer, load_config, predict_instances  # noqa: E402
from scripts.scorer import Score, format_score, score_pair  # noqa: E402
from scripts.vintext import iter_instances  # noqa: E402

# ---------------------------------------------------------------- PRE-REGISTERED
# Fixed for the real-only baseline AND for every synthetic curve point (Firewall 3:
# the curve varies ONLY synthetic count). Changing any of these invalidates the curve.
HP = dict(
    batch_size=32,
    iters=12000,           # ~15 epochs over 25,744 crops @ bs32 (805 iters/epoch)
    valid_every=1000,
    metrics=2000,          # val samples used for model selection
    max_lr=3e-4,           # pbcquoc base.yml default
    pct_start=0.1,         # OneCycleLR
    image_height=32,
    image_min_width=32,
    image_max_width=512,
    image_aug=True,
    masked_language_model=True,
    optimizer="AdamW betas=(0.9,0.98) eps=1e-9 + OneCycleLR",
    model_selection="best val full-sequence accuracy (vietocr rule), on val-300 crops only",
)


def count_ann(split):
    with open(f"data/crops/annotation_{split}.txt", encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_cfg(seed, iters):
    cfg = load_config()
    cfg["dataset"] = dict(
        # NOT seed-suffixed: the data is identical across seeds, so the lmdb cache is
        # shared. Only sampler order / augmentation / dropout differ by seed -- which is
        # exactly the run-to-run variance the Gate-A noise floor is meant to capture.
        name="vintext_real",
        data_root="./data/crops/",
        train_annotation="annotation_train.txt",
        valid_annotation="annotation_val.txt",
        image_height=HP["image_height"],
        image_min_width=HP["image_min_width"],
        image_max_width=HP["image_max_width"],
    )
    cfg["trainer"] = dict(
        batch_size=HP["batch_size"],
        print_every=200,
        valid_every=HP["valid_every"],
        iters=iters,
        export=f"runs/baseline_seed{seed}/best.pth",
        checkpoint=f"runs/baseline_seed{seed}/ckpt.pth",
        log=f"runs/baseline_seed{seed}/train.log",
        metrics=HP["metrics"],
    )
    cfg["optimizer"] = dict(max_lr=HP["max_lr"], pct_start=HP["pct_start"])
    cfg["aug"] = dict(image_aug=HP["image_aug"], masked_language_model=HP["masked_language_model"])
    cfg["dataloader"] = dict(num_workers=0, pin_memory=True)  # num_workers>0 + lmdb is flaky on win
    cfg["pretrain"] = "weights/vgg_transformer.pth"
    cfg["weights"] = "weights/vgg_transformer.pth"
    return cfg


def evaluate(cfg, weights, split="test"):
    rec = Recognizer(cfg, weights=weights)
    insts = list(iter_instances(split, scorable_only=True))
    kept, preds, degen = predict_instances(rec, insts)
    sc = Score()
    for inst, p in zip(kept, preds):
        score_pair(sc, inst.text, p)
    del rec
    torch.cuda.empty_cache()
    return sc, degen, list(zip([i.text for i in kept], preds))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--iters", type=int, default=HP["iters"])
    ap.add_argument("--eval-only", action="store_true")
    args = ap.parse_args()

    outdir = f"runs/baseline_seed{args.seed}"
    os.makedirs(outdir, exist_ok=True)
    set_seed(args.seed)

    cfg = build_cfg(args.seed, args.iters)
    best = cfg["trainer"]["export"]

    if not args.eval_only:
        from vietocr.model.trainer import Trainer

        print(f"=== fine-tuning seed={args.seed} iters={args.iters} ===")
        print(f"HP: {json.dumps(HP)}")
        t0 = time.time()
        trainer = Trainer(cfg, pretrained=True)  # loads local weights/vgg_transformer.pth
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
        scope="rec-only", testset="VinText test-500 (unseen_test_images)",
        normalization="NFC (axes: NFD)",
        n_instances=sc.n_samples, n_chars=sc.char_ref,
        cer=sc.cer, wer=sc.wer, exact=sc.exact,
        axis1_base=sc.base_acc, axis1_base_ci=sc.base_acc_ci,
        axis2_modifier=sc.mod_acc, axis3_tone=sc.tone_acc,
        axis_n=dict(base=sc.base_n, modifier=sc.mod_n, tone=sc.tone_n),
        degenerate=degen,
        checkpoint_sha256_pretrain="380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59",
        # counted from the annotation files, never hardcoded (a hardcoded 25744 survived the
        # OOV filter that dropped 2 instances and silently misreported the manifest once)
        train_crops=count_ann("train"), val_crops=count_ann("val"),
        lmdb_note="vietocr createDataset has an off-by-one (nSamples=cnt-1): lmdb exposes N-1 "
                  "of the N written crops, so training actually saw train_crops-1. Labels and "
                  "images stay aligned (read_buffer uses one idx). Benign; recorded.",
    )
    with open(f"{outdir}/result.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    with open(f"{outdir}/predictions.tsv", "w", encoding="utf-8") as f:
        for gt, pr in pairs:
            f.write(f"{gt}\t{pr}\n")
    print(f"\nwrote {outdir}/result.json  (+ predictions.tsv for Stage-1 error analysis)")


if __name__ == "__main__":
    main()
