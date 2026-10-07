#!/usr/bin/env bash
# DAS732 A2 (Team Silica) - regenerate every output from data/processed (+ optional raw rebuild).
# Usage:  bash run_all.sh            (figures + report)
#         REBUILD_RAW=1 bash run_all.sh   (also re-subset gridMET from the raw files)
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONUTF8=1
PY=${PYTHON:-python}

if [[ "${REBUILD_RAW:-0}" == "1" ]]; then
  $PY scivis/common/download_gridmet.py
  $PY scivis/common/load_gridmet.py
fi
$PY scivis/common/stats_and_dates.py
$PY infovis/common/a1_preprocess.py
$PY scivis/s1_colormapping/run.py
$PY scivis/s2_contours/run.py
$PY scivis/s3_quiver_streamlines/run.py
$PY infovis/i1_network/run.py
$PY infovis/i2_web/screenshots.py
$PY infovis/i3_horizon_ridgeline/run.py
cd report
$PY build_report_assets.py
latexmk -pdf -interaction=nonstopmode main.tex
cp main.pdf DAS732_A2_Report.pdf
