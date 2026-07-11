"""The crop-level synthetic generator (DATA_ENGINE §2, §6).

Produces (crop BGR, NFC label) pairs sized like real VinText GT-box crops. The thesis
(DATA_ENGINE §1): the pretrained prior already reads clean Vietnamese, so the ENTIRE value
is document->scene domain transfer -- degradation realism is THE lever. Degradation is built
and applied in the MEASURED Stage-1 priority order (DATA_ENGINE §12), not the doc's original
tone-first guess:

    GEOMETRIC (worst stratum, tilt>=20deg = 30.3% CER)  -> perspective / rotation / shear
    PHOTOMETRIC (contrast<0.2 = 27.6%)                  -> illumination / low-contrast / glare
    RESOLUTION/BLUR (height<12px = 22.9%; tone visibility)-> downsample / defocus / motion / jpeg / noise

Coverage targets (real VinText train crops, engine/imstats): sharpness p5=94 med=1950,
contrast p5=0.18 med=0.49, height p5=9 med=28 p95=150, bg_edge p95=0.36. The degradation
ranges below are [CONJECTURE], tuned to COVER those (the §7 audit checks, before training).

Per-sample label integrity (DATA_ENGINE §2): every char must map to a real glyph in the
chosen font (cmap check); else another font is drawn. The font gate (§5) makes this rare.
"""
from __future__ import annotations

import json
import os
import random
import sys

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")

FONT_DIR = os.path.join("data", "synth", "fonts")
BG_DIR = os.path.join("data", "synth", "bg")

# ------------------------------------------------------------------ default config
# every value here is [CONJECTURE], tuned by the §7 audit + §8 Gate-A loop. Grouped by the
# §12 degradation order. Probabilities are per-crop application chances.
DEFAULT_CFG = dict(
    # geometric (applied FIRST, at working resolution)
    p_perspective=0.75, persp_jitter=0.08,     # corner jitter as frac of size
    p_rotate=0.72, rot_deg=15.0,               # +-, covers the tilt>=20 worst stratum tail
    p_shear=0.45, shear=0.18,
    p_curve=0.15, curve_amp=0.06,              # mild baseline curvature (frac of height)
    # --- severity budget (legibility hygiene, 2026-07-11) ---------------------
    # A single per-crop latent `sev` in [0,1] scales ALL heavy degradations coherently, so a
    # crop is mild OR hard as a whole, never independently-maxed on every axis at once (the
    # ~26% illegible fraction = training noise, DATA_ENGINE §8.2 bug-check b/d). sev is biased
    # LOW; the heaviest ops only engage at high sev; maxima are capped so hard crops stay
    # LEGIBLE. §7 hard-tail coverage is preserved because high-sev crops still hit low
    # contrast / blur / small size -- just not all-destroyed simultaneously.
    sev_bias=1.5,                              # sev = U^sev_bias  (higher -> more mass at low sev)
    # photometric
    p_illum=0.6, illum_strength=0.32,          # scaled by sev
    p_lowcontrast=0.5, contrast_min=0.42,      # a = 1 - sev*(1-contrast_min); floor keeps text readable
    p_glare=0.10, glare_strength=0.28, glare_sev=0.7,   # glare only when sev>glare_sev (blows highlights)
    p_shadow=0.22, shadow_off=0.06,
    # resolution / sensor (applied LAST, at/near target height)
    p_clean=0.30,                              # near-pristine crops -> cover the SHARP/high-contrast end
    supersample_max=1.8,
    p_defocus=0.6, defocus_sigma=1.5,          # sigma scales with sev; height-capped so tiny crops survive
    p_motion=0.35, motion_len=8, motion_sev=0.5,        # motion only when sev>motion_sev
    jpeg_qmin=34, jpeg_qmax=93,                # q = qmax - sev*(qmax-qmin); always applied
    p_noise=0.6, noise_sigma=9.0,              # sigma scales with sev
    # background / appearance
    p_real_bg=0.82,                            # else synthetic solid/gradient
    contrast_margin=95,                        # min text-vs-bg luminance gap (before degradation)
    pad_frac=0.08,                             # background margin around text (real GT crops are tight)
)


def load_fonts():
    m = json.load(open(os.path.join(FONT_DIR, "fonts_manifest.json"), encoding="utf-8"))
    fonts = []
    for e in m["fonts"]:
        fonts.append(dict(family=e["family"], path=e["path"],
                          cmap=_cmap(e["path"])))
    return fonts


def _cmap(path):
    tt = TTFont(path, fontNumber=0, lazy=True)
    cps = set()
    for t in tt["cmap"].tables:
        if t.isUnicode():
            cps.update(t.cmap.keys())
    tt.close()
    return cps


