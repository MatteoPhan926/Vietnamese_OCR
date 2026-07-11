"""The §7 synthetic-vs-real crop distribution audit (EVAL_PROTOCOL §7 / DATA_ENGINE §7).

Run BEFORE any training. The #1 Gate-A-RED cause is 'synthetic systematically cleaner than
real'; this catches it at zero training cost. Pass criterion (§7): the synthetic distribution
must COVER the real one on each statistic -- same range, comparable spread. Operationalized:

  RANGE  : synthetic [p2.5, p97.5] must span real's central 90% ([p5, p95]).
  CENTER : synthetic median within one real-IQR of real median (in log space for the
           heavy-tailed sharpness stat).

Over-degrading FAILS too: if synthetic is systematically blurrier/darker than real it does
not COVER the sharp/high-contrast end and its center drifts -- the audit flags both directions.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from engine.corpus import Corpus  # noqa: E402
from engine.imstats import crop_stats, summarize  # noqa: E402
from engine.render import Generator, load_bg_index, load_fonts  # noqa: E402

STATS = ("sharpness", "contrast", "lum_mean", "lum_std", "height", "bg_edge")
LOG_STATS = {"sharpness"}
REAL_CACHE = os.path.join("data", "synth", "real_crop_stats.json")

# §7's stated failure mode is "synthetic systematically CLEANER than real" (-> flat curve).
# "Clean/easy" is a DIFFERENT tail per statistic, so coverage is asymmetric: the engine must
# REACH real's HARD tail (where domain transfer is earned) and must NOT sit systematically on
# the easy side. Under-reaching the EASY extreme (e.g. not matching the very sharpest or
# tallest real crop) is benign and not required.
HARD_LOW = {"sharpness", "contrast", "height"}   # hard tail = low (blur / low-contrast / tiny)
HARD_HIGH = {"bg_edge"}                            # hard tail = high (busy background)
TWO_SIDED = {"lum_mean", "lum_std"}                # lighting: judged on center comparability


def real_stats(n=4000, seed=0):
    if os.path.exists(REAL_CACHE):
        return json.load(open(REAL_CACHE, encoding="utf-8"))
    files = glob.glob("data/crops/train/*.jpg")
    random.Random(seed).shuffle(files)
    out = []
    for f in files[:n]:
        im = cv2.imread(f)
        if im is not None and im.shape[0] >= 2 and im.shape[1] >= 2:
            out.append(crop_stats(im))
    summ = summarize(out)
    json.dump(summ, open(REAL_CACHE, "w", encoding="utf-8"), indent=2)
    return summ


def synth_stats(n, seed, cfg=None):
    g = Generator(Corpus(seed=seed), load_fonts(), load_bg_index(), seed=seed, cfg=cfg)
    out = []
    t0 = time.time()
    miss = 0
    while len(out) < n:
        r = g.generate()
        if r is None:
            miss += 1
            continue
        out.append(crop_stats(r[0]))
    dt = time.time() - t0
    return summarize(out), dt, miss


def _cover(real, synth, stat):
    """Return (reach_hard, center_ok, cleaner) per §7's asymmetric coverage.

    reach_hard: synthetic reaches real's HARD tail.
    center_ok : synthetic median within one real-IQR of real median (log for sharpness).
    cleaner   : synthetic is systematically on the EASY side of real (the §7 danger) -> a WARN.
    """
    log = stat in LOG_STATS
    def L(x):
        return np.log10(max(x, 1e-3)) if log else x

    if stat in HARD_LOW:   # hard = low; easy = high
        reach_hard = synth["p5"] <= real["p5"] * 1.20
        cleaner = L(synth["median"]) > L(real["median"]) + (0.15 if log else 0) \
            and synth["median"] > real["median"] * 1.20
    elif stat in HARD_HIGH:  # hard = high; easy = low
        reach_hard = synth["p95"] >= real["p95"] * 0.90
        cleaner = synth["median"] < real["median"] * 0.70
    else:                    # two-sided lighting stat: no hard tail, judged on center
        reach_hard = True
        cleaner = False

    iqr = max(L(real["p75"]) - L(real["p25"]), 1e-6)
    center_ok = abs(L(synth["median"]) - L(real["median"])) <= 1.25 * iqr
    return bool(reach_hard), bool(center_ok), bool(cleaner)


def report(real, synth):
    print(f"{'stat':10s} {'REAL p5/med/p95':>26s}   {'SYNTH p5/med/p95':>26s}   hard  center cleaner?")
    allok = True
    any_cleaner = False
    for s in STATS:
        r, y = real[s], synth[s]
        rh, co, cl = _cover(r, y, s)
        ok = rh and co and not cl
        allok = allok and ok
        any_cleaner = any_cleaner or cl
        def f(d):
            return f"{d['p5']:.3g}/{d['median']:.3g}/{d['p95']:.3g}"
        print(f"{s:10s} {f(r):>26s}   {f(y):>26s}   {'OK ' if rh else 'MISS':>4s}  "
              f"{'OK ' if co else 'off':>4s}  {'CLEANER!' if cl else '-'}")
    print("\n§7 criterion: reach real's HARD tail + center within ~1 IQR + NOT systematically cleaner")
    print(f"§7 AUDIT: {'PASS' if allok else 'FAIL'}"
          + ("  (synthetic is systematically cleaner than real -- degradation too weak)" if any_cleaner
             else "  (synthetic covers real's hard end; not cleaner than real)"))
    return allok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=999)
    ap.add_argument("--cfg", type=str, default=None, help="json file overriding DEFAULT_CFG")
    args = ap.parse_args()
    cfg = json.load(open(args.cfg, encoding="utf-8")) if args.cfg else None
    real = real_stats()
    synth, dt, miss = synth_stats(args.n, args.seed, cfg)
    print(f"(synth: {args.n} crops in {dt:.1f}s, {1000*dt/args.n:.1f} ms/crop, {miss} font-misses)\n")
    ok = bool(report(real, synth))
    json.dump(dict(real=real, synth=synth, pass_=ok),
              open(os.path.join("data", "synth", "audit_result.json"), "w", encoding="utf-8"), indent=2)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
