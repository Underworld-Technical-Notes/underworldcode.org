#!/bin/bash
# Regenerate UWTN 2026-022's trench figures and numbers. Python 3 with numpy, scipy, h5py and
# matplotlib (on Kaiju the uw3 container's python3).
#
#   bash make_all.sh [H5_DIR]
#
# trench-mesh.png and trench-cost.png are written to the note's figures/ (../../.. from here);
# trench_mesh.json, trench_cost.json and run_summary.json to ../. trench_cost.py and run_summary.py
# read only the records shipped in ../data. trench_mesh.py also reads the four steps' solver-mesh
# h5 files and the base mesh's (72 MB, not in the repository; ../README.md says where they are and
# ../data/SHA256SUMS checks them): give their folder as H5_DIR, which must also hold the state_*.json
# and records_trimmed.json of ../data (Kaiju's figures_out/uwtn_2026_022/data/ holds all of them).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
H5="${1:-$HERE/../data}"
python3 "$HERE/trench_mesh.py" -uw_data "$H5"
python3 "$HERE/trench_cost.py" > /dev/null
python3 "$HERE/run_summary.py"
