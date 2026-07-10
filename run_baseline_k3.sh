#!/usr/bin/env bash
set -u
export PYTHONIOENCODING=utf-8 TORCH_HOME="E:/ocr_engine/.torch" PYTHONUTF8=1
for S in 0 1 2; do
  echo "########## SEED $S start $(date) ##########"
  .venv/Scripts/python.exe scripts/train_baseline.py --seed "$S" 2>&1 \
    | tr '\r' '\n' | grep -v -E "it/s\]|it/s\]$" | tail -n 400
  echo "########## SEED $S done  $(date) rc=$? ##########"
done
echo "ALL SEEDS COMPLETE"
