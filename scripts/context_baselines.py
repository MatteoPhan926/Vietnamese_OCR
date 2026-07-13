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

    python scripts/context_baselines.py --smoke                # 20 crops, every system
    python scripts/context_baselines.py --systems easyocr      # full test-500
"""
from __future__ import annotations

import argparse
import json
import os
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.infer import crops_for                      # noqa: E402  (the EVAL's crop path)
from scripts.vintext import iter_instances               # noqa: E402
from vi_three_axis_scorer import Score, score_pair       # noqa: E402  (OUR scorer)

OUT = "runs/context_baselines.json"


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
        self.version = str(pytesseract.get_tesseract_version())
        langs = pytesseract.get_languages()
        if "vie" not in langs:
            raise RuntimeError(f"'vie' traineddata not installed (have: {langs[:8]}...)")
        self.model = "tesseract vie, --psm 8"

    def read(self, pil):
        return self.t.image_to_string(pil, lang="vie", config="--psm 8").strip()


SYSTEMS = {"easyocr": EasyOCR, "paddleocr": PaddleOCR, "tesseract": Tesseract}


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
    for i, (inst, im) in enumerate(pairs):
        pred = "" if im is None else sysobj.read(im)     # degenerate quad -> empty, never dropped
        empties += int(not pred.strip())
        preds.append((inst.text, pred))
        score_pair(sc, inst.text, pred)
        if not smoke and i and i % 1000 == 0:
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
    args = ap.parse_args()

    pairs = build_crops(args.limit, args.smoke)
    print(f"crops: {len(pairs)}   scope: rec-only (GT boxes)   "
          f"{'SMOKE TEST (§16)' if args.smoke else 'FULL test-500'}")
    if not args.smoke:
        assert len(pairs) == 10068, f"denominator moved: {len(pairs)} != 10068"

    results = {}
    for s in args.systems:
        r = run(s, pairs, args.smoke)
        if r:
            results[s] = r

    if args.smoke:
        print("\n§16 smoke verdict: a system with empty returns on THESE crops is being called "
              "wrong.\nFix the API mode before the full run.")
        return

    # the free row: the same model BEFORE fine-tuning (already measured, Stage 0)
    results["zeroshot_pbcquoc"] = dict(
        system="pbcquoc vgg_transformer (zero-shot, no fine-tune)",
        model="document-pretrained, never saw scene text", version="checkpoint 380512…5ea59",
        n=10068, chars=37254, cer=21.33, wer=40.35, exact=60.83,
        base=86.41, mod=88.49, tone=85.88, note="measured at Stage 0, RESULTS.md §0.2",
    )
    results["ours_r10"] = dict(
        system="ours @ r=10% (2,574 real + 10k synth)", model="vgg_transformer fine-tuned",
        version="seed 0", n=10068, chars=37254, cer=13.73, tone=91.50,
        note="k=5 mean; the study's headline arm",
    )
    results["ours_full"] = dict(
        system="ours @ full real data (25,742 crops)", model="vgg_transformer fine-tuned",
        version="k=3 mean", n=10068, chars=37254, cer=9.381, wer=19.291, exact=81.870,
        base=94.114, mod=96.252, tone=94.410, note="RESULTS.md §0.5",
    )

    os.makedirs("runs", exist_ok=True)
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\n" + "=" * 92)
    print("CONTEXT, NOT A CONTEST — rec-only, VinText test-500 (10,068 inst / 37,254 chars), NFC,")
    print("scored by OUR three-axis scorer. These systems were NOT trained on VinText; ours was.")
    print("=" * 92)
    print(f"{'system':<44s} {'CER':>7s} {'exact':>7s} {'base':>7s} {'modif':>7s} {'tone':>7s}")
    for r in results.values():
        print(f"{r['system']:<44s} {r.get('cer',float('nan')):7.2f} "
              f"{r.get('exact',float('nan')):7.2f} {r.get('base',float('nan')):7.2f} "
              f"{r.get('mod',float('nan')):7.2f} {r.get('tone',float('nan')):7.2f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
