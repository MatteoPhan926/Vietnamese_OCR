"""Strata-targeted AUGMENTATION of REAL crops (DATA_ENGINE §8.4 arms B and C).

§8.4: the Gate-A comparator must be the STRONGEST real-only model, not the default-augmented
one. STEP 0 verified that the installed vietocr `image_aug` is WEAK on exactly the measured
failure strata: it has NO rotation/shear, NO gaussian blur, NO noise, NO JPEG, NO downsample,
and only a 0.01-0.05 perspective + a fixed 3-px motion blur. So the baseline was never shown
to be non-starved on augmentation.

This augmentor manufactures the Stage-1 measured failure strata (DATA_ENGINE §12) FROM REAL
CROPS -- real content, hard presentation:
    GEOMETRIC   (tilt>=20deg stratum, 30.3% CER) -> strong perspective + shear + rotation
    PHOTOMETRIC (contrast<0.20 stratum, 27.6%)   -> crush contrast below Michelson 0.20
    RESOLUTION  (height<12px stratum, 22.9%)     -> downsample to 8-12px, then back up

Applied ONE stratum at a time (real hard crops are hard on one axis, mostly) so the crop stays
LEGIBLE -- the lesson of the §8.2 over-degradation bug-check.

NOTE (recorded, and flagged to the brain): crops are perspective-RECTIFIED by crop_quad at BOTH
train and test time, so the model never sees a literally 20-degree-rotated crop. The tilt
stratum's difficulty survives rectification as RESIDUAL geometric distortion (imperfect quad
fit, foreshortening), so "geometric" is manufactured as strong perspective + shear + moderate
rotation rather than a literal >=20deg rotation.

ARMS B AND C USE THE *SAME* AUGMENTOR. That is what makes C-B the pure synthetic contribution
at matched augmentation -- the only honest answer to "was generating the synthetic worth it?"
"""
from __future__ import annotations

import random

import albumentations as A
import cv2
import numpy as np
from PIL import Image

from vietocr.loader.aug import RandomDottedLine

# §12 measured priority: geometric > photometric > resolution
STRATA_W = dict(geometric=0.40, photometric=0.30, resolution=0.30)
P_STRATA = 0.5          # half the crops get one heavy stratum; the rest see only the base aug


class StrataAugment:
    """Callable PIL->PIL, drop-in for vietocr's ImgAugTransformV2.

    Applied to the NATIVE-resolution crop, BEFORE process_image resizes to h=32
    (vietocr/loader/dataloader.py read_data), so downsampling really does emulate small text.
    """

    def __init__(self, p_strata: float = P_STRATA, seed: int | None = None):
        self.p_strata = p_strata
        self.rng = random.Random(seed)
        # BASE = exactly the default vietocr aug, so arm B is a strict SUPERSET of arm A's aug
        # (raising the bar, never lowering it -- EVAL_PROTOCOL §15).
        self.base = A.Compose([
            A.InvertImg(p=0.2),
            A.ColorJitter(p=0.2),
            A.MotionBlur(blur_limit=3, p=0.2),
            A.RandomBrightnessContrast(p=0.2),
            A.Perspective(scale=(0.01, 0.05)),
            RandomDottedLine(),
        ])
        # GEOMETRIC stratum: strong residual distortion
        self.geo = A.Compose([
            A.Affine(rotate=(-20, 20), shear=(-18, 18), scale=(0.9, 1.1),
                     border_mode=cv2.BORDER_REPLICATE, p=1.0),
            A.Perspective(scale=(0.06, 0.15), border_mode=cv2.BORDER_REPLICATE, p=0.8),
        ])

    # ---- strata ops (numpy BGR/RGB uint8) ------------------------------------
    def _photometric(self, img):
        """Crush contrast below the measured <0.20 Michelson stratum, keeping text readable."""
        f = img.astype(np.float32)
        target = self.rng.uniform(0.08, 0.20)          # target Michelson contrast
        g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
        p5, p95 = np.percentile(g, 5), np.percentile(g, 95)
        cur = (p95 - p5) / (p95 + p5 + 1e-6)
        if cur > 1e-3:
            a = min(1.0, target / cur)                 # scale factor toward the target
            mean = f.mean()
            f = mean + (f - mean) * a
        f = f + self.rng.uniform(-25, 25)              # random level (light/dark scene)
        return np.clip(f, 0, 255).astype(np.uint8)

    def _resolution(self, img):
        """Emulate the height<12px stratum: downsample to 8-12px tall, then back up."""
        h, w = img.shape[:2]
        th = self.rng.randint(8, 12)
        if h <= th:
            return img
        tw = max(4, int(round(w * th / h)))
        small = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

    def __call__(self, img):
        arr = np.array(img)                            # PIL RGB -> numpy
        if self.rng.random() < self.p_strata:
            names = list(STRATA_W)
            which = self.rng.choices(names, weights=[STRATA_W[n] for n in names], k=1)[0]
            # legibility guard (§8.2 lesson): rotating/shearing an already-tiny crop wipes it.
            # Small crops are ALREADY in the hard 'resolution' stratum, so redirect instead.
            if which == "geometric" and arr.shape[0] < 16:
                which = "photometric"
            if which == "geometric":
                arr = self.geo(image=arr)["image"]
            elif which == "photometric":
                arr = self._photometric(arr)
            else:
                arr = self._resolution(arr)
        arr = self.base(image=arr)["image"]            # base aug always (superset of arm A)
        return Image.fromarray(arr)


DESCRIPTION = dict(
    name="StrataAugment",
    base="vietocr ImgAugTransformV2 (InvertImg .2 | ColorJitter .2 | MotionBlur(3) .2 | "
         "RandomBrightnessContrast +-0.2 .2 | Perspective(0.01-0.05) .5 | RandomDottedLine .5)",
    p_strata=P_STRATA,
    strata_weights=STRATA_W,
    geometric="Affine(rotate +-20, shear +-18, scale 0.9-1.1) + Perspective(0.06-0.15)",
    photometric="crush Michelson contrast to 0.08-0.20 + level shift +-25",
    resolution="downsample to height 8-12px then upsample (emulates the <12px stratum)",
    note="one stratum at a time (legibility); applied to native-res crop before h=32 resize",
)
