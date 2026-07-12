"""The §14 real-data-budget axis (EVAL_PROTOCOL §14 / §14.1 FROZEN spec).

The question with actual decision value: **how much real annotation can synthetic replace?**
Full-real already answered "does synthetic add on top of ALL my real data?" -- NO (C≈B, RED).

`[LOCKED]` per §14.1:
  * r in {10,25,50}% NESTED fixed-seed subsets (r=100% is REUSED: baseline A / the leg run).
  * Arms: real(r) ONLY  vs  real(r) + synth10k_leg (the hygiene-clean 10k, FROZEN, SAME set at
    every r -- one variable at a time).
  * Config = the §6 OPERATING point: DEFAULT image_aug (NOT Attempt-1's strata aug -- that
    question is answered), fixed HP, iters=12,000, best-val model selection.
  * Sampling: UNIFORM over the pooled set. The synthetic FRACTION therefore grows as r shrinks
    (~28% at r=100% -> ~79% at r=10%). That is the PHENOMENON under study (a practitioner with
    r real + 10k synth trains on all of it), not a confound.
  * Val: the FULL val-300 at every r (model-selection quality held constant; the budget question
    is about TRAIN labels). Stated, not hidden.
  * Fixed iters + best-val export: at low r the epoch count balloons (~150 real-epochs at r=10%
    real-only); best-val selection guards overfit. Val curve is logged for the per-r sanity report.

k=3 seeds. This script trains+evaluates ONE (r, arm, seed). It does NOT declare a gate.
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

SYNTH = "synth10k_leg"     # FROZEN: the same hygiene-clean 10k at every r
ROOT = "data/crops"


def synth_set(r, arm):
    """The synthetic set this arm pools in.

    arm=synth  -> synth10k_leg: Source B drawn from the FULL train transcript bank. The
                  pre-registered primary run (§14.1).
    arm=strict -> synth10k_strict_r{r}: EVAL_PROTOCOL §14.2 (C1). Source B restricted to the
                  r-subset's OWN transcripts -- transcripts ARE labels, and a practitioner at
                  budget r holds only r% of them. Identical fonts/degradation/seed; the bank is
                  the ONLY variable. The HEADLINE quotes this arm.
    arm=clean  -> synth10k_clean_r{r}: EVAL_PROTOCOL §14.4(A) CLEAN-RENDER CONTROL. Identical to the
                  strict set (same corpus/fonts/strict bank/seed) except the ENTIRE degradation stack
                  is OFF. ATTRIBUTION ONLY: does the realism machinery carry the +2.783pp, or does any
                  10k of extra crops? The headline does not move either way, and this is NOT a §8.1
                  re-gate attempt.
    """
    if arm == "clean":
        return f"synth10k_clean_r{r}"
    return SYNTH if arm == "synth" else f"synth10k_strict_r{r}"


def real_annotation(r):
    return "annotation_train.txt" if r == 100 else f"annotation_train_r{r}.txt"


def build_annotation(r, arm):
    """Return the train-annotation filename for this (r, arm), building the pooled one if needed."""
    real_ann = real_annotation(r)
    if arm == "real":
        return real_ann
    syn_name = synth_set(r, arm)
    out = f"annotation_budget_r{r}_{arm}.txt"
    real = [ln for ln in open(os.path.join(ROOT, real_ann), encoding="utf-8") if ln.strip()]
    syn = [ln for ln in open(os.path.join(ROOT, f"annotation_{syn_name}.txt"), encoding="utf-8") if ln.strip()]
    with open(os.path.join(ROOT, out), "w", encoding="utf-8") as f:
        f.writelines(l if l.endswith("\n") else l + "\n" for l in real + syn)
    frac = 100.0 * len(syn) / (len(real) + len(syn))
    print(f"pooled: {len(real)} real + {len(syn)} synth = {len(real)+len(syn)}  "
          f"(synthetic fraction {frac:.1f}% -- uniform pooled sampling, §14.1)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r", type=int, required=True, choices=[10, 25, 50, 100])
    ap.add_argument("--arm", choices=["real", "synth", "strict", "clean"], required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--iters", type=int, default=HP["iters"])   # FIXED = 12000
    args = ap.parse_args()

    if args.arm == "strict" and args.r not in (10, 25):
        raise SystemExit("strict-bank arm (§14.2 C1) is defined at the GREEN points r=10 and r=25 only")
    if args.arm == "clean" and args.r != 10:
        raise SystemExit("clean-render control (§14.4 A) is defined at the headline point r=10 only")

    ann = build_annotation(args.r, args.arm)
    n_real = sum(1 for ln in open(os.path.join(ROOT, real_annotation(args.r)), encoding="utf-8") if ln.strip())
    n_syn = 0
    if args.arm != "real":
        n_syn = sum(1 for ln in open(os.path.join(ROOT, f"annotation_{synth_set(args.r, args.arm)}.txt"),
                                     encoding="utf-8") if ln.strip())

    dataset = f"budget_r{args.r}_{args.arm}"
    outdir = f"runs/{dataset}_seed{args.seed}"
    os.makedirs(outdir, exist_ok=True)
    set_seed(args.seed)

    cfg = load_config()
    cfg["dataset"] = dict(
        name=dataset, data_root="./data/crops/",
        train_annotation=ann, valid_annotation="annotation_val.txt",   # FULL val-300 at every r
        image_height=HP["image_height"], image_min_width=HP["image_min_width"],
        image_max_width=HP["image_max_width"],
    )
    cfg["trainer"] = dict(
        batch_size=HP["batch_size"], print_every=200, valid_every=HP["valid_every"],
        iters=args.iters, export=f"{outdir}/best.pth", checkpoint=f"{outdir}/ckpt.pth",
        log=f"{outdir}/train.log", metrics=HP["metrics"],
    )
    cfg["optimizer"] = dict(max_lr=HP["max_lr"], pct_start=HP["pct_start"])
    # DEFAULT augmentation (§6 operating point) -- NOT Attempt-1's strata aug
    cfg["aug"] = dict(image_aug=HP["image_aug"], masked_language_model=HP["masked_language_model"])
    cfg["dataloader"] = dict(num_workers=0, pin_memory=True)
    cfg["pretrain"] = "weights/vgg_transformer.pth"
    cfg["weights"] = "weights/vgg_transformer.pth"

    from vietocr.model.trainer import Trainer

    real_epochs = args.iters * HP["batch_size"] / max(1, n_real + n_syn)
    print(f"=== BUDGET r={args.r}%  arm={args.arm}  seed={args.seed}  "
          f"real={n_real} synth={n_syn}  iters={args.iters} (FIXED) ===")
    print(f"    epochs over the pooled set: ~{real_epochs:.1f}  (default image_aug; best-val export)")
    t0 = time.time()
    trainer = Trainer(cfg, pretrained=True)     # default augmentor (ImgAugTransformV2)
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
        budget_r=args.r, arm=args.arm, seed=args.seed, iters=args.iters, hp=HP,
        train_seconds=train_s, n_real=n_real, n_synth=n_syn,
        synth_set=(None if args.arm == "real" else synth_set(args.r, args.arm)),
        source_b_bank=("full train transcript bank (§14.1 primary)" if args.arm == "synth" else
                       f"STRICT: r={args.r}% subset transcripts ONLY (§14.2 C1)"
                       if args.arm in ("strict", "clean") else None),
        degradation=("OFF -- §14.4(A) clean-render CONTROL (attribution ablation; §7 audit FAILs by "
                     "design, non-gating; headline unaffected)" if args.arm == "clean" else
                     "ON (shipped generator)" if args.arm != "real" else None),
        subset_manifest="data/crops/budget_subsets_manifest.json",
        augmentation="default image_aug (§6 operating point)",
        sampling="uniform pooled (§14.1)",
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
