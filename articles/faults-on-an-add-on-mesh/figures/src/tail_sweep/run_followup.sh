#!/bin/bash
# After the timing pair: the FAC records. Two queues of four ranks side by side:
#   P: the set-up probe for every B arm, then problem A again (smoothers recorded) with
#      H1 also at UW_CUSTOM_MG_DISABLE_FAC=1;
#   N: B H1 at S 0.002 with UW_CUSTOM_MG_DISABLE_FAC=1 (a full solve).
set -u
cd "$(dirname "$0")"
while pgrep -f "run_timing.sh|tail_sweep_box.py|tail_sweep_linear.py" > /dev/null; do sleep 30; done
(./run_box.sh 0.004:H0:probe 0.004:H1:probe 0.004:H2:probe \
              0.002:H0:probe 0.002:H1:probe 0.002:H2:probe 0.002:H3:probe \
              0.00125:H0:probe 0.00125:H1:probe 0.00125:H2:probe 0.00125:H3:probe 0.00125:H1c:probe
 ./run_linear.sh 80:H0 80:H1 80:H1:nofac 80:H2 160:H0 160:H1 160:H1:nofac 160:H2 160:H3 \
                 320:H0 320:H1 320:H1:nofac 320:H2 320:H3 320:H1c) > logs/queue_followup_P.log 2>&1 &
./run_box.sh 0.002:H1:nofac > logs/queue_followup_N.log 2>&1 &
wait
