"""EVAL_PROTOCOL §16 — context baselines. CONTEXT, NOT A CONTEST.

Off-the-shelf Vietnamese OCR on the SAME test-500, at the SAME rec-only scope, scored by OUR
three-axis scorer. These systems were NOT trained on VinText; ours was. This table measures the
TASK'S DIFFICULTY and demonstrates the scorer on systems that are not mine. It is not a
superiority claim and must never be written as one.

§16 is enforced in code, not in prose:

  * RECOGNITION-ONLY, MANDATORY. Every system is called through its recognizer entry point on a
    GT-box crop (EasyOCR: Reader.recognize(); PaddleOCR: TextRecognition; Tesseract: --psm 8).
    Handing a word crop to a full detect+recognize pipeline and scoring its empty return as a
    catastrophic error is a STRAWMAN and is forbidden.
  * SMOKE TEST FIRST (--smoke): 20 easy, high-contrast crops. If a system returns empty on
    clearly legible text, that is OUR API-mode bug, not its result. Fix it before the full run.
  * Same crops as the eval: scripts.infer.crops_for -> the eval's own crop_quad code path.
    A degenerate quad becomes an EMPTY prediction, never an exclusion -- the denominator stays
    pinned at 10,068 instances / 37,254 chars.
  * Install / network failures are reported AS FAILURES. No row is faked.
  * NO HAND-TYPED NUMBERS. Every row -- including OUR OWN -- is computed here from the run
    artifacts (runs/*/result.json, runs/probe_contamination.json), median over seeds, on the same
    frozen denominator with the same scorer. A metric that cannot be computed from an artifact does
    not get printed: a `nan` in this table would be a number nobody measured.
  * The writer MERGES per system. A single-system run updates only its own key and can never
    destroy another system's measured row (it did once -- see the git history of this file).
  * SCOPE: this table is CONTEXT -- external systems + the zero-shot checkpoint + ours @ full real
    data (which is what answers "is 9.4% CER any good?"). Our *study arms* (r=10%, etc.) are NOT
    yardsticks and live in the RESULTS table, not here.

    python scripts/context_baselines.py --smoke                # 20 crops, every system
    python scripts/context_baselines.py --systems easyocr      # full test-500 (merges)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time

import cv2
import numpy as np

# The C: drive on this box is FULL (0 GB free), and every one of these libraries defaults its
# weight cache -- and its download temp dir -- to C:. Left alone they fail with ENOSPC, which
# looks exactly like a broken system and would tempt a fake row. Redirect the lot to E: BEFORE
# any of them is imported. (BUILD_PLAN "BLOCKERS/Q": same fix as uv cache / TORCH_HOME.)
CACHE = os.environ.setdefault("OCR_CACHE_ROOT", "E:/ocr_cache")
for var in ("HF_HOME", "MODELSCOPE_CACHE", "PADDLE_PDX_CACHE_HOME", "PADDLEX_HOME",
            "XDG_CACHE_HOME", "TMP", "TEMP", "TMPDIR", "EASYOCR_MODULE_PATH"):
    os.environ[var] = os.path.join(CACHE, var.lower())
    os.makedirs(os.environ[var], exist_ok=True)

# Tesseract needs a SYSTEM install (the pip package is only a wrapper), and its language packs live
# next to the binary on the full C: drive. Point it at a tessdata dir on E: instead of shipping
# `vie.traineddata` into Program Files. Both are overridable from the environment.
TESSDATA = os.environ.setdefault("TESSDATA_PREFIX", os.path.join(CACHE, "tessdata"))
if not os.environ.get("TESSERACT_EXE"):
    for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(cand):
            os.environ["TESSERACT_EXE"] = cand
            break

# This script prints Vietnamese. The Windows console defaults to cp1252, which cannot encode ả/ệ/ữ
# and dies mid-table -- on the smoke test, whose whole job is to SHOW the predictions.
for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.infer import crops_for                      # noqa: E402  (the EVAL's crop path)
from scripts.vintext import iter_instances               # noqa: E402
from vi_three_axis_scorer import Score, score_pair       # noqa: E402  (OUR scorer)

OUT = "runs/context_baselines.json"
NO_BATCH = False          # --no-batch: force the per-crop path (used to prove batch mode agrees)


# ----------------------------------------------------------------- the systems
class EasyOCR:
    """recognize() is EasyOCR's RECOGNIZER. With no box lists it reads the whole crop."""
    name = "EasyOCR"

    def __init__(self):
        import easyocr
        self.version = easyocr.__version__
        self.model = "easyocr 'vi' (latin_g2 recognizer)"
        store = os.path.join(CACHE, "easyocr")
        os.makedirs(store, exist_ok=True)
        self.r = easyocr.Reader(["vi"], gpu=True, verbose=False,
                                model_storage_directory=store,
                                user_network_directory=store)

    def read(self, pil):
        grey = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2GRAY)
        out = self.r.recognize(grey, detail=0)          # rec-only: no detector is run
        return out[0] if out else ""


