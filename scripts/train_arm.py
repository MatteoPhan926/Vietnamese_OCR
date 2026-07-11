"""The THREE-ARM Attempt-1 experiment (DATA_ENGINE §8.4, EVAL_PROTOCOL §15).

  A = real + DEFAULT aug                      (the Stage-0 baseline -- already measured)
  B = real + STRATA-TARGETED aug, NO synth    (CONTROL; not a re-gate attempt)
  C = real + the SAME strata aug + STRATA-TARGETED SYNTHETIC (§8.3)   (Attempt 1)

JUDGE C AGAINST B, NOT A.
  B - A = what augmentation alone buys.
  C - B = the PURE synthetic contribution AT MATCHED AUGMENTATION -- the only honest answer to
          "was generating the synthetic worth it?" Comparing C to an under-augmented A is a
          strawman (§15: the comparator is the STRONGEST real-only config; the bar may be RAISED,
          never lowered).

B and C use the IDENTICAL augmentor (engine.strata_aug.StrataAugment), so C-B isolates the
synthetic regardless of how the augmentation is tuned.

Everything else is held fixed (Firewall 3): same pre-registered HP, iters=12000 FIXED (= the
baseline's training compute), same val set + model-selection rule, same eval (rec-only test-500,
frozen denominator 10,068 / 37,254). k=3 seeds.

This script trains + evaluates ONE arm/seed. It does NOT declare a gate.
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
from scripts.scorer import format_score  # noqa: E402
from scripts.train_baseline import HP, evaluate, set_seed  # noqa: E402

SYNTH = "synth10k_strata"   # the §8.3 strata-targeted set (arm C only)


def build_combined_annotation():
    root = "data/crops"
    out = os.path.join(root, f"annotation_train_{SYNTH}.txt")
    real = [ln for ln in open(os.path.join(root, "annotation_train.txt"), encoding="utf-8") if ln.strip()]
    syn = [ln for ln in open(os.path.join(root, f"annotation_{SYNTH}.txt"), encoding="utf-8") if ln.strip()]
    with open(out, "w", encoding="utf-8") as f:
        f.writelines(l if l.endswith("\n") else l + "\n" for l in real + syn)
    return len(real), len(syn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["B", "C"], required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--iters", type=int, default=HP["iters"])   # FIXED = baseline's 12000
    args = ap.parse_args()

    if args.arm == "B":
        n_real = sum(1 for ln in open("data/crops/annotation_train.txt", encoding="utf-8") if ln.strip())
        n_syn = 0
        ann = "annotation_train.txt"
    else:
        n_real, n_syn = build_combined_annotation()
        ann = f"annotation_train_{SYNTH}.txt"

    dataset = f"arm{args.arm}"
    outdir = f"runs/{dataset}_seed{args.seed}"
    os.makedirs(outdir, exist_ok=True)
    set_seed(args.seed)

    cfg = load_config()
    cfg["dataset"] = dict(
        name=dataset, data_root="./data/crops/",
        train_annotation=ann, valid_annotation="annotation_val.txt",
        image_height=HP["image_height"], image_min_width=HP["image_min_width"],
        image_max_width=HP["image_max_width"],
    )
    cfg["trainer"] = dict(
        batch_size=HP["batch_size"], print_every=200, valid_every=HP["valid_every"],
        iters=args.iters, export=f"{outdir}/best.pth", checkpoint=f"{outdir}/ckpt.pth",
        log=f"{outdir}/train.log", metrics=HP["metrics"],
    )
    cfg["optimizer"] = dict(max_lr=HP["max_lr"], pct_start=HP["pct_start"])
    cfg["aug"] = dict(image_aug=HP["image_aug"], masked_language_model=HP["masked_language_model"])
    cfg["dataloader"] = dict(num_workers=0, pin_memory=True)
    cfg["pretrain"] = "weights/vgg_transformer.pth"
    cfg["weights"] = "weights/vgg_transformer.pth"

    from engine.strata_aug import DESCRIPTION, StrataAugment
    from vietocr.model.trainer import Trainer

    print(f"=== ARM {args.arm}  seed={args.seed}  real={n_real} synth={n_syn}  iters={args.iters} ===")
    print(f"augmentor: StrataAugment (SAME in B and C) {json.dumps(DESCRIPTION)}")
    t0 = time.time()
    trainer = Trainer(cfg, pretrained=True, augmentor=StrataAugment(seed=args.seed))
    trainer.train()
    train_s = time.time() - t0
    print(f"training wall time: {train_s/60:.1f} min")

    best = cfg["trainer"]["export"]
    if not os.path.exists(best):
        raise SystemExit(f"no exported weights at {best}")

    sc, degen, pairs = evaluate(cfg, best, "test")
    print()
    print(format_score(sc, scope="rec-only (GT boxes)", testset="VinText test-500 (real held-out)"))

    res = dict(
        arm=args.arm, seed=args.seed, iters=args.iters, hp=HP, train_seconds=train_s,
        augmentor=DESCRIPTION, n_real=n_real, n_synth=n_syn,
        synth_set=(SYNTH if args.arm == "C" else None),
        synth_manifest=(f"data/crops/{SYNTH}/manifest.json" if args.arm == "C" else None),
        scope="rec-only", testset="VinText test-500 (unseen_test_images)",
        normalization="NFC (axes: NFD)",
        n_instances=sc.n_samples, n_chars=sc.char_ref,
        cer=sc.cer, wer=sc.wer, exact=sc.exact,
        axis1_base=sc.base_acc, axis2_modifier=sc.mod_acc, axis3_tone=sc.tone_acc,
        axis_n=dict(base=sc.base_n, modifier=sc.mod_n, tone=sc.tone_n),
        degenerate=degen,
    )
    with open(f"{outdir}/result.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    with open(f"{outdir}/predictions.tsv", "w", encoding="utf-8") as f:
        for gt, pr in pairs:
            f.write(f"{gt}\t{pr}\n")
    print(f"\nwrote {outdir}/result.json")


if __name__ == "__main__":
    main()
