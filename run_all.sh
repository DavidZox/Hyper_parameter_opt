#!/usr/bin/env bash
# 一鍵重現：14 組簡報實驗 → 與簡報比對 → 彙整報告 → 多種子研究。完整 log 存在 logs/run_all.log
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
export MPLCONFIGDIR="$PWD/.cache/matplotlib"   # matplotlib 字型快取放在專案內
export PYTHONUNBUFFERED=1                       # 進度即時寫入 log
PY=${PYTHON:-python}
SEEDS=${SEEDS:-20}

{
  echo "===== $(date '+%F %T') run_all.sh ====="
  "$PY" -c "import sys, pymoo, numpy, matplotlib; print('python', sys.version.split()[0], '| pymoo', pymoo.__version__, '| numpy', numpy.__version__, '| matplotlib', matplotlib.__version__)"
  echo; echo "### [1/4] 執行 14 組簡報實驗"
  "$PY" scripts/run_experiment.py --all
  echo; echo "### [2/4] 與簡報逐項比對"
  "$PY" scripts/verify_slides.py
  echo; echo "### [3/4] 彙整報告與比較圖"
  "$PY" scripts/make_report.py
  echo; echo "### [4/4] 多種子研究（${SEEDS} 個種子 + seed 42）"
  "$PY" scripts/seed_study.py --seeds "$SEEDS"
  echo; echo "===== $(date '+%F %T') 完成 ====="
} 2>&1 | tee logs/run_all.log
