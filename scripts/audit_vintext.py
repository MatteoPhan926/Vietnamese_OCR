"""Stage 0.4 — audit the raw VinText annotations before defining any count.

Answers, by measurement (never assumption):
  * how many comma-separated fields per line (does a transcript contain commas?)
  * how many polygon points
  * the '###' do-not-care marker's prevalence
  * the Unicode normalization state of the shipped labels (NFC? NFD? mixed?)
  * the exact instance count per split, with and without do-not-care
"""
import collections
import os
import sys
import unicodedata as ud

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.join("data", "vietnamese")
SPLITS = {
    "train-1200": ("train_images", range(1, 1201)),
    "val-300": ("test_image", range(1201, 1501)),
    "test-500": ("unseen_test_images", range(1501, 2001)),
}


def read_label(idx):
    path = os.path.join(ROOT, "labels", f"gt_{idx}.txt")
    with open(path, encoding="utf-8") as fh:
        return [ln for ln in fh.read().splitlines() if ln.strip()]


def main():
    field_counts = collections.Counter()
    per_split = {}
    norm_state = collections.Counter()
    charset = collections.Counter()
    dontcare_forms = collections.Counter()

    bad_poly = []
    empty_transcripts = []

    for split, (_imgdir, idxs) in SPLITS.items():
        total = kept = dontcare = 0
        n_hash = n_empty = n_chars = n_words = 0
        for i in idxs:
            for line in read_label(i):
                parts = line.split(",")
                field_counts[len(parts)] += 1
                # VALIDATE, do not assume: the first 8 fields must all parse as ints.
                # If they do, the polygon is a 4-point quad and everything after
                # field 8 is transcript (which may legitimately contain commas).
                try:
                    [int(p) for p in parts[:8]]
                except ValueError:
                    bad_poly.append((i, line))
                # first 8 fields are the polygon; the transcript is everything after,
                # rejoined, because a transcript may itself contain a comma.
                transcript = ",".join(parts[8:])
                total += 1
                if transcript.strip() == "###":
                    dontcare += 1
                    n_hash += 1
                    dontcare_forms[transcript] += 1
                elif not transcript.strip():
                    empty_transcripts.append((i, line))
                    dontcare += 1
                    n_empty += 1
                    dontcare_forms["<empty>"] += 1
                else:
                    kept += 1
                    # CER denominator is over NFC-normalized GT chars (EVAL_PROTOCOL §2).
                    n_chars += len(ud.normalize("NFC", transcript))
                    n_words += len(transcript.split())
                    charset.update(transcript)
                    nfc, nfd = ud.normalize("NFC", transcript), ud.normalize("NFD", transcript)
                    if transcript == nfc and transcript == nfd:
                        norm_state["ascii-only (NFC==NFD)"] += 1
                    elif transcript == nfc:
                        norm_state["NFC"] += 1
                    elif transcript == nfd:
                        norm_state["NFD"] += 1
                    else:
                        norm_state["MIXED/neither"] += 1
        per_split[split] = dict(total=total, kept=kept, dontcare=dontcare,
                                hash=n_hash, empty=n_empty, chars=n_chars, words=n_words)

    print("=== fields per line (8 poly coords + transcript => 9 normally) ===")
    for k, v in sorted(field_counts.items()):
        print(f"  {k} fields: {v} lines")
    print(f"  lines whose first 8 fields are NOT all ints: {len(bad_poly)}")
    for i, ln in bad_poly[:5]:
        print(f"    gt_{i}: {ln!r}")
    print(f"  lines with an empty transcript: {len(empty_transcripts)}")

    print("\n=== instance counts per split (READABLE = rec-only scorable) ===")
    hdr = f"{'split':12s} {'total':>7s} {'###':>7s} {'empty':>7s} {'READABLE':>9s} {'GT chars':>9s} {'GT words':>9s}"
    print(hdr)
    for s, d in per_split.items():
        print(f"{s:12s} {d['total']:7d} {d['hash']:7d} {d['empty']:7d} "
              f"{d['kept']:9d} {d['chars']:9d} {d['words']:9d}")
    agg = {k: sum(d[k] for d in per_split.values()) for k in
           ("total", "hash", "empty", "kept", "chars", "words")}
    print(f"{'ALL':12s} {agg['total']:7d} {agg['hash']:7d} {agg['empty']:7d} "
          f"{agg['kept']:9d} {agg['chars']:9d} {agg['words']:9d}")

    print("\n=== normalization state of shipped readable transcripts ===")
    for k, v in norm_state.most_common():
        print(f"  {k}: {v}")

    print("\n=== do-not-care marker forms ===")
    for k, v in dontcare_forms.most_common(5):
        print(f"  {k!r}: {v}")

    print(f"\n=== charset: {len(charset)} distinct codepoints (readable transcripts) ===")
    combining = [c for c in charset if ud.combining(c)]
    print(f"  combining marks present: {[hex(ord(c)) for c in combining]}")
    lo = "".join(sorted(c for c in charset if ord(c) < 128))
    print(f"  ascii: {lo!r}")
    nonascii = sorted((c for c in charset if ord(c) >= 128), key=lambda c: -charset[c])
    print(f"  non-ascii ({len(nonascii)}): {''.join(nonascii)}")


if __name__ == "__main__":
    main()