class PaddleOCR:
    """TextRecognition is PaddleOCR 3.x's standalone RECOGNIZER module (no detector)."""
    name = "PaddleOCR"

    def __init__(self, model_name="latin_PP-OCRv5_mobile_rec"):
        import paddleocr
        from paddleocr import TextRecognition
        self.version = paddleocr.__version__
        self.model = model_name
        self.r = TextRecognition(model_name=model_name)
        self.charset_note = self._charset_coverage(model_name)

    @staticmethod
    def _charset_coverage(model_name):
        """PaddleOCR ships no Vietnamese recognizer; the nearest is the multilingual LATIN model.

        Its output charset is a HARD CEILING on what it can possibly emit, so measure it rather
        than reading its errors as if they were accuracy. Anything missing here is a character
        the model is structurally incapable of producing -- reporting that as a tone failure
        would be exactly the strawman §16 forbids.
        """
        import glob
        import yaml
        f = glob.glob(os.path.join(os.environ["PADDLE_PDX_CACHE_HOME"], "official_models",
                                   model_name, "inference.yml"))
        if not f:
            return "charset not inspected"
        def find(o, k="character_dict"):
            if isinstance(o, dict):
                for a, b in o.items():
                    if k in str(a):
                        return b
                    r = find(b, k)
                    if r:
                        return r
            return None
        chars = set(find(yaml.safe_load(open(f[0], encoding="utf-8"))) or [])
        vn = [chr(c) for c in range(0x1EA0, 0x1EFA)]          # the Vietnamese precomposed block
        missing = [c for c in vn if c not in chars]
        return (f"output charset = {len(chars)} chars; {len(missing)}/{len(vn)} of the Vietnamese "
                f"precomposed block (U+1EA0-U+1EF9: ạ ả ấ ầ ệ ự …) are ABSENT from it. Those "
                f"characters CANNOT BE EMITTED. Its tone axis is structurally capped, not merely "
                f"inaccurate.")

    def read(self, pil):
        bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        out = self.r.predict(bgr)                        # rec-only
        if not out:
            return ""
        o = out[0]
        return (o.get("rec_text") if isinstance(o, dict) else getattr(o, "rec_text", "")) or ""


