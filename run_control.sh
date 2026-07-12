#!/usr/bin/env bash
# EVAL_PROTOCOL §14.4(A) — the CLEAN-RENDER CONTROL. 3 runs: r=10%, arm=clean, seeds {0,1,2}.
#
# Same corpus / fonts / strict bank (r=10) / generation seed as synth10k_strict_r10; the ENTIRE
# degradation stack is OFF. Same HP, iters=12,000, default image_aug, best-val export.
#
# PRE-REGISTERED READINGS (§14.4(A), locked BEFORE this ran -- do not renegotiate after seeing it):
#   clean buys >= ~80% of the +2.783 -> the realism machinery is NOT load-bearing at this operating
#     point; the claim is label-efficiency via decoder-training signal (premature-<eos> repair).
#   clean buys <  ~50%               -> the degradations ARE load-bearing; the domain-transfer
#     framing survives alongside the decoder mechanism.
#   in between                       -> report the measured split, no story beyond it.
#
# Accounting: an ATTRIBUTION ABLATION of an already-green result. NOT a §8.1 re-gate attempt. The
# headline (+2.783, strict, k=5) does not move regardless of what this says.

PYTHON_EXE="./.venv/Scripts/python.exe"
[ -f "$PYTHON_EXE" ] || { echo "FATAL: no python at $PYTHON_EXE (run from E:/ocr_engine)"; exit 1; }

export TMPDIR=E:/ocr_engine/.tmp
export PYTHONIOENCODING=utf-8
mkdir -p "$TMPDIR" runs

MASTER="runs/control_clean.log"

LOCK="runs/.control.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
    echo "run_control.sh is already running (lock: $LOCK). Not starting a second driver."
    exit 1
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

exec > >(tee -a "$MASTER") 2>&1
say() { echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

training_alive() {
    powershell -NoProfile -Command 'if (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "train_budget" }) { "alive" }' 2>/dev/null | grep -q alive
}

say "=== §14.4(A) clean-render control: r=10%, k=3, resume-safe ==="
if training_alive; then
    say "a train_budget run is in flight; waiting"
    while training_alive; do sleep 60; done
fi

ok=0; failed=0
for s in 0 1 2; do
    out="runs/budget_r10_clean_seed${s}/result.json"
    log="runs/budget_r10_clean_s${s}.out"
    if [ -f "$out" ]; then
        say "SKIP r=10 clean seed=$s (result.json exists)"; continue
    fi
    for attempt in 1 2; do
        # purge the cell's lmdb: vietocr reuses ./train_<dataset> by NAME without checking it
        # matches the annotation, so a stale/partial cache would be trained on silently.
        rm -rf "train_budget_r10_clean"
        say "START r=10 arm=clean seed=$s (attempt $attempt/2)"
        "$PYTHON_EXE" scripts/train_budget.py --r 10 --arm clean --seed "$s" > "$log" 2>&1
        [ -f "$out" ] && break
        say "  attempt $attempt produced no result.json"
        [ "$attempt" = "1" ] && sleep 30
    done
    if [ -f "$out" ]; then
        cer=$("$PYTHON_EXE" -c "import json;print(f\"{json.load(open(r'$out'))['cer']:.4f}\")" 2>/dev/null)
        say "OK   r=10 clean seed=$s  CER=${cer:-?}"; ok=$((ok+1))
    else
        say "FAIL r=10 clean seed=$s -- see $log"; tail -5 "$log" | sed 's/^/       | /'; failed=$((failed+1))
    fi
done

say "=== control done: $ok trained, $failed failed ==="
say "=== attribution split (scripts/aggregate_control.py) ==="
"$PYTHON_EXE" scripts/aggregate_control.py
say "=== CONTROL DONE ==="
