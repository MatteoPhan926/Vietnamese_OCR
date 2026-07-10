"""GT-box crop extraction for rec-only scope (EVAL_PROTOCOL §1).

rec-only = "VietOCR recognition GIVEN ground-truth boxes". VinText boxes are 4-point
quads, often rotated/sheared, so a naive axis-aligned bbox crop would feed the recognizer
background and neighbouring glyphs. We rectify each quad with a perspective warp to an
upright rectangle -- the standard scene-text rec-only preparation.

The quad's point order in VinText is the polygon as annotated; we canonicalise it to
(top-left, top-right, bottom-right, bottom-left) by angle about the centroid so the warp
does not mirror or rotate text by 90 degrees.
"""
from __future__ import annotations

import numpy as np


def order_quad(pts: np.ndarray) -> np.ndarray:
    """Canonicalise 4 points to TL, TR, BR, BL."""
    c = pts.mean(axis=0)
    # sort by angle around centroid -> consistent winding
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    pts = pts[np.argsort(ang)]
    # rotate so the point closest to the top-left of the bbox comes first
    start = np.argmin(pts.sum(axis=1))
    return np.roll(pts, -start, axis=0)


def crop_quad(img: np.ndarray, poly, min_side: int = 4):
    """Perspective-rectify the quad `poly` (8 ints) out of `img` (H,W,3 RGB).

    Returns None if the quad is degenerate (a real occurrence in scene-text GT).
    """
    import cv2

    pts = np.array(poly, dtype=np.float32).reshape(4, 2)
    pts = order_quad(pts)

    # target size from the quad's own side lengths
    w = int(round(max(np.linalg.norm(pts[0] - pts[1]), np.linalg.norm(pts[3] - pts[2]))))
    h = int(round(max(np.linalg.norm(pts[0] - pts[3]), np.linalg.norm(pts[1] - pts[2]))))
    if w < min_side or h < min_side:
        return None

    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(pts.astype(np.float32), dst)
    return cv2.warpPerspective(img, M, (w, h), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE)
