# Inputs of the restart table (RESTART_AND_RECORDS.md section 5, UWTN 2026-022)

Trimmed copies of the six runs' `records.json` (steps 3580-3600 only), from kaiju
`~/campaigns/dev-restart-runs/<run>/`, with each run's `run_info.json` where it has one and
otherwise `PROVENANCE.txt` (the job log's Script / Container / overlay lines, as
`analysis/restart_table.py` prints them). Pairs: old_a/old_b (original driver), new_a/new_b
(decision state + V_b warm start), i3_a/i3_b16 (faulted-mesh checkpoint); `_a` ran 3580->3600
uninterrupted, `_b` restarted from its own 3590 checkpoint for 10 steps. Regenerate the table
from `figures/src/`, whose `restart_table.py` reads these directories by default:

    python restart_table.py

The i3 pair's run_info.json driver_commit values (998de2aa,
b0147e1c) predate the faulted-mesh checkpoint they test (81727da / 460e49d) and are stale.
