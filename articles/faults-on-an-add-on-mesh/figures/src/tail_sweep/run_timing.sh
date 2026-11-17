#!/bin/bash
# Controlled timing: H0 and H1 at S 0.002 side by side (eight ranks, the same load on
# both), with -log_view for the event breakdown. Waits until no other arm is running.
set -u
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
PIXI="pixi run --manifest-path $HOME/+Underworld/underworld3-pixi/.claude/worktrees/fault-split-integration/pixi.toml -e amr-dev"
while pgrep -f "tail_sweep_box.py" > /dev/null; do sleep 20; done
for h in H0 H1; do
    tag="B_s0.002_${h}_np4_logview"
    echo "$(date +%H:%M:%S) start $tag"
    $PIXI mpirun -np 4 python tail_sweep_box.py -uw_spacing 0.002 -uw_hier "$h" \
        -uw_out "timing/${tag}.json" -log_view > "timing/${tag}.log" 2>&1 &
done
wait
echo "$(date +%H:%M:%S) end"
