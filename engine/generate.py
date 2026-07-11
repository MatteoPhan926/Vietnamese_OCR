"""Generate a synthetic crop set to disk + the reproducibility manifest (DATA_ENGINE §10 /
EVAL_PROTOCOL §11). Crops land under data/crops/synth<N>/ (same data_root as the real crops)
so the Gate-A trainer can consume real + synthetic from one lmdb.

Firewall (EVAL_PROTOCOL §10): the corpus draws only from wiki_vi + VinText TRAIN labels, and
backgrounds only from TRAIN images, so no val/test signal enters training. The label written
is the NFC string the generator rendered (per-sample cmap integrity already enforced).

The manifest records everything needed to regenerate byte-for-recipe: fonts + verdicts,
corpus mixture + snapshot, the full degradation config, count, seed, timing, and the §7
distribution-audit verdict computed on THIS generated set.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import cv2

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from engine.audit import real_stats, report  # noqa: E402
from engine.corpus import SCENE_TXT, WIKI_TSV, Corpus, build_strict_scene_bank  # noqa: E402
from engine.imstats import crop_stats, summarize  # noqa: E402
from engine.render import DEFAULT_CFG, Generator, load_bg_index, load_fonts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default=None)
    ap.add_argument("--strata", action="store_true",
                    help="DATA_ENGINE §8.3: over-represent the MEASURED failure strata "
                         "(tilt/low-contrast/tiny/short) instead of matching real's marginals")
    ap.add_argument("--strict-bank-r", type=int, default=None, choices=[10, 25, 50],
                    help="EVAL_PROTOCOL §14.2 (C1): restrict Source B to the r-subset's OWN "
                         "transcripts (transcripts ARE labels -- a budget-r practitioner holds "
                         "only r%% of them). Everything else identical.")
    args = ap.parse_args()
    name = args.name or f"synth{args.n // 1000}k"

    outdir = os.path.join("data", "crops", name)
    imgdir = os.path.join(outdir, "img")
    os.makedirs(imgdir, exist_ok=True)

    fonts = load_fonts()
    bg = load_bg_index()

    # §14.2 (C1): Source B from the r-subset's own transcripts, or the full train bank (default).
    scene_bank = None
    if args.strict_bank_r is not None:
        scene_bank = build_strict_scene_bank(args.strict_bank_r)

    # strata mode also over-samples the short (1-2 char) crop stratum in the corpus
    corpus = Corpus(seed=args.seed, short_rate=0.20 if args.strata else 0.0, scene_bank=scene_bank)
    gen = Generator(corpus, fonts, bg, seed=args.seed, strata=args.strata)

    lines = []
    stats = []
    t0 = time.time()
    n = miss = 0
    while n < args.n:
        r = gen.generate()
        if r is None:
            miss += 1
            continue
        crop, text, fam = r
        rel = f"{name}/img/{n:06d}.jpg"
        cv2.imwrite(os.path.join("data", "crops", rel), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        assert "\t" not in text and "\n" not in text
        lines.append(f"{rel}\t{text}")
        if n % 5 == 0:                      # audit a 20% sample (fast, representative)
            stats.append(crop_stats(crop))
        n += 1
        if n % 2000 == 0:
            print(f"  {n}/{args.n}  ({(time.time()-t0):.0f}s)")
    gen_s = time.time() - t0

    ann = os.path.join("data", "crops", f"annotation_{name}.txt")
    with open(ann, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # §7 audit on the actually-generated crops
    real = real_stats()
    synth = summarize(stats)
    print(f"\n=== §7 audit on generated {name} ({len(stats)} sampled) ===")
    audit_pass = bool(report(real, synth))

    manifest = dict(
        name=name, count=n, seed=args.seed,
        strata_targeted=bool(args.strata),
        strata_note=("DATA_ENGINE §8.3 Attempt 1: generation re-weighted to OVER-REPRESENT the "
                     "measured failure strata (geometric tilt / contrast<0.20 / height<12px / "
                     "1-2-char), NOT to match real's marginals." if args.strata else
                     "marginal-matched to real (§7 audit)"),
        generation_seconds=round(gen_s, 1), ms_per_crop=round(1000 * gen_s / n, 2),
        font_misses=miss,
        annotation=ann, image_dir=imgdir,
        fonts_manifest="data/synth/fonts/fonts_manifest.json",
        n_fonts=len(fonts),
        corpus=dict(
            source_A="wiki_vi (HF wikimedia/wikipedia 20231101.vi, rev b04c8d1)",
            source_A_bank=WIKI_TSV,
            source_B=("VinText TRAIN-split transcripts (verbatim, firewall=train only)"
                      if scene_bank is None else
                      f"STRICT-BANK (§14.2 C1): ONLY the r={args.strict_bank_r}% subset's own "
                      f"transcripts -- no label text beyond the stated budget"),
            source_B_bank=scene_bank or SCENE_TXT,
            source_B_bank_size=len(corpus.scene),
            source_B_prob=corpus.source_b_prob,
            strict_bank_r=args.strict_bank_r,
        ),
        degradation_config=DEFAULT_CFG,
        bg_patches="data/synth/bg (text-free, VinText TRAIN images only, texture-weighted)",
        degradation_order="MEASURED §12: geometric -> photometric -> resolution/blur",
        s7_audit_pass=audit_pass,
        s7_audit=dict(real=real, synth=synth),
        firewall="corpus + backgrounds from wiki_vi + VinText TRAIN only; no val/test (EVAL_PROTOCOL §10)",
        label_normalization="NFC; per-sample cmap glyph-integrity enforced (DATA_ENGINE §2)",
    )
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nwrote {n} crops -> {imgdir}")
    print(f"annotation -> {ann}")
    print(f"manifest   -> {outdir}/manifest.json")
    print(f"generation: {gen_s:.0f}s ({1000*gen_s/n:.1f} ms/crop); 200k ~= {200000*gen_s/n/60:.0f} min")
    print(f"§7 audit on generated set: {'PASS' if audit_pass else 'FAIL — do NOT train, re-diagnose (§8)'}")


if __name__ == "__main__":
    main()
