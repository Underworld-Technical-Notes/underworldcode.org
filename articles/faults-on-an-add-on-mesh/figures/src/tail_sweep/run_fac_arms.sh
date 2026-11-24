#!/bin/bash
# After the follow-up queues: the two serial jobs for the notes session (the figure's
# placements with the clearance each took; the note's recipe, unedited), then the H0
# FAC arms: the patch blocks by LU (faclu) and the patch off (nofac). Two queues of
# four ranks side by side.
set -u
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
PIXI="pixi run --manifest-path $HOME/+Underworld/underworld3-pixi/.claude/worktrees/fault-split-integration/pixi.toml -e amr-dev"
LADDER=$HOME/+Simulations/uwtn_2026_022_ladder
SKILLS=$HOME/+Underworld/underworld3-pixi/.claude/worktrees/fault-split-integration/.claude/skills/uw-line-diagrams
SP=/private/tmp/claude-501/-Users-lmoresi--Underworld-underworld3-pixi/4b87baab-f49d-4eb1-8e76-9bd1c1f1c240/scratchpad
while pgrep -f "run_followup.sh|tail_sweep_box.py|tail_sweep_linear.py" > /dev/null; do sleep 30; done
echo "$(date +%H:%M:%S) start serial"
(cd "$LADDER" && $PIXI python place_log.py fig_ladder_construction.py -uw_out "$SP/ladder_placelog" \
    -uw_skills "$SKILLS" > place_log_figure.log 2>&1)
(cd "$SP/recipe" && $PIXI python "$LADDER/place_log.py" recipe.py > "$LADDER/place_log_recipe.log" 2>&1)
echo "$(date +%H:%M:%S) end serial"
(./run_box_fac.sh 0.002:H0:faclu 0.004:H0:faclu
 ./run_linear.sh 80:H0:faclu 80:H0:nofac 160:H0:faclu 160:H0:nofac 320:H0:faclu 320:H0:nofac) \
    > logs/queue_fac_a.log 2>&1 &
./run_box_fac.sh 0.002:H0:nofac 0.00125:H0:faclu > logs/queue_fac_b.log 2>&1 &
wait
echo "$(date +%H:%M:%S) end"
