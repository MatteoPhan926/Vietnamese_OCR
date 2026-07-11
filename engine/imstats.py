"""Image statistics for the §7 synthetic-vs-real distribution audit (EVAL_PROTOCOL §7 /
DATA_ENGINE §7). The #1 Gate-A-RED cause is 'synthetic is systematically cleaner than real',
so before spending a training run we check the synthetic distribution COVERS the real one on:

  sharpness  -- Laplacian variance (focus/blur; the tone-killer axis)
  contrast   -- Michelson (p95-p5)/(p95+p5) on luminance
  lum_mean   -- mean luminance (lighting)
  lum_std    -- luminance spread
  height     -- crop pixel height (resolution proxy; small text)
  bg_edge    -- edge density (Canny) = background-complexity proxy

Same function on both real and synthetic crops so the comparison is apples-to-apples.
"""
from __future__ import annotations

import numpy as np


def crop_stats(bgr: np.ndarray) -> dict:
    import cv2

    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = g.shape[:2]
    lap = cv2.Laplacian(g, cv2.CV_64F).var()
    p5, p95 = np.percentile(g, 5), np.percentile(g, 95)
    contrast = (p95 - p5) / (p95 + p5 + 1e-6)
    edges = cv2.Canny(g, 50, 150)
    return dict(
        sharpness=float(lap),
        contrast=float(contrast),
        lum_mean=float(g.mean()),
        lum_std=float(g.std()),
        height=int(h),
        width=int(w),
        bg_edge=float((edges > 0).mean()),
    )


def summarize(stats_list, keys=("sharpness", "contrast", "lum_mean", "lum_std", "height", "bg_edge")):
    out = {}
    for k in keys:
        v = np.array([s[k] for s in stats_list], dtype=float)
        out[k] = dict(
            p5=float(np.percentile(v, 5)), p25=float(np.percentile(v, 25)),
            median=float(np.percentile(v, 50)),
            p75=float(np.percentile(v, 75)), p95=float(np.percentile(v, 95)),
            min=float(v.min()), max=float(v.max()), mean=float(v.mean()),
        )
    return out
