"""C3 — the assisted-gold transcription tool (EVAL_PROTOCOL §5 as amended by §14.4(B)).

    python tools/gold_tool.py                 # pass 1  -> http://localhost:8765
    python tools/gold_tool.py --pass 2        # pass 2 (>=24h after pass 1 completes)
    python tools/gold_tool.py --report        # the gold report (no server)
    python tools/gold_tool.py --smoke         # 20-row end-to-end self-test ON A COPY

Single file, stdlib only, offline. No external deps, no network calls.

WHAT THIS TOOL MAY AND MAY NOT SHOW YOU (§14.4(B) -- this is protocol, not preference):
  * The input box is PRE-FILLED WITH THE PUBLIC LABEL ONLY.
  * NO MODEL PREDICTION and no OCR output -- from any arm, any checkpoint, any external engine --
    appears anywhere in this UI. Ever. OCR-prefilled gold inherits the model's own errors through
    anchoring and biases the model-vs-gold comparison in the flattering direction, which is the one
    direction that VOIDS the artifact. This file never opens a checkpoint or a predictions file.
  * Public-label prefill still anchors (toward the public label), so the measured noise floor is a
    LOWER BOUND: "the public labels contain AT LEAST X% errors." Conservative for every downstream
    claim -- it can only understate label noise, never overstate it.
  * That anchoring is QUANTIFIED, not assumed: a ~12% stratified BLIND subset (fixed seed) is shown
    with an EMPTY box and the public label HIDDEN. The blind edit rate is the unbiased estimator;
    blind-vs-assisted rates are reported per stratum.
  * UNREADABLE is a first-class outcome, stored and counted. Never guess to fill a box.

CRASH SAFETY: every action appends to runs/gold_events.jsonl (append-only, fsync'd) AND rewrites
the sheet atomically. Kill it at any time; restart resumes at the first unjudged row.

The crops served here are the ones in data/gold/crops/, extracted and perspective-rectified by
scripts/gold_sample.py via scripts.crops.crop_quad -- THE SAME code path the evaluator uses. What
you judge is exactly what the model is scored on.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import random
import shutil
import socketserver
import statistics as st
import sys
import time
import unicodedata as ud
import urllib.parse
import webbrowser
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join("data", "gold", "transcription_sheet.tsv")
MANIFEST = os.path.join("data", "gold", "gold_manifest.json")
CROPS = os.path.join("data", "gold", "crops")
EVENTS = os.path.join("runs", "gold_events.jsonl")
STATE = os.path.join("runs", "gold_state.json")
VINTEXT_TEST = os.path.join("data", "vietnamese", "unseen_test_images")

BLIND_SEED = 20260712      # fixed: the blind subset must be reproducible
BLIND_FRAC = 0.12          # ~12%, stratified
ORDER_SEED = 20260712      # fixed: randomized presentation order (NOT grouped by source image)
P2_SAMPLE_SEED = 20260713  # fixed: the 10% accepted-row audit sample in pass 2
P2_SAMPLE_FRAC = 0.10
PORT = 8765

COLUMNS = ["idx", "crop_file", "img_id", "stratum", "public_label",
           "gold_pass1", "gold_pass2", "blind", "action1", "action2", "resolved"]

# Format/zero-width codepoints that must never survive into a gold label. They are invisible, they
# break exact-match and CER silently, and a human cannot see them to remove them.
ZW = {"​", "‌", "‍", "⁠", "﻿", "­"}


def vocab():
    """The locked VinText/vgg_transformer charset. Used to WARN, never to block -- a real label may
    legitimately contain something outside it, and that fact is itself a finding."""
    import yaml  # noqa: PLC0415  (only needed for the charset warning; the server itself is stdlib)
    return set(yaml.safe_load(open("configs/vgg_transformer_pinned.yml", encoding="utf-8"))["vocab"])


try:
    VOCAB = vocab()
except Exception:                                        # charset check degrades to "no warning"
    VOCAB = None


def clean_text(s: str):
    """Strip format/zero-width codepoints, NFC-normalize, and charset-check. Returns (text, warnings).
    NEVER raises and never blocks a save."""
    warns = []
    raw = s
    s = "".join(c for c in s if c not in ZW and ud.category(c) != "Cf")
    if s != raw:
        warns.append("stripped invisible/format codepoint(s)")
    s2 = ud.normalize("NFC", s)
    if s2 != s:
        warns.append("NFC-normalized (was NFD/mixed)")
    s = s2.strip()
    if VOCAB is not None:
        bad = sorted({c for c in s if c not in VOCAB})
        if bad:
            warns.append("outside the VinText charset: " + " ".join(f"{c!r}(U+{ord(c):04X})" for c in bad))
    return s, warns


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------- sheet I/O
#
# PLAIN TSV -- deliberately NOT the csv module.
#
# Real VinText labels contain bare double-quote characters (e.g. `"Độc`, `TƯỞNG"`). csv.reader
# treats those as FIELD QUOTES and swallows every line until the next quote: on this sheet it
# silently collapsed 2,437 rows into 1,465, and csv.writer would then have re-quoted the labels on
# save. A tool that silently drops 40% of the gold sheet -- and rewrites the labels it does keep --
# is exactly the kind of quiet corruption this project exists to prevent. So: split on TAB, join on
# TAB, no quoting, no escaping. Values are guaranteed tab/newline-free (enforced on save).
def load_sheet(path):
    with open(path, encoding="utf-8") as f:
        lines = [ln.rstrip("\n").rstrip("\r") for ln in f if ln.strip("\r\n")]
    head = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        parts = ln.split("\t")
        parts += [""] * (len(head) - len(parts))
        r = dict(zip(head, parts))
        for c in COLUMNS:
            r.setdefault(c, "")
        rows.append(r)
    return rows


def save_sheet(rows, path):
    """Atomic: write a temp file then os.replace, so a crash mid-write cannot corrupt the sheet."""
    def cell(v):
        # a tab or newline inside a value would break the row structure -- strip, never escape
        return str(v or "").replace("\t", " ").replace("\r", "").replace("\n", " ")

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            f.write("\t".join(cell(r.get(c, "")) for c in COLUMNS) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def log_event(ev):
    os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {}


def write_state(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d, open(STATE, "w", encoding="utf-8"), indent=2)


def assign_blind(rows):
    """~12% stratified blind subset, fixed seed. Idempotent: only assigned once, then persisted."""
    if any(r["blind"] for r in rows):
        return False
    by = {}
    for r in rows:
        by.setdefault(r["stratum"], []).append(r)
    rng = random.Random(BLIND_SEED)
    for _, rs in sorted(by.items()):
        k = max(1, round(BLIND_FRAC * len(rs)))
        for r in rs:
            r["blind"] = "0"
        for r in rng.sample(rs, k):
            r["blind"] = "1"
    return True


def order(rows):
    """Randomized presentation order (fixed seed) -- NOT grouped by source image, so a transcriber
    cannot ride the context of one photo across many rows (which would correlate their errors)."""
    idx = list(range(len(rows)))
    random.Random(ORDER_SEED).shuffle(idx)
    return idx


# ----------------------------------------------------------------------------- queues
def pass1_pending(rows, seq):
    return [i for i in seq if not rows[i]["action1"]]


def pass2_queue(rows, seq):
    """§14.4(B): all EDITED + all BLIND + a fixed-seed 10% sample of ACCEPTED rows.
    The double pass's error-catching power is preserved exactly where it has power."""
    edited = [i for i in seq if rows[i]["action1"] == "edit"]
    blind = [i for i in seq if rows[i]["blind"] == "1" and rows[i]["action1"]]
    accepted = [i for i in seq if rows[i]["action1"] == "accept" and rows[i]["blind"] != "1"]
    rng = random.Random(P2_SAMPLE_SEED)
    sample = rng.sample(accepted, max(1, round(P2_SAMPLE_FRAC * len(accepted)))) if accepted else []
    q, seen = [], set()
    for i in seq:                                   # keep the randomized order
        if i in set(edited) | set(blind) | set(sample) and i not in seen:
            seen.add(i)
            q.append(i)
    return q