class Tesseract:
    """--psm 8 = 'treat the image as a single word'. That is the rec-only mode."""
    name = "Tesseract-vie"

    def __init__(self):
        import pytesseract
        exe = os.environ.get("TESSERACT_EXE")
        if exe:
            pytesseract.pytesseract.tesseract_cmd = exe
        self.t = pytesseract
        self.exe = pytesseract.pytesseract.tesseract_cmd
        self.version = str(pytesseract.get_tesseract_version())
        langs = pytesseract.get_languages()
        if "vie" not in langs:
            raise RuntimeError(f"'vie' traineddata not installed (have: {langs[:8]}...); "
                               f"TESSDATA_PREFIX={os.environ.get('TESSDATA_PREFIX')}")
        self.model = "tesseract vie, --psm 8"

    def read(self, pil):
        return self.t.image_to_string(pil, lang="vie", config="--psm 8").strip()

    def batch(self, pairs):
        """One tesseract process for all 10,068 crops instead of 10,068 of them.

        Tesseract has no library binding here -- pytesseract shells out per call, and at ~0.2 s of
        process spawn per crop the full test set takes ~35 min, which is all overhead and no OCR.
        Tesseract's own batch mode takes a FILE OF IMAGE PATHS and emits one page per image,
        form-feed separated, in input order. Same binary, same --psm 8, same model: only the
        process count changes.

        The one hazard is ALIGNMENT. If the page count ever disagreed with the image count, every
        prediction after the discrepancy would be scored against the wrong ground truth and the row
        would be quietly, catastrophically wrong. So it is asserted, not assumed.
        """
        import subprocess
        work = os.path.join(CACHE, "tess_batch")
        os.makedirs(work, exist_ok=True)

        idx, paths = [], []
        for i, (_inst, im) in enumerate(pairs):
            if im is None:                       # degenerate quad -> stays an empty prediction
                continue
            p = os.path.join(work, f"{i:06d}.png")
            im.save(p)
            idx.append(i)
            paths.append(p)

        lst = os.path.join(work, "images.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.write("\n".join(paths) + "\n")
        outbase = os.path.join(work, "out")

        r = subprocess.run([self.exe, lst, outbase, "-l", "vie", "--psm", "8"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"tesseract batch failed (rc={r.returncode}): {r.stderr[-300:]}")

        text = open(outbase + ".txt", encoding="utf-8").read()
        pages = text.split("\f")
        if pages and pages[-1].strip() == "":
            pages.pop()                          # trailing separator after the final page
        if len(pages) != len(paths):
            raise RuntimeError(f"tesseract batch MISALIGNED: {len(pages)} pages for {len(paths)} "
                               f"images — refusing to score predictions against the wrong GT")

        preds = [""] * len(pairs)
        for i, page in zip(idx, pages):
            preds[i] = page.strip()
        for p in paths:
            os.remove(p)
        return preds


SYSTEMS = {"easyocr": EasyOCR, "paddleocr": PaddleOCR, "tesseract": Tesseract}

# The six metrics every row must carry. `nan` is not an acceptable value for any of them: the two
# that §7's promotion rule needs (cer, tone) are not the only two a reader will read.
METRICS = ("cer", "wer", "exact", "base", "mod", "tone")

# result.json's key -> ours
_AXES = dict(cer="cer", wer="wer", exact="exact",
             base="axis1_base", mod="axis2_modifier", tone="axis3_tone")


# ------------------------------------------------- OUR rows, computed from the run artifacts
def ours_row(run_dirs, system, model, note):
    """Median over seeds of all six metrics, straight out of runs/<arm>_seed<N>/result.json.

    Not one number here is typed by hand. The seed spread is carried too -- a median with no
    spread beside it is half a result (CLAUDE.md G5).
    """
    rs = []
    for d in run_dirs:
        p = os.path.join("runs", d, "result.json")
        if not os.path.exists(p):
            raise FileNotFoundError(f"{p} -- cannot compute '{system}' without its artifact")
        rs.append(json.load(open(p, encoding="utf-8")))

    n = {r["n_instances"] for r in rs}
    chars = {r["n_chars"] for r in rs}
    assert n == {10068} and chars == {37254}, f"denominator moved in {run_dirs}: {n}/{chars}"

    row = dict(system=system, model=model, version=f"k={len(rs)} median over seeds "
                                                   f"{sorted(r['seed'] for r in rs)}",
               n=10068, chars=37254, note=note,
               source=[f"runs/{d}/result.json" for d in run_dirs])
    for m, key in _AXES.items():
        seeds = [r[key] * 100 for r in rs]
        row[m] = statistics.median(seeds)          # this table's point estimate
        row[f"{m}_seeds"] = seeds
        # The arm-vs-baseline tables adjudicate on mean ± CI95 (an overlap test needs means), so
        # carry those too rather than let the two statistics drift apart unrecorded. They differ by
        # ~0.01 pp on CER -- far inside the CI -- but a reader comparing sections will spot it.
        row[f"{m}_mean"] = statistics.mean(seeds)
        if len(seeds) > 2:
            row[f"{m}_ci95_half"] = 1.96 * statistics.stdev(seeds) / math.sqrt(len(seeds))
    return row


def zeroshot_row():
    """The free row: the SAME backbone before fine-tuning -- from the contamination probe's artifact."""
    p = "runs/probe_contamination.json"
    d = json.load(open(p, encoding="utf-8"))
    t = d["results"]["test"]                     # test-500 only; the train row is not this table's business
    row = dict(system="pbcquoc vgg_transformer (zero-shot, no fine-tune)",
               model="document-pretrained, never saw scene text",
               version=f"checkpoint {d['checkpoint_sha256'][:6]}…{d['checkpoint_sha256'][-5:]}",
               n=t["n"], chars=t["chars"],
               note="Stage 0 contamination probe, RESULTS.md §0.2", source=[p])
    row.update({m: t[m] * 100 for m in METRICS})
    return row


def derived_rows():
    return {
        "zeroshot_pbcquoc": zeroshot_row(),
        # §16 scope: ours @ FULL real data is the row that answers "is 9.4% CER any good?".
        # The r=10% arm is a STUDY ARM, not an external yardstick -- it belongs to the RESULTS
        # table. Putting it here invites precisely the head-to-head the framing forbids.
        "ours_full": ours_row(
            [f"baseline_seed{s}" for s in (0, 1, 2)],
            system="ours @ full real data (25,742 crops)",
            model="vgg_transformer fine-tuned",
            note="real-only baseline, RESULTS.md §0.5"),
    }


# ----------------------------------------------------------------- run
def build_crops(limit=None, smoke=False):
    insts = list(iter_instances("test", scorable_only=True))
    pairs = crops_for(insts)                              # the eval's own code path
    if smoke:
        # §16: 20 EASY crops -- big, high-contrast, multi-char. If a system returns empty on
        # THESE, the API mode is wrong and it is our bug, not the system's result.
        cand = []
        for inst, im in pairs:
            if im is None or len(inst.text) < 4:
                continue
            g = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            if im.height >= 32 and (g.max() - g.min()) > 0.75 and g.std() > 0.22:
                cand.append((inst, im))
            if len(cand) >= 20:
                break
        return cand
    return pairs[:limit] if limit else pairs


def run(sysname, pairs, smoke):
    cls = SYSTEMS[sysname]
    try:
        sysobj = cls()
    except Exception as e:                               # §16: report failures AS failures
        print(f"\n  {cls.name:14s} INSTALL/LOAD FAILED — {type(e).__name__}: {str(e)[:120]}")
        print(f"  {'':14s} -> reported as a failure. No row is faked.")
        return None

    t0 = time.time()
    sc, empties, preds = Score(), 0, []

    # A system may offer a batch entry point (same binary, same flags, fewer processes). The smoke
    # test deliberately stays on the per-crop path: it is the one that must be shown to work.
    if not smoke and not NO_BATCH and hasattr(sysobj, "batch"):
        print(f"    {sysobj.name}: batch mode ({len(pairs)} crops, one process)", flush=True)
        batched = sysobj.batch(pairs)
        assert len(batched) == len(pairs), "batch returned the wrong number of predictions"
        got = iter(batched)
    else:
        got = None

    for i, (inst, im) in enumerate(pairs):
        if got is not None:
            pred = next(got)
        else:
            pred = "" if im is None else sysobj.read(im)  # degenerate quad -> empty, never dropped
        empties += int(not pred.strip())
        preds.append((inst.text, pred))
        score_pair(sc, inst.text, pred)
        if got is None and not smoke and i and i % 1000 == 0:
            print(f"    {sysobj.name}: {i}/{len(pairs)}  ({time.time()-t0:.0f}s)", flush=True)
    dt = time.time() - t0

    if smoke:
        print(f"\n  {sysobj.name}  ({sysobj.model}, v{sysobj.version})")
        for gt, pred in preds[:20]:
            flag = "  <-- EMPTY on legible text: OUR API bug, not its result" if not pred.strip() else ""
            print(f"    GT {gt!r:<22s} -> {pred!r}{flag}")
        print(f"    empty returns: {empties}/{len(preds)}   CER {sc.cer*100:.2f}%")
        return dict(empty=empties, n=len(preds), cer=sc.cer * 100)

    return dict(
        system=sysobj.name, model=sysobj.model, version=sysobj.version,
        n=sc.n_samples, chars=sc.char_ref,
        cer=sc.cer * 100, wer=sc.wer * 100, exact=sc.exact * 100,
        base=sc.base_acc * 100, base_ci=sc.base_acc_ci * 100,
        mod=sc.mod_acc * 100, tone=sc.tone_acc * 100,
        empty_returns=empties, seconds=dt,
        tone_confusion=sc.confusion("tone", top=6),
        charset_note=getattr(sysobj, "charset_note", None),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", nargs="*", default=list(SYSTEMS))
    ap.add_argument("--smoke", action="store_true", help="§16: 20 easy crops first")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-batch", action="store_true",
                    help="force the per-crop path even where a batch one exists (equivalence check)")
    ap.add_argument("--dry-run", action="store_true",
                    help="score, print, but do NOT write the artifact")
    args = ap.parse_args()

    global NO_BATCH
    NO_BATCH = args.no_batch

    pairs = build_crops(args.limit, args.smoke)
    print(f"crops: {len(pairs)}   scope: rec-only (GT boxes)   "
          f"{'SMOKE TEST (§16)' if args.smoke else 'FULL test-500'}")
    if not args.smoke and not args.limit:
        # The frozen denominator guards the REAL run. --limit is a diagnostic and never writes.
        assert len(pairs) == 10068, f"denominator moved: {len(pairs)} != 10068"

    fresh = {}
    for s in args.systems:
        r = run(s, pairs, args.smoke)
        if r:
            fresh[s] = dict(r, measured_at=time.strftime("%Y-%m-%d %H:%M"))

    if args.smoke:
        print("\n§16 smoke verdict: a system with empty returns on THESE crops is being called "
              "wrong.\nFix the API mode before the full run.")
        return

    # MERGE, never overwrite. `--systems tesseract` must not delete the PaddleOCR row that a
    # previous run measured -- runs/ is gitignored, so an overwrite here is UNRECOVERABLE data
    # loss, and it has already happened once. Only the systems measured in THIS run are replaced;
    # the derived rows are always recomputed from their artifacts.
    results = {}
    if os.path.exists(OUT):
        results = json.load(open(OUT, encoding="utf-8"))
    carried = [k for k in results if k in SYSTEMS and k not in fresh]
    results.update(fresh)
    results.update(derived_rows())
    results.pop("ours_r10", None)          # §16 scope: a study arm, not a yardstick -> RESULTS table

    # No unmeasured number reaches the page. A `nan` here used to mean "hand-typed from a summary
    # that only stored two metrics"; now it can only mean a bug, so fail loudly instead of printing.
    for k, r in results.items():
        bad = [m for m in METRICS
               if not isinstance(r.get(m), (int, float)) or math.isnan(float(r[m]))]
        if bad:
            raise ValueError(f"row '{k}' has no measured value for {bad} — refusing to write a "
                             f"table with numbers nobody computed")

    if args.dry_run or args.limit:
        # A partial run has a different denominator; it must never overwrite the frozen table.
        print(f"\n[dry-run/limit] scored {len(pairs)} crops — artifact NOT written")
        for k in fresh:
            print(f"  {results[k]['system']:<28s} " + " ".join(f"{m} {results[k][m]:6.2f}"
                                                               for m in METRICS))
        return

    os.makedirs("runs", exist_ok=True)
    order = [k for k in ("easyocr", "paddleocr", "tesseract") if k in results]
    order += [k for k in ("zeroshot_pbcquoc", "ours_full") if k in results]
    results = {k: results[k] for k in order + [k for k in results if k not in order]}
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\n" + "=" * 96)
    print("CONTEXT, NOT A CONTEST — rec-only, VinText test-500 (10,068 inst / 37,254 chars), NFC,")
    print("scored by OUR three-axis scorer. These systems were NOT trained on VinText; ours was.")
    print("=" * 96)
    print(f"{'system':<44s} {'CER':>7s} {'WER':>7s} {'exact':>7s} {'base':>7s} {'modif':>7s} {'tone':>7s}")
    for k in results:
        r = results[k]
        mark = "  (carried forward)" if k in carried else ""
        print(f"{r['system']:<44s} " + " ".join(f"{r[m]:7.2f}" for m in METRICS) + mark)
    missing = [s for s in args.systems if s not in fresh]
    if missing:
        print(f"\nnot measured this run: {', '.join(missing)} (failures are reported, never faked)")
    print(f"\nwrote {OUT}  ({len(results)} rows; merged, {len(fresh)} re-measured)")


if __name__ == "__main__":
    main()
