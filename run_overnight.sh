#!/usr/bin/env bash
# §14 budget axis -- unattended overnight driver.
#
#   bash run_overnight.sh
#
# Full grid = 18 runs: r in {10,25,50} x arm in {real,synth} x seed in {0,1,2}.
# Runs that already have a result.json are SKIPPED, so this is safe to re-run
# after a crash/reboot -- it resumes, it never retrains a finished cell.
# Ends by writing the label-efficiency curve (scripts/aggregate_budget.py).

PYTHON_EXE="./.venv/Scripts/python.exe"

if [ ! -f "$PYTHON_EXE" ]; then
    echo "FATAL: no python at $PYTHON_EXE (run from E:/ocr_engine)"
    exit 1
fi

export TMPDIR=E:/ocr_engine/.tmp
export PYTHONIOENCODING=utf-8
mkdir -p "$TMPDIR" runs

MASTER="runs/overnight.log"
exec > >(tee -a "$MASTER") 2>&1     # everything below lands in the console AND the master log

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

# --- true if a train_budget.py python is alive (the in-flight run, or a stray from a prior launch).
# Name -eq python.exe is load-bearing: without it the probe matches the powershell.exe running the
# probe (its own command line contains the pattern) and reports "alive" forever.
training_alive() {
    powershell -NoProfile -Command 'if (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "train_budget" }) { "alive" }' 2>/dev/null | grep -q alive
}

say "=== overnight start: 18-cell grid, resume-safe ==="

# One trainer at a time -- two on the same GPU is an OOM, not a speedup.
if training_alive; then
    say "a train_budget run is already in flight; waiting for it to finish before starting the queue"
    while training_alive; do sleep 60; done
    say "in-flight run finished; starting the queue"
fi

ok=0; skipped=0; failed=0
FAILED_CELLS=""

for r in 10 25 50; do
  for arm in real synth; do
    for s in 0 1 2; do
        out="runs/budget_r${r}_${arm}_seed${s}/result.json"
        log="runs/budget_r${r}_${arm}_s${s}.out"

        if [ -f "$out" ]; then
            say "SKIP r=$r $arm seed=$s (result.json exists)"
            skipped=$((skipped + 1))
            continue
        fi

        # up to 2 attempts -- a transient CUDA/OOM hiccup shouldn't cost the whole cell
        for attempt in 1 2; do
            say "START r=$r arm=$arm seed=$s (attempt $attempt/2)"
            "$PYTHON_EXE" scripts/train_budget.py --r "$r" --arm "$arm" --seed "$s" > "$log" 2>&1
            if [ -f "$out" ]; then
                break
            fi
            say "  attempt $attempt produced no result.json"
            [ "$attempt" = "1" ] && sleep 30
        done

        if [ -f "$out" ]; then
            cer=$("$PYTHON_EXE" -c "import json;print(f\"{json.load(open(r'$out'))['cer']:.4f}\")" 2>/dev/null)
            say "OK   r=$r $arm seed=$s  CER=${cer:-?}"
            ok=$((ok + 1))
        else
            say "FAIL r=$r $arm seed=$s -- see $log (tail below)"
            tail -5 "$log" | sed 's/^/       | /'
            failed=$((failed + 1))
            FAILED_CELLS="$FAILED_CELLS r${r}_${arm}_s${s}"
        fi
    done
  done
done

say "=== grid done: $ok trained, $skipped skipped, $failed failed ==="
[ -n "$FAILED_CELLS" ] && say "failed cells:$FAILED_CELLS  (just re-run this script -- it resumes)"

say "=== label-efficiency curve (scripts/aggregate_budget.py) ==="
"$PYTHON_EXE" scripts/aggregate_budget.py

say "=== ALL DONE ==="
