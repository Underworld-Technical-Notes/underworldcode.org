#!/bin/bash
# Problem B queue (FAC arms): np 4, one arm at a time. An arm is S:H, S:H:nofac (the FAC patch
# smoother off, UW_CUSTOM_MG_DISABLE_FAC=1) or S:H:probe (the set-up probe: one Newton
# increment, for the smoothers as installed; record in probes/).
set -u
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
PIXI="pixi run --manifest-path $HOME/+Underworld/underworld3-pixi/.claude/worktrees/fault-split-integration/pixi.toml -e amr-dev"
for arm in "$@"; do
    IFS=: read -r s h flag <<< "$arm"
    flag=${flag:-}
    env_set=(); extra=(); dir=records; logdir=logs; suffix=""
    case "$flag" in
        nofac) env_set=(UW_CUSTOM_MG_DISABLE_FAC=1); suffix="_nofac" ;;
        probe) extra=(-uw_probe 1); dir=probes; logdir=probes; suffix="_probe" ;;
        faclu) extra=(-uw_fac_lu 1); suffix="_faclu" ;;
        "") ;;
        *) echo "unknown flag $flag"; exit 1 ;;
    esac
    tag="B_s${s}_${h}${suffix}_np4"
    echo "$(date +%H:%M:%S) start $tag"
    env ${env_set[@]+"${env_set[@]}"} $PIXI mpirun -np 4 python tail_sweep_box.py -uw_spacing "$s" -uw_hier "$h" \
        ${extra[@]+"${extra[@]}"} -uw_out "${dir}/${tag}.json" > "${logdir}/${tag}.log" 2>&1
    echo "$(date +%H:%M:%S) end $tag"
done