def load_bg_index():
    """Return (filenames, sampling_weights). Weights bias toward TEXTURED patches so the
    synthetic bg_edge distribution reaches the busy real tail (real text sits on busy
    backgrounds; uniform patch sampling over-picks smooth sky/wall)."""
    idx = [ln.strip() for ln in open(os.path.join(BG_DIR, "index.txt"), encoding="utf-8") if ln.strip()]
    cache = os.path.join(BG_DIR, "edge.json")
    if os.path.exists(cache):
        ed = json.load(open(cache, encoding="utf-8"))
    else:
        ed = {}
        for fn in idx:
            im = cv2.imread(os.path.join(BG_DIR, fn), cv2.IMREAD_GRAYSCALE)
            ed[fn] = float((cv2.Canny(im, 50, 150) > 0).mean()) if im is not None else 0.0
        json.dump(ed, open(cache, "w", encoding="utf-8"))
    w = [0.15 + ed.get(fn, 0.0) for fn in idx]   # texture-biased, floor keeps smooth patches
    return idx, w


# real crop height distribution (engine/imstats on VinText train): resampled so synthetic
# height COVERS real (p5=9, med=28, p95=150). Log-spaced buckets with real-ish weights.
_H_BUCKETS = [(8, 12), (12, 19), (19, 28), (28, 40), (40, 60), (60, 105), (105, 175)]
_H_WEIGHTS = [0.13, 0.15, 0.20, 0.18, 0.14, 0.11, 0.09]


