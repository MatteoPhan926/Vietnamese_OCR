#!/usr/bin/env bash
# §14.2 (C1) STRICT-BANK closure -- unattended driver.
#
#   bash run_c1.sh
#
# 6 runs: r in {10,25} x arm=strict x seed in {0,1,2}. The +synth arm regenerated with Source B
# restricted to the r-subset's OWN transcripts (transcripts ARE labels -- a budget-r practitioner
# holds only r% of them). Fonts/degradation/seed identical to synth10k_leg; the BANK is the only
# variable. Per §14.2 the HEADLINE quotes this arm.
#
# Resume-safe: a cell with a result.json is SKIPPED, so re-running after a crash never retrains it.

PYTHON_EXE="./.venv/Scripts/python.exe"

if [ ! -f "$PYTHON_EXE" ]; then
    echo "FATAL: no python at $PYTHON_EXE (run from E:/ocr_engine)"
    exit 1
fi

export TMPDIR=E:/ocr_engine/.tmp
export PYTHONIOENCODING=utf-8
mkdir -p "$TMPDIR" runs

MASTER="runs/c1_strict.log"

# --- single-instance lock. mkdir is atomic, so a second launch loses the race and exits instead
# of racing the first one into vietocr's lmdb cache (which is keyed by dataset NAME: two drivers
# on the same cell = one builds the lmdb while the other reads it half-written -> num-samples None).
LOCK="runs/.c1.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
    echo "run_c1.sh is already running (lock: $LOCK). Not starting a second driver."
    echo "If you are sure none is running: rmdir $LOCK"
    exit 1
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

exec > >(tee -a "$MASTER") 2>&1

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

# true if a train_budget python is alive (the in-flight run, or a stray from a prior launch).
# Name -eq python.exe is load-bearing: without it the probe matches the powershell.exe running the
# probe (its own command line contains the pattern) and reports "alive" forever.
training_alive() {
    powershell -NoProfile -Command 'if (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "train_budget" }) { "alive" }' 2>/dev/null | grep -q alive
}

say "=== C1 strict-bank start: 6 cells, resume-safe ==="

# One trainer at a time -- two on the same GPU is an OOM, not a speedup.
if training_alive; then
    say "a train_budget run is already in flight; waiting for it to finish"
    while training_alive; do sleep 60; done
    say "in-flight run finished; starting the queue"
fi

ok=0; skipped=0; failed=0
FAILED_CELLS=""

for r in 10 25; do
  for s in 0 1 2; do
      out="runs/budget_r${r}_strict_seed${s}/result.json"
      log="runs/budget_r${r}_strict_s${s}.out"

      if [ -f "$out" ]; then
          say "SKIP r=$r strict seed=$s (result.json exists)"
          skipped=$((skipped + 1))
          continue
      fi

      for attempt in 1 2; do
          # vietocr caches the lmdb as ./train_<dataset> and REUSES it whenever the folder exists,
          # without checking that it matches the annotation it was built from. A crashed/partial
          # build would then be silently trained on. Purge it so every attempt builds from the
          # annotation this cell actually names.
          rm -rf "train_budget_r${r}_strict"
          say "START r=$r arm=strict seed=$s (attempt $attempt/2)"
          "$PYTHON_EXE" scripts/train_budget.py --r "$r" --arm strict --seed "$s" > "$log" 2>&1
          [ -f "$out" ] && break
          say "  attempt $attempt produced no result.json"
          [ "$attempt" = "1" ] && sleep 30
      done

      if [ -f "$out" ]; then
          cer=$("$PYTHON_EXE" -c "import json;print(f\"{json.load(open(r'$out'))['cer']:.4f}\")" 2>/dev/null)
          say "OK   r=$r strict seed=$s  CER=${cer:-?}"
          ok=$((ok + 1))
      else
          say "FAIL r=$r strict seed=$s -- see $log (tail below)"
          tail -5 "$log" | sed 's/^/       | /'
          failed=$((failed + 1))
          FAILED_CELLS="$FAILED_CELLS r${r}_strict_s${s}"
      fi
  done
done

say "=== C1 grid done: $ok trained, $skipped skipped, $failed failed ==="
[ -n "$FAILED_CELLS" ] && say "failed cells:$FAILED_CELLS  (just re-run this script -- it resumes)"

say "=== aggregate (strict vs full-bank vs real-only) ==="
"$PYTHON_EXE" scripts/aggregate_budget.py

say "=== C1 DONE ==="
