#!/bin/bash
# Problem A queue: np 1 then np 4, one arm at a time. An arm is n_rungs:H,
# n_rungs:H:nofac (the FAC patch smoother off, UW_CUSTOM_MG_DISABLE_FAC=1) or
# n_rungs:H:faclu (the FAC patch blocks solved by LU, -uw_fac_lu 1).
set -u
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
PIXI="pixi run --manifest-path $HOME/+Underworld/underworld3-pixi/.claude/worktrees/fault-split-integration/pixi.toml -e amr-dev"
for np in 1 4; do
    for arm in "$@"; do
        IFS=: read -r r h flag <<< "$arm"
        flag=${flag:-}
        env_set=(); extra=(); suffix=""
        case "$flag" in
            nofac) env_set=(UW_CUSTOM_MG_DISABLE_FAC=1); suffix="_nofac" ;;
            faclu) extra=(-uw_fac_lu 1); suffix="_faclu" ;;
            "") ;;
            *) echo "unknown flag $flag"; exit 1 ;;
        esac
        tag="A_r${r}_${h}${suffix}_np${np}"
        echo "$(date +%H:%M:%S) start $tag"
        env ${env_set[@]+"${env_set[@]}"} $PIXI mpirun -np "$np" python tail_sweep_linear.py -uw_n_rungs "$r" \
            -uw_hier "$h" ${extra[@]+"${extra[@]}"} -uw_out "records/${tag}.json" > "logs/${tag}.log" 2>&1
        echo "$(date +%H:%M:%S) end $tag"
    done
done
