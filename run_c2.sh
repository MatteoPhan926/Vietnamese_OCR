#!/usr/bin/env bash
# §14.2 (C2) k=5 AT THE HEADLINE POINT -- unattended driver.
#
#   bash run_c2.sh
#
# 4 runs: r=10% x {real-only, strict} x seed in {3,4}, taking the headline point to k=5 vs k=5.
# Authorized by the brain ONLY because the strict arm SURVIVED at r=10% (C1: GREEN, +2.810 pp).
#
# `[PRE-COMMITTED]` (§14.2): the k=5 numbers REPLACE the k=3 numbers REGARDLESS OF DIRECTION.
# Adding seeds after a green is honest only under that pre-commitment -- it can KILL the green;
# it can never be used to shop for one. No cherry-picking of seeds, no reverting to k=3 if k=5
# is less flattering.
#
# Resume-safe: a cell with a result.json is SKIPPED.

PYTHON_EXE="./.venv/Scripts/python.exe"

if [ ! -f "$PYTHON_EXE" ]; then
    echo "FATAL: no python at $PYTHON_EXE (run from E:/ocr_engine)"
    exit 1
fi

export TMPDIR=E:/ocr_engine/.tmp
export PYTHONIOENCODING=utf-8
mkdir -p "$TMPDIR" runs

MASTER="runs/c2_k5.log"

# single-instance lock (mkdir is atomic) -- see the C1 incident: two drivers on one cell race
# vietocr's lmdb cache (keyed by dataset NAME) and one reads it half-written.
LOCK="runs/.c2.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
    echo "run_c2.sh is already running (lock: $LOCK). Not starting a second driver."
    echo "If you are sure none is running: rmdir $LOCK"
    exit 1
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

exec > >(tee -a "$MASTER") 2>&1

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

training_alive() {
    powershell -NoProfile -Command 'if (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "train_budget" }) { "alive" }' 2>/dev/null | grep -q alive
}

say "=== C2 start: k=5 at r=10%, both arms (4 cells), resume-safe ==="

if training_alive; then
    say "a train_budget run is already in flight; waiting for it to finish"
    while training_alive; do sleep 60; done
    say "in-flight run finished; starting the queue"
fi

ok=0; skipped=0; failed=0
FAILED_CELLS=""

for arm in real strict; do
  for s in 3 4; do
      out="runs/budget_r10_${arm}_seed${s}/result.json"
      log="runs/budget_r10_${arm}_s${s}.out"

      if [ -f "$out" ]; then
          say "SKIP r=10 $arm seed=$s (result.json exists)"
          skipped=$((skipped + 1))
          continue
      fi

      for attempt in 1 2; do
          # purge the cell's lmdb: vietocr reuses ./train_<dataset> by NAME without checking it
          # matches the annotation, so a stale/partial cache would be trained on silently.
          rm -rf "train_budget_r10_${arm}"
          say "START r=10 arm=$arm seed=$s (attempt $attempt/2)"
          "$PYTHON_EXE" scripts/train_budget.py --r 10 --arm "$arm" --seed "$s" > "$log" 2>&1
          [ -f "$out" ] && break
          say "  attempt $attempt produced no result.json"
          [ "$attempt" = "1" ] && sleep 30
      done

      if [ -f "$out" ]; then
          cer=$("$PYTHON_EXE" -c "import json;print(f\"{json.load(open(r'$out'))['cer']:.4f}\")" 2>/dev/null)
          say "OK   r=10 $arm seed=$s  CER=${cer:-?}"
          ok=$((ok + 1))
      else
          say "FAIL r=10 $arm seed=$s -- see $log (tail below)"
          tail -5 "$log" | sed 's/^/       | /'
          failed=$((failed + 1))
          FAILED_CELLS="$FAILED_CELLS r10_${arm}_s${s}"
      fi
  done
done

say "=== C2 grid done: $ok trained, $skipped skipped, $failed failed ==="
[ -n "$FAILED_CELLS" ] && say "failed cells:$FAILED_CELLS  (just re-run this script -- it resumes)"

say "=== aggregate (k=5 at r=10% now REPLACES k=3, per the §14.2 pre-commitment) ==="
"$PYTHON_EXE" scripts/aggregate_budget.py

say "=== C2 DONE ==="
