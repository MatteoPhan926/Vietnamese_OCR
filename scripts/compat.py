"""Compatibility shims for the vendored pbcquoc/vietocr (last touched 2025-01) on a
modern numpy/torch stack. Import this BEFORE importing anything from `vietocr`.

Kept here, in version control, rather than as edits to the gitignored third_party/ clone,
so a fresh checkout reproduces the environment exactly (EVAL_PROTOCOL §11).

Each shim is behaviour-preserving:
  * np.fromstring(bytes, dtype=uint8) -> np.frombuffer(...). Removed in numpy 2.0.
    frombuffer is what fromstring's binary mode already did internally.
"""
import numpy as np

if not hasattr(np, "fromstring"):
    np.fromstring = lambda buf, dtype=float, **kw: np.frombuffer(buf, dtype=dtype, **kw)
else:
    _orig = np.fromstring

    def _fromstring(buf, dtype=float, **kw):
        if isinstance(buf, (bytes, bytearray, memoryview)):
            return np.frombuffer(buf, dtype=dtype, **kw)
        return _orig(buf, dtype=dtype, **kw)

    np.fromstring = _fromstring