def pass2_pending(rows, q):
    out = []
    for i in q:
        if not rows[i]["action2"]:
            out.append(i)
        elif rows[i]["gold_pass1"] != rows[i]["gold_pass2"] and rows[i]["resolved"] != "1":
            out.append(i)                           # disagreement -> back into the resolve queue
    return out


# ----------------------------------------------------------------------------- the page
PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Gold pass</title><style>
*{box-sizing:border-box} body{margin:0;font:14px/1.45 system-ui,sans-serif;background:#14161a;color:#e8eaed}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
.bar{display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:13px;color:#9aa3ad;
     border-bottom:1px solid #2a2f37;padding-bottom:10px;margin-bottom:14px}
.bar b{color:#e8eaed}
.badge{padding:2px 8px;border-radius:99px;font-size:12px;font-weight:600}
.b-diacritic_dense{background:#3b2d5c;color:#d3c1ff}.b-small{background:#0f3f46;color:#9fe8f2}
.b-low_contrast{background:#4a3410;color:#ffd79a}.b-plain{background:#26303a;color:#b9c6d3}
.blind{background:#5c1f1f;color:#ffc9c9}
.cropbox{background:#0b0d10;border:1px solid #2a2f37;border-radius:8px;padding:16px;overflow:auto;
         display:flex;align-items:center;justify-content:center;min-height:180px}
img.crop{image-rendering:pixelated;display:block}
input#box{width:100%;font:600 30px/1.3 ui-monospace,monospace;padding:12px 14px;margin-top:14px;
  background:#0b0d10;color:#fff;border:2px solid #3a4250;border-radius:8px}
input#box:focus{outline:none;border-color:#5b8dd6}
input#box.dirty{border-color:#d6a25b}
.hint{margin-top:8px;color:#7e8894;font-size:12.5px}
.warn{margin-top:8px;color:#ffcf8a;font-size:13px;min-height:18px}
.pub{margin-top:10px;font-size:13px;color:#7e8894}
.pub code{color:#c7d0da;font-size:15px;background:#0b0d10;padding:2px 6px;border-radius:4px}
kbd{background:#2a2f37;border:1px solid #3a4250;border-bottom-width:2px;border-radius:4px;
    padding:1px 6px;font:600 12px ui-monospace,monospace;color:#dbe2ea}
.ctx{margin-top:14px;display:none;border:1px solid #2a2f37;border-radius:8px;overflow:auto;max-height:60vh;background:#0b0d10}
.done{text-align:center;padding:60px 20px}
.stat{color:#9aa3ad}.stat b{color:#e8eaed}
</style></head><body><div class="wrap">
<div class="bar">
  <span>pass <b id="pass"></b></span>
  <span><b id="pos"></b> / <b id="total"></b></span>
  <span class="stat">done <b id="done"></b></span>
  <span class="stat">edit rate <b id="erate"></b></span>
  <span class="stat">unreadable <b id="unread"></b></span>
  <span class="stat">~<b id="rate"></b> s/row</span>
  <span class="stat">ETA <b id="eta"></b></span>
</div>
<div id="main">
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
    <span class="badge" id="stratum"></span>
    <span class="badge blind" id="blindbadge" style="display:none">BLIND — type from scratch</span>
    <span class="stat" id="px"></span>
    <span class="stat" id="rowid"></span>
  </div>
  <div class="cropbox"><img class="crop" id="crop"></div>
  <input id="box" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off">
  <div class="warn" id="warn"></div>
  <div class="pub" id="pub"></div>
  <div class="hint">
    <kbd>Enter</kbd> accept &amp; next ·
    <kbd>U</kbd> unreadable ·
    <kbd>B</kbd> back ·
    <kbd>C</kbd> context image ·
    type to edit (then <kbd>Alt</kbd>+<kbd>U</kbd> / <kbd>Alt</kbd>+<kbd>B</kbd> / <kbd>Alt</kbd>+<kbd>C</kbd>,
    since U/B/C become literal characters once you start typing)
  </div>
  <div class="ctx" id="ctx"></div>
</div>
<div class="done" id="donebox" style="display:none">
  <h2>Queue complete.</h2>
  <p class="stat">Every judgment is saved. Run <code>python tools/gold_tool.py --report</code>.</p>
</div>
</div><script>
let cur=null, t0=Date.now(), times=[], pristine=true;
const $=i=>document.getElementById(i);
function fmt(s){if(!isFinite(s)||s<=0)return"—";const m=Math.round(s/60);if(m<60)return m+"m";
  return Math.floor(m/60)+"h"+String(m%60).padStart(2,"0")}
async function load(){
  const r=await fetch("/api/next"); const d=await r.json();
  $("pass").textContent=d.pass; $("total").textContent=d.total; $("done").textContent=d.done;
  $("erate").textContent=d.edit_rate; $("unread").textContent=d.unreadable;
  const med=times.length?times.reduce((a,b)=>a+b,0)/times.length/1000:0;
  $("rate").textContent=med?med.toFixed(1):"—";
  $("eta").textContent=med?fmt(med*d.remaining):"—";
  if(d.finished){$("main").style.display="none";$("donebox").style.display="block";return}
  cur=d.row; $("pos").textContent=d.done+1;
  $("stratum").textContent=cur.stratum; $("stratum").className="badge b-"+cur.stratum;
  $("blindbadge").style.display=cur.blind==="1"?"":"none";
  $("px").textContent=cur.w+"×"+cur.h+" px";
  $("rowid").textContent="row "+cur.idx;
  $("crop").src="/crop/"+cur.idx+"?"+Date.now();
  $("crop").style.width=(cur.w*cur.zoom)+"px";
  // BLIND rows: empty box, public label HIDDEN (the whole point -- no anchor).
  $("box").value=cur.prefill;
  $("pub").innerHTML = cur.blind==="1" ? "<i>blind row — public label hidden by protocol</i>"
      : (cur.pass==2 ? "pass-1 value prefilled. public label: <code>"+esc(cur.public_label)+"</code>"
                     : "prefilled with the <b>public label</b> (no model output is ever shown)");
  if(cur.disagree) $("pub").innerHTML += "<br><b style='color:#ffcf8a'>RESOLVE: pass1 <code>"+
      esc(cur.gold_pass1)+"</code> ≠ pass2 <code>"+esc(cur.gold_pass2)+"</code> — type the correct one.</b>";
  $("warn").textContent=""; $("ctx").style.display="none"; $("ctx").innerHTML="";
  pristine=true; $("box").classList.remove("dirty");
  $("box").focus(); $("box").select(); t0=Date.now();
}
function esc(s){const d=document.createElement("div");d.textContent=s||"";return d.innerHTML}
async function save(action){
  const v=$("box").value;
  const r=await fetch("/api/save",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({idx:cur.idx,value:v,action:action})});
  const d=await r.json();
  times.push(Date.now()-t0); if(times.length>25)times.shift();
  if(d.warnings&&d.warnings.length){/* shown on the NEXT row is useless; show briefly then move on */}
  await load();
}
async function back(){await fetch("/api/back",{method:"POST"});times=[];await load()}
async function ctx(){
  const c=$("ctx");
  if(c.style.display!=="none"){c.style.display="none";return}
  const r=await fetch("/api/ctx/"+cur.idx); const d=await r.json();
  c.innerHTML='<svg viewBox="0 0 '+d.iw+' '+d.ih+'" style="width:100%;display:block">'+
    '<image href="/image/'+d.img_id+'" width="'+d.iw+'" height="'+d.ih+'"/>'+
    '<polygon points="'+d.poly+'" fill="none" stroke="#ff4d4d" stroke-width="'+d.sw+'"/></svg>';
  c.style.display="block";
  c.scrollTop=Math.max(0,(d.cy/d.ih)*c.scrollHeight-c.clientHeight/2);
}
$("box").addEventListener("input",()=>{pristine=false;$("box").classList.add("dirty")});
document.addEventListener("keydown",e=>{
  if(e.key==="Enter"){e.preventDefault();save("auto");return}
  const alt=e.altKey;
  const k=(e.key||"").toLowerCase();
  // Bare U/B/C only while the box is untouched (the accept path). Once you type, they are letters.
  if((alt||pristine)&&k==="u"){e.preventDefault();save("unreadable");return}
  if((alt||pristine)&&k==="b"){e.preventDefault();back();return}
  if((alt||pristine)&&k==="c"){e.preventDefault();ctx();return}
});
load();
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    rows = []
    seq = []
    queue = []
    pos = 0
    passno = 1
    sheet = SHEET
    manifest = {}

    def log_message(self, *a):
        pass                                        # keep the console clean for the transcriber

    # ---- helpers
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        if not os.path.exists(path):
            return self._send(404, b"not found", "text/plain")
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype)

    # ---- routes
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        C = Handler
        if p == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if p.startswith("/crop/"):
            i = int(p.split("/")[2].split("?")[0])
            return self._file(os.path.join("data", "gold", C.rows[i]["crop_file"].replace("/", os.sep)),
                              "image/png")
        if p.startswith("/image/"):
            iid = int(p.split("/")[2])
            return self._file(os.path.join(VINTEXT_TEST, f"im{iid:04d}.jpg"), "image/jpeg")
        if p.startswith("/api/ctx/"):
            i = int(p.split("/")[3])
            inst = C.manifest["instances"][i]
            poly = inst["poly"]
            xs, ys = poly[0::2], poly[1::2]
            # image size is not in the manifest; read it from the JPEG header (stdlib, no PIL)
            iw, ih = jpeg_size(os.path.join(VINTEXT_TEST, f"im{inst['img_id']:04d}.jpg"))
            return self._send(200, dict(
                img_id=inst["img_id"], iw=iw, ih=ih,
                poly=" ".join(f"{poly[k]},{poly[k+1]}" for k in range(0, 8, 2)),
                cy=sum(ys) / 4.0, sw=max(2, int(max(iw, ih) / 400)),
            ))
        if p == "/api/next":
            return self._send(200, C.state_payload())
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        C = Handler
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}

        if p == "/api/back":
            C.pos = max(0, C.pos - 1)
            return self._send(200, {"ok": True})

        if p == "/api/save":
            i = int(body["idx"])
            action = body.get("action", "auto")
            r = C.rows[i]
            if action == "unreadable":
                text, warns = "", []
                act = "unreadable"
            else:
                text, warns = clean_text(body.get("value", ""))
                prev = r["gold_pass1"] if C.passno == 2 else r["public_label"]
                # BLIND rows have no prefill, so "accept" is meaningless: the comparison that
                # matters is typed-vs-public, computed at report time. Record the action honestly.
                act = "edit" if text != prev else "accept"
                if C.passno == 1 and r["blind"] == "1":
                    act = "blind_typed"
            col, acol = ("gold_pass1", "action1") if C.passno == 1 else ("gold_pass2", "action2")
            r[col] = text
            r[acol] = act
            if C.passno == 2 and r["gold_pass1"] == r["gold_pass2"]:
                r["resolved"] = "1"
            elif C.passno == 2 and body.get("resolving"):
                r["resolved"] = "1"

            log_event(dict(ts=now_iso(), pass_=C.passno, idx=i, action=act, value=text,
                           blind=r["blind"], public_label=r["public_label"],
                           pass1=r["gold_pass1"], warnings=warns))
            save_sheet(C.rows, C.sheet)             # materialize on EVERY action (crash-safe)
            C.pos += 1
            return self._send(200, {"ok": True, "warnings": warns})

        return self._send(404, b"not found", "text/plain")

    # ---- queue state
    @classmethod
    def refresh_queue(cls):
        if cls.passno == 1:
            cls.queue = pass1_pending(cls.rows, cls.seq)
        else:
            cls.queue = pass2_pending(cls.rows, pass2_queue(cls.rows, cls.seq))

    @classmethod
    def state_payload(cls):
        cls.refresh_queue()
        total = (len(cls.rows) if cls.passno == 1
                 else len(pass2_queue(cls.rows, cls.seq)))
        done = total - len(cls.queue)
        acted = [r for r in cls.rows if r["action1"]]
        edits = sum(1 for r in acted if r["action1"] == "edit")
        unread = sum(1 for r in cls.rows if r["action1"] == "unreadable"
                     or r["action2"] == "unreadable")
        erate = f"{100.0*edits/len(acted):.1f}%" if acted else "—"
        if not cls.queue:
            return dict(finished=True, pass_=cls.passno, total=total, done=done, remaining=0,
                        edit_rate=erate, unreadable=unread, **{"pass": cls.passno})
        cls.pos = min(cls.pos, len(cls.queue) - 1)
        i = cls.queue[cls.pos]
        r = cls.rows[i]
        inst = cls.manifest["instances"][i]
        w, h = int(inst["width"]), int(inst["height"])
        zoom = max(2.0, min(8.0, 140.0 / max(8, h)))       # ~4x on a typical 32px crop
        if cls.passno == 1:
            prefill = "" if r["blind"] == "1" else r["public_label"]
        else:
            prefill = r["gold_pass1"]
        disagree = (cls.passno == 2 and r["action2"] and r["gold_pass1"] != r["gold_pass2"]
                    and r["resolved"] != "1")
        return dict(
            finished=False, total=total, done=done, remaining=len(cls.queue),
            edit_rate=erate, unreadable=unread, **{"pass": cls.passno},
            row=dict(idx=i, stratum=r["stratum"], blind=r["blind"], prefill=prefill,
                     public_label=("" if r["blind"] == "1" else r["public_label"]),
                     gold_pass1=r["gold_pass1"], gold_pass2=r["gold_pass2"],
                     disagree=bool(disagree), w=w, h=h, zoom=round(zoom, 2), **{"pass": cls.passno}),
        )


def jpeg_size(path):
    """Read a JPEG's pixel size from its SOF marker. Stdlib only -- the server must not need PIL."""
    try:
        with open(path, "rb") as f:
            f.read(2)
            while True:
                b = f.read(1)
                while b and b != b"\xff":
                    b = f.read(1)
                m = f.read(1)
                while m == b"\xff":
                    m = f.read(1)
                if not m:
                    break
                if m[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    f.read(3)
                    h = int.from_bytes(f.read(2), "big")
                    w = int.from_bytes(f.read(2), "big")
                    return w, h
                ln = int.from_bytes(f.read(2), "big")
                f.read(max(0, ln - 2))
    except Exception:
        pass
    return 1280, 720


# ----------------------------------------------------------------------------- report
def report(sheet=SHEET):
    rows = load_sheet(sheet)
    acted = [r for r in rows if r["action1"]]
    if not acted:
        print("no pass-1 judgments yet — nothing to report.")
        return
    print("=" * 92)
    print("GOLD REPORT (EVAL_PROTOCOL §5 as amended by §14.4(B))")
    print("=" * 92)
    print(f"rows judged (pass 1): {len(acted)} / {len(rows)}")

    def rate(rs, pred):
        rs = [r for r in rs if r["action1"]]
        return (100.0 * sum(1 for r in rs if pred(r)) / len(rs)) if rs else float("nan")

    assisted = [r for r in acted if r["blind"] != "1"]
    blind = [r for r in acted if r["blind"] == "1"]

    # assisted: an EDIT means the public label was wrong (as judged with the label visible).
    a_edit = rate(assisted, lambda r: r["action1"] == "edit")
    # blind: typed from scratch -> disagreement with the public label is the UNBIASED estimator.
    b_dis = (100.0 * sum(1 for r in blind if r["gold_pass1"] != r["public_label"]
                         and r["action1"] != "unreadable") / len(blind)) if blind else float("nan")
    unread = sum(1 for r in rows if r["action1"] == "unreadable")

    print(f"\nASSISTED rows (public label prefilled): {len(assisted)}   edit rate {a_edit:.2f}%")
    print(f"BLIND rows (typed from scratch):        {len(blind)}   disagreement {b_dis:.2f}%")
    print(f"UNREADABLE: {unread} ({100.0*unread/len(rows):.2f}% of the sheet) — stored as unscoreable,")
    print("            never a forced guess.")
    print(f"\n`[BIAS DIRECTION, stated]` Public-label prefill ANCHORS toward the public label, so the")
    print(f"assisted edit rate UNDERCOUNTS label noise. The honest quote is a LOWER BOUND:")
    print(f'   "the public VinText test labels contain AT LEAST {a_edit:.2f}% errors"')
    if blind and not (b_dis != b_dis):
        d = b_dis - a_edit
        print(f"The BLIND subset measures the anchoring itself: blind {b_dis:.2f}% vs assisted "
              f"{a_edit:.2f}% = {d:+.2f} pp.")
        print(f"Blind is the unbiased estimator; if blind > assisted, anchoring is real and measured,")
        print(f"not assumed. A defensible noise-floor point estimate is the BLIND rate ({b_dis:.2f}%).")

    print(f"\n{'stratum':>18s} {'n':>5s} {'assisted edit%':>15s} {'n_blind':>8s} {'blind disagree%':>16s}")
    for s in sorted({r["stratum"] for r in rows}):
        rs = [r for r in acted if r["stratum"] == s]
        ra = [r for r in rs if r["blind"] != "1"]
        rb = [r for r in rs if r["blind"] == "1"]
        ae = rate(ra, lambda r: r["action1"] == "edit")
        be = (100.0 * sum(1 for r in rb if r["gold_pass1"] != r["public_label"]) / len(rb)) if rb else float("nan")
        print(f"{s:>18s} {len(rs):5d} {ae:14.2f}% {len(rb):8d} {be:15.2f}%")

    p2 = [r for r in rows if r["action2"]]
    if p2:
        dis = [r for r in p2 if r["gold_pass1"] != r["gold_pass2"]]
        print(f"\nPASS 2: {len(p2)} rows re-judged; pass1≠pass2 on {len(dis)} "
              f"({100.0*len(dis)/len(p2):.2f}%) — these are the transcriber's OWN errors, caught by")
        print("the double pass. Unresolved:", sum(1 for r in dis if r["resolved"] != "1"))
    else:
        print("\nPASS 2: not started.")
    print("\nBRAIN CHECKPOINT: report these numbers; the noise floor is a LOWER BOUND (see above).")


# ----------------------------------------------------------------------------- smoke test
def smoke():
    """20-row end-to-end self-test ON A COPY. The live sheet is never touched, and ZERO gold values
    are fabricated in it. Exercises: accept / edit / unreadable / back / resume / pass-2 dry run."""
    import threading
    import urllib.request

    tmpdir = os.path.join("runs", "_smoke_gold")
    shutil.rmtree(tmpdir, ignore_errors=True)
    os.makedirs(tmpdir, exist_ok=True)
    sheet = os.path.join(tmpdir, "sheet.tsv")
    shutil.copy(SHEET, sheet)

    global EVENTS, STATE
    EVENTS, STATE = os.path.join(tmpdir, "events.jsonl"), os.path.join(tmpdir, "state.json")

    rows = load_sheet(sheet)
    live_before = [r["gold_pass1"] for r in load_sheet(SHEET)]

    assign_blind(rows)
    save_sheet(rows, sheet)
    seq = order(rows)[:20]                       # a 20-row slice of the real randomized order

    H = Handler
    H.rows, H.seq, H.queue, H.pos, H.passno, H.sheet = rows, seq, [], 0, 1, sheet
    H.manifest = json.load(open(MANIFEST, encoding="utf-8"))

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def get(p):
        return json.load(urllib.request.urlopen(base + p))

    def post(p, d=None):
        req = urllib.request.Request(base + p, method="POST",
                                     data=json.dumps(d or {}).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req))

    print("=" * 88)
    print("SMOKE TEST — 20 rows, ON A COPY (the live sheet is not touched; no gold is fabricated)")
    print("=" * 88)
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    # ROW-COUNT INTEGRITY (regression guard). The csv module silently collapsed this sheet from
    # 2,437 rows to 1,465 because two real labels contain a bare `"` (`"Độc`, `TƯỞNG"`), which it
    # read as a field quote. Every row must survive a load, and a save->reload must be lossless.
    raw_n = sum(1 for ln in open(SHEET, encoding="utf-8") if ln.strip()) - 1
    check(f"load_sheet reads EVERY row ({raw_n} expected, no quote-swallowing)", len(rows) == raw_n)
    labels_before = [r["public_label"] for r in rows]
    save_sheet(rows, sheet)
    check("save->reload is lossless (labels with \" survive verbatim)",
          [r["public_label"] for r in load_sheet(sheet)] == labels_before)
    check("labels containing a double-quote are preserved",
          any('"' in x for x in labels_before))

    s = get("/api/next")
    check("serves a row", not s["finished"] and "row" in s)
    check("blind subset assigned (~12%)",
          0.08 < sum(1 for r in rows if r["blind"] == "1") / len(rows) < 0.16)

    # 1) ACCEPT a row (prefill unchanged)
    r0 = s["row"]
    post("/api/save", dict(idx=r0["idx"], value=r0["prefill"], action="auto"))
    exp = "blind_typed" if r0["blind"] == "1" else "accept"
    check(f"accept -> action1={exp}", rows[r0["idx"]]["action1"] == exp)

    # 2) EDIT a row
    s = get("/api/next")
    r1 = s["row"]
    post("/api/save", dict(idx=r1["idx"], value=r1["prefill"] + "X", action="auto"))
    check("edit -> action1 recorded", rows[r1["idx"]]["action1"] in ("edit", "blind_typed"))
    check("edit -> value stored", rows[r1["idx"]]["gold_pass1"].endswith("X"))

    # 3) UNREADABLE
    s = get("/api/next")
    r2 = s["row"]
    post("/api/save", dict(idx=r2["idx"], value="whatever", action="unreadable"))
    check("unreadable -> stored as unreadable, empty value",
          rows[r2["idx"]]["action1"] == "unreadable" and rows[r2["idx"]]["gold_pass1"] == "")

    # 4) BACK
    before = get("/api/next")["row"]["idx"]
    post("/api/back")
    after = get("/api/next")["row"]["idx"]
    check("back -> moves the cursor back", after != before or H.pos == 0)
    H.pos = 0

    # 5) NFC + zero-width + charset hygiene on save
    s = get("/api/next")
    r3 = s["row"]
    dirty = "Hòa​"                      # NFD 'ò' + a zero-width space
    res = post("/api/save", dict(idx=r3["idx"], value=dirty, action="auto"))
    stored = rows[r3["idx"]]["gold_pass1"]
    check("save strips zero-width", "​" not in stored)
    check("save NFC-normalizes", stored == ud.normalize("NFC", stored) and stored == "Hòa")
    check("warnings surfaced (not blocked)", isinstance(res.get("warnings"), list) and res["warnings"])

    # 6) CRASH-SAFETY: events appended AND sheet materialized on every action
    # 4 saves so far (accept, edit, unreadable, NFC-hygiene). `back` is a cursor move, not a judgment,
    # so it correctly logs no event and writes no value.
    n_saves = 4
    ev = [json.loads(l) for l in open(EVENTS, encoding="utf-8")]
    check("every action logged to events.jsonl", len(ev) == n_saves)
    check("sheet materialized on disk", any(r["action1"] for r in load_sheet(sheet)))

    # 7) RESUME: rebuild from the sheet, as a fresh process would
    rows2 = load_sheet(sheet)
    pend = pass1_pending(rows2, seq)
    check("resume skips judged rows", len(pend) == len(seq) - n_saves)

    # 8) finish the slice, then PASS-2 dry run
    H.rows = rows2
    for i in list(pend):
        H.pos = 0
        H.refresh_queue()
        row = get("/api/next")["row"]
        post("/api/save", dict(idx=row["idx"], value=row["prefill"], action="auto"))
    check("pass 1 slice complete", not pass1_pending(H.rows, seq))

    H.passno = 2
    H.pos = 0
    q = pass2_queue(H.rows, seq)
    edited = [i for i in seq if H.rows[i]["action1"] == "edit"]
    check("pass-2 queue = edits + blind + 10% accepted",
          all(i in q for i in edited) and all(i in q for i in seq if H.rows[i]["blind"] == "1"
                                              and H.rows[i]["action1"]))
    s = get("/api/next")
    check("pass 2 prefills the PASS-1 value (never a model output)",
          s["row"]["prefill"] == H.rows[s["row"]["idx"]]["gold_pass1"])
    # force a disagreement -> it must loop into the resolve queue
    ridx = s["row"]["idx"]
    post("/api/save", dict(idx=ridx, value=(H.rows[ridx]["gold_pass1"] or "Z") + "Q", action="auto"))
    check("pass1≠pass2 -> unresolved, stays queued",
          H.rows[ridx]["resolved"] != "1" and ridx in pass2_pending(H.rows, q))
    post("/api/save", dict(idx=ridx, value=H.rows[ridx]["gold_pass1"], action="auto", resolving=True))
    check("re-agreeing resolves the row", H.rows[ridx]["resolved"] == "1")

    # 9) THE PROTOCOL INVARIANT: no model output reachable from the SERVING path.
    # Scan the module with this test harness excluded -- smoke() has to name the banned tokens in
    # order to look for them, so scanning the whole file makes the check flag its own source. What
    # the invariant is actually about is the code that serves the transcriber.
    # Strip comments/docstring prose -- the word "checkpoint" appears in this module's own docstring
    # explaining that it never opens one, and prose must not fail a check about CODE.
    serving_src = open(__file__, encoding="utf-8").read().lower().split("def smoke(")[0]
    code = "\n".join(l for l in serving_src.splitlines()
                     if not l.lstrip().startswith(("#", '"', "*")))
    banned = ["predictions.tsv", ".pth", "vietocr", "torch", "runs/budget", "best.p"]
    hits = [b for b in banned if b in code]
    check(f"serving CODE never touches a checkpoint / prediction file (hits: {hits or 'none'})",
          not hits)
    check("LIVE sheet still has zero judgments",
          [r["gold_pass1"] for r in load_sheet(SHEET)] == live_before
          and not any(r["gold_pass1"] for r in load_sheet(SHEET)))

    srv.shutdown()
    print("\n" + ("SMOKE TEST PASSED — the loop is sound and the live sheet is untouched."
                  if ok else "SMOKE TEST FAILED — do not hand this to the transcriber."))
    print(f"(scratch copy: {tmpdir}; delete it freely)")
    return 0 if ok else 1


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="passno", type=int, default=1, choices=[1, 2])
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--force", action="store_true", help="override the pass-2 24h cooling-off warning")
    args = ap.parse_args()

    if args.smoke:
        raise SystemExit(smoke())
    if args.report:
        return report(args.sheet)

    rows = load_sheet(args.sheet)
    if assign_blind(rows):
        save_sheet(rows, args.sheet)
        n = sum(1 for r in rows if r["blind"] == "1")
        print(f"assigned the BLIND subset: {n}/{len(rows)} rows ({100.0*n/len(rows):.1f}%), "
              f"stratified, seed={BLIND_SEED} — persisted in the sheet's `blind` column.")

    state = read_state()
    if args.passno == 2:
        done1 = state.get("pass1_completed_at")
        if not done1:
            print("WARNING: pass 1 is not marked complete. Pass 2 is defined over pass-1 outcomes.")
            if not args.force:
                raise SystemExit("refusing to start pass 2 (use --force if you know what you are doing)")
        else:
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(done1)).total_seconds() / 3600
            if age_h < 24:
                print("=" * 88)
                print(f"!! PASS-2 COOLING-OFF VIOLATION: only {age_h:.1f}h since pass 1 completed.")
                print("!! §14.4(B) requires >=24h. The point of the second pass is that you have")
                print("!! FORGOTTEN your first reading — a same-day re-pass mostly reproduces your own")
                print("!! errors and measures nothing. Come back tomorrow.")
                print("=" * 88)
                if not args.force:
                    raise SystemExit("refusing to start pass 2 (--force to override, and say so in the write-up)")
                print("PROCEEDING UNDER --force. This MUST be disclosed in the write-up.")

    H = Handler
    H.rows, H.seq, H.pos, H.passno, H.sheet = rows, order(rows), 0, args.passno, args.sheet
    H.manifest = json.load(open(MANIFEST, encoding="utf-8"))
    H.refresh_queue()

    if not H.queue:
        if args.passno == 1 and not state.get("pass1_completed_at"):
            state["pass1_completed_at"] = now_iso()
            write_state(state)
            print("PASS 1 COMPLETE — timestamped. Pass 2 unlocks in 24h.")
        print("queue empty — nothing to judge. Run --report.")
        return

    n_blind = sum(1 for r in rows if r["blind"] == "1")
    print("=" * 88)
    print(f"GOLD TOOL — pass {args.passno} · {len(H.queue)} rows queued · {n_blind} blind rows in the sheet")
    print("The box is prefilled with the PUBLIC LABEL. No model output is shown, anywhere, ever.")
    print("Enter = accept & next · U = unreadable · B = back · C = context image")
    print("(once you start typing, U/B/C are literal characters — use Alt+U / Alt+B / Alt+C)")
    print(f"\n  ->  http://localhost:{args.port}\n")
    print("Ctrl+C to stop. Every action is saved immediately; restarting resumes where you left off.")
    print("=" * 88)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), H) as srv:
        try:
            webbrowser.open(f"http://localhost:{args.port}")
        except Exception:
            pass
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped. progress saved.")
            H.refresh_queue()
            if args.passno == 1 and not H.queue and not read_state().get("pass1_completed_at"):
                s = read_state()
                s["pass1_completed_at"] = now_iso()
                write_state(s)
                print("PASS 1 COMPLETE — timestamped. Pass 2 unlocks in 24h.")


if __name__ == "__main__":
    main()