class Generator:
    def __init__(self, corpus, fonts, bg_index, seed=0, cfg=None):
        self.corpus = corpus
        self.fonts = fonts
        if isinstance(bg_index, tuple):
            self.bg_index, self.bg_weights = bg_index
        else:
            self.bg_index, self.bg_weights = bg_index, None
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.cfg = dict(DEFAULT_CFG, **(cfg or {}))

    # ---- helpers -------------------------------------------------------------
    def _pick_font(self, text):
        order = self.rng.sample(range(len(self.fonts)), len(self.fonts))
        for i in order:
            f = self.fonts[i]
            if all((ord(c) in f["cmap"]) or c == " " for c in text):
                return f
        return None  # no font covers this string (should be ~never post-gate)

    def _target_height(self):
        i = self.rng.choices(range(len(_H_BUCKETS)), weights=_H_WEIGHTS, k=1)[0]
        lo, hi = _H_BUCKETS[i]
        return self.rng.randint(lo, hi)

    def _render_text_mask(self, text, font_path, px_h):
        """Tight alpha mask (H,W) uint8 of white text on black, at pixel height px_h."""
        font = ImageFont.truetype(font_path, px_h)
        pad = px_h
        est_w = int(px_h * 0.75 * max(1, len(text))) + 4 * pad
        canvas = Image.new("L", (est_w, px_h * 3), 0)
        d = ImageDraw.Draw(canvas)
        d.text((pad, pad), text, font=font, fill=255)
        arr = np.asarray(canvas)
        ys, xs = np.where(arr > 12)
        if len(xs) == 0:
            return None
        x0, x1 = xs.min(), xs.max() + 1
        y0, y1 = ys.min(), ys.max() + 1
        m = px_h // 6 + 1
        x0 = max(0, x0 - m); y0 = max(0, y0 - m)
        x1 = min(arr.shape[1], x1 + m); y1 = min(arr.shape[0], y1 + m)
        return arr[y0:y1, x0:x1]

    def _background(self, w, h):
        cfg = self.cfg
        if self.rng.random() < cfg["p_real_bg"] and self.bg_index:
            if self.bg_weights:
                fn = self.rng.choices(self.bg_index, weights=self.bg_weights, k=1)[0]
            else:
                fn = self.rng.choice(self.bg_index)
            bg = cv2.imread(os.path.join(BG_DIR, fn))
            if bg is not None:
                bh, bw = bg.shape[:2]
                # random crop a region >= (w,h) if possible then resize
                if bw > w and bh > h:
                    x = self.rng.randint(0, bw - w); y = self.rng.randint(0, bh - h)
                    bg = bg[y:y + h, x:x + w]
                else:
                    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)
                if bg.shape[:2] != (h, w):
                    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)
                return bg
        # synthetic background: solid or vertical gradient, plus fine texture so it is not
        # perfectly flat (real signage has grain; a flat bg under-represents real bg_edge).
        c1 = self.np_rng.integers(0, 256, 3)
        if self.rng.random() < 0.5:
            c2 = self.np_rng.integers(0, 256, 3)
            t = np.linspace(0, 1, h)[:, None, None]
            bg = (c1[None, None, :] * (1 - t) + c2[None, None, :] * t)
            bg = np.broadcast_to(bg, (h, w, 3)).astype(np.float32).copy()
        else:
            bg = np.full((h, w, 3), c1, dtype=np.float32)
        bg = bg + self.np_rng.normal(0, self.rng.uniform(2, 14), (h, w, 3))
        return np.clip(bg, 0, 255).astype(np.uint8)

    def _compose(self, mask):
        """Colorize the text mask and composite onto a background. Returns BGR canvas."""
        cfg = self.cfg
        th, tw = mask.shape
        pad = int(cfg["pad_frac"] * th) + 2
        H, W = th + 2 * pad, tw + 2 * pad
        bg = self._background(W, H).astype(np.float32)
        bg_lum = float(cv2.cvtColor(bg.astype(np.uint8), cv2.COLOR_BGR2GRAY).mean())

        # text colour: pick a random hue, then shift its luminance to CONTRAST the actual
        # background luminance by >= contrast_margin. This guarantees a readable, high-contrast
        # base; the low-contrast/illumination degradations then reduce it in a controlled way,
        # so the crop distribution spans real's contrast range instead of sitting at the low end.
        m = cfg["contrast_margin"]
        if bg_lum > 127:                       # light bg -> dark text
            tlum = self.rng.randint(0, max(1, int(bg_lum) - m))
        else:                                  # dark bg -> light text
            tlum = self.rng.randint(min(254, int(bg_lum) + m), 255)
        col = self.np_rng.integers(0, 256, 3).astype(np.float32)
        cur = 0.114 * col[0] + 0.587 * col[1] + 0.299 * col[2]   # BGR luminance
        tcol = np.clip(col + (tlum - cur), 0, 255).astype(np.float32)

        full = np.zeros((H, W), np.float32)
        full[pad:pad + th, pad:pad + tw] = mask
        alpha = (full / 255.0)[..., None]

        # optional cast shadow before the text
        if self.rng.random() < cfg["p_shadow"]:
            off = max(1, int(cfg["shadow_off"] * th))
            sh = np.zeros_like(full)
            sh[off:, off:] = full[:H - off, :W - off]
            sa = (sh / 255.0)[..., None] * 0.6
            bg = bg * (1 - sa)

        crop = bg * (1 - alpha) + tcol[None, None, :] * alpha
        return crop, bg_lum

    # ---- degradation groups (measured §12 order) -----------------------------
    def _geometric(self, img, light=False):
        cfg = self.cfg
        H, W = img.shape[:2]
        pj = cfg["persp_jitter"] * (0.35 if light else 1.0)
        rd = cfg["rot_deg"] * (0.4 if light else 1.0)
        # baseline curvature first (remap), then affine/perspective as one homography
        if not light and self.rng.random() < cfg["p_curve"]:
            amp = cfg["curve_amp"] * H * self.rng.uniform(-1, 1)
            xs = np.arange(W)
            shift = (amp * np.sin(np.linspace(0, np.pi, W))).astype(np.float32)
            mapx = np.tile(xs, (H, 1)).astype(np.float32)
            mapy = (np.arange(H)[:, None] + shift[None, :]).astype(np.float32)
            img = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
        dst = src.copy()
        if self.rng.random() < cfg["p_perspective"]:
            dst += self.np_rng.uniform(-pj, pj, (4, 2)).astype(np.float32) * [W, H]
        M = cv2.getPerspectiveTransform(src, dst)
        # rotation + shear folded into an affine, then combined
        ang = self.rng.uniform(-rd, rd) if self.rng.random() < cfg["p_rotate"] else 0
        R = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
        A = np.vstack([R, [0, 0, 1]])
        if not light and self.rng.random() < cfg["p_shear"]:
            sx = self.rng.uniform(-cfg["shear"], cfg["shear"])
            A = A @ np.float32([[1, sx, 0], [0, 1, 0], [0, 0, 1]])
        M = M @ A
        return cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REFLECT)

    def _photometric(self, img, sev):
        cfg = self.cfg
        H, W = img.shape[:2]
        img = img.astype(np.float32)
        if self.rng.random() < cfg["p_illum"]:
            gx, gy = self.rng.uniform(-1, 1), self.rng.uniform(-1, 1)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            g = (xx / W - 0.5) * gx + (yy / H - 0.5) * gy
            g = 1.0 + cfg["illum_strength"] * sev * g            # scaled by severity
            img = img * g[..., None]
        if sev > cfg["glare_sev"] and self.rng.random() < cfg["p_glare"]:
            cx, cy = self.rng.uniform(0, W), self.rng.uniform(0, H)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.exp(-(((xx - cx) / (0.3 * W)) ** 2 + ((yy - cy) / (0.3 * H)) ** 2))
            img = img + cfg["glare_strength"] * 255 * r[..., None] * self.rng.uniform(0.2, 0.7)
        if self.rng.random() < cfg["p_lowcontrast"]:
            # contrast retained = 1 at sev 0, floored at contrast_min at sev 1 (readable floor)
            a = 1.0 - sev * (1.0 - cfg["contrast_min"])
            mean = img.mean()
            img = mean + (img - mean) * a
            img = img + self.rng.uniform(-25, 25) * sev
        return np.clip(img, 0, 255).astype(np.uint8)

    def _resolution(self, img, target_h, clean=False, sev=0.0):
        cfg = self.cfg
        if img.dtype != np.uint8:                       # clean path skips _photometric's cast
            img = np.clip(img, 0, 255).astype(np.uint8)
        H, W = img.shape[:2]
        scale = target_h / H
        tw = max(4, int(round(W * scale)))
        img = cv2.resize(img, (tw, target_h),
                         interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        if clean:
            # near-pristine: cover the SHARP real end. 40% get NO jpeg (crispest), rest a
            # light high-quality jpeg.
            if self.rng.random() < 0.4:
                return img
            q = self.rng.randint(90, 98)
            ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
            if ok:
                img = cv2.imdecode(enc, cv2.IMREAD_COLOR)
            return img
        if self.rng.random() < cfg["p_defocus"]:
            # sigma scales with severity, capped relative to crop height (tiny crops survive)
            smax = min(cfg["defocus_sigma"] * (0.4 + 0.6 * sev), max(0.5, target_h / 12.0))
            s = self.rng.uniform(0.35, max(0.4, smax))
            k = int(2 * round(s) + 1)
            img = cv2.GaussianBlur(img, (k, k), s)
        if sev > cfg["motion_sev"] and self.rng.random() < cfg["p_motion"]:
            L = self.rng.randint(3, max(4, int(3 + (cfg["motion_len"] - 3) * sev)))
            ker = np.zeros((L, L), np.float32)
            ang = self.rng.uniform(0, np.pi)
            cx = (L - 1) / 2
            for i in range(L):
                x = int(round(cx + (i - cx) * np.cos(ang)))
                y = int(round(cx + (i - cx) * np.sin(ang)))
                if 0 <= x < L and 0 <= y < L:
                    ker[y, x] = 1
            ker /= max(ker.sum(), 1)
            img = cv2.filter2D(img, -1, ker)
        if self.rng.random() < cfg["p_noise"]:
            n = self.np_rng.normal(0, self.rng.uniform(2, max(2.5, cfg["noise_sigma"] * sev)), img.shape)
            img = np.clip(img.astype(np.float32) + n, 0, 255).astype(np.uint8)
        # jpeg always applied; quality scales inversely with severity
        q = int(round(cfg["jpeg_qmax"] - sev * (cfg["jpeg_qmax"] - cfg["jpeg_qmin"])))
        ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if ok:
            img = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        return img

    # ---- one crop ------------------------------------------------------------
    def generate(self):
        for _ in range(6):  # retry on rare font/empty-mask misses
            text = self.corpus.sample()
            font = self._pick_font(text)
            if font is None:
                continue
            target_h = self._target_height()
            clean = self.rng.random() < self.cfg["p_clean"]
            # bias supersample low (ss^2) so most crops stay sharp; clean crops near 1x
            ss = 1.0 + (self.rng.random() ** 2) * (self.cfg["supersample_max"] - 1.0)
            if clean:
                ss = self.rng.uniform(1.0, 1.25)
            work_h = int(max(22, min(200, target_h * ss)))
            mask = self._render_text_mask(text, font["path"], work_h)
            if mask is None or mask.shape[1] < 3:
                continue
            crop, _ = self._compose(mask)
            crop = self._geometric(crop, light=clean)   # geometry always applies (scene angles)
            # per-crop severity latent (biased low); scales photometric + sensor coherently so
            # crops are mild-OR-hard, not independently-destroyed on every axis (legibility hygiene)
            sev = self.rng.random() ** self.cfg["sev_bias"]
            if not clean:
                crop = self._photometric(crop, sev)
            crop = self._resolution(crop, target_h, clean=clean, sev=sev)
            if crop.shape[0] < 3 or crop.shape[1] < 3:
                continue
            return crop, text, font["family"]
        return None
