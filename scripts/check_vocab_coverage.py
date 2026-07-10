"""Stage 0.2 — can the locked vocab even represent VinText's ground truth?

Any GT character absent from the model vocab is UNPREDICTABLE: it contributes an
irreducible CER floor that is a property of the vocab, not of the model. Measuring
it now stops us from later attributing that floor to the recognizer (or to synthetic
data failing to fix it).
"""
import collections
import os
import sys
import unicodedata as ud

import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.vintext import SPLITS, iter_instances  # noqa: E402

cfg = yaml.safe_load(open("configs/vgg_transformer_pinned.yml", encoding="utf-8"))
vocab = set(cfg["vocab"])
print(f"vocab size: {len(vocab)} distinct chars")

for split in SPLITS:
    charcount = collections.Counter()
    inst_total = inst_bad = 0
    for inst in iter_instances(split, scorable_only=True):
        t = ud.normalize("NFC", inst.text)
        charcount.update(t)
        inst_total += 1
        if any(c not in vocab for c in t):
            inst_bad += 1

    oov = {c: n for c, n in charcount.items() if c not in vocab}
    n_chars = sum(charcount.values())
    n_oov = sum(oov.values())
    print(f"\n--- {split} ---")
    print(f"  instances: {inst_total}   chars: {n_chars}")
    print(f"  OOV chars: {n_oov} ({100*n_oov/n_chars:.4f}% of chars)")
    print(f"  instances containing >=1 OOV char: {inst_bad} ({100*inst_bad/inst_total:.4f}%)")
    if oov:
        items = sorted(oov.items(), key=lambda kv: -kv[1])
        print("  OOV inventory:")
        for c, n in items:
            print(f"    {c!r}  U+{ord(c):04X}  {ud.name(c,'<no name>')}  x{n}")
