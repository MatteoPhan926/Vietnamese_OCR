"""Re-derive the frozen instance/char counts from the ONE shared parser (scripts/vintext.py).

This is the number the docs must cite. If this script and EVAL_PROTOCOL §13 E1 ever
disagree, the doc is wrong.
"""
import sys
import unicodedata as ud

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from scripts.vintext import SPLITS, iter_instances  # noqa: E402

print(f"{'split':8s} {'scorable':>9s} {'NFC chars':>10s} {'words':>8s} {'nonscorable':>12s}")
tot = [0, 0, 0, 0]
for split in SPLITS:
    n = chars = words = 0
    for inst in iter_instances(split, scorable_only=True):
        n += 1
        chars += len(ud.normalize("NFC", inst.text))
        words += len(inst.text.split())
    nons = sum(1 for i in iter_instances(split, scorable_only=False) if not i.scorable)
    print(f"{split:8s} {n:9d} {chars:10d} {words:8d} {nons:12d}")
    tot = [tot[0] + n, tot[1] + chars, tot[2] + words, tot[3] + nons]
print(f"{'ALL':8s} {tot[0]:9d} {tot[1]:10d} {tot[2]:8d} {tot[3]:12d}")
