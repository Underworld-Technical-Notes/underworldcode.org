# UWTN 2026-022: band-ratio sweep of the multigrid hierarchy under the finest ladder

Requested 2026-10-29 by the notes session (underworld-technical-notes-25), on Louis's
word: "I am very unsure at this point that we recorded the best cases. This should be
resolved before we publish any results."

## Provenance

- underworld3 `feature/fault-split-integration` at 799ef021 (src identical to 4698938f,
  PR #890), built into that worktree's `amr-dev` environment (installed files checked
  against the source), PETSc 3.25.0, macOS (Wombat-3), OpenMPI, `OMP_NUM_THREADS=1`.
- Problem B's rheology and walls come from `box_model.py` in uw3-campaigns
  `zg95_lid_regimes/drivers` (local checkout at 2a4b21a; `box_model.py` and
  `box_fault.py` are identical on origin/main 0b990aa). Nothing in uw3-campaigns was
  changed; the chain placement option lives in this folder's script.

## The hierarchies

The solver mesh is always the S ladder placed in a copy of the base's finest level
(`place_fault_ribbon_2d(host, [(name, trace)], 2kS, margin_rings=1, clearance=0.7,
split=True, mesher="ladder")`, band 2kS wide, square cells). Only the multigrid levels
under it change, through `set_custom_fmg(stokes, levels, field_id=0)`, with the same
solver options in every arm.

| | levels under the S ladder |
|---|---|
| H0 | all base levels welded (1/8, 1/16, 1/32) |
| H1 | the lean chain (production, `uw_chain=2`): 1/8 welded, 4S in 1/16, 2S in 1/32 |
| H2 | graded chain in copies of the finest: 1/8, 1/16, 1/32 welded, then 2^J S ... 2S all in 1/32; J the smallest j with h_b/(2^j S) <= 4 (J = 1, 2, 3 at ratios 6, 12, 25) |
| H1c | H1 with every band 2S wide (not widened) |
| H3 | hybrid: 1/8 welded, 4S in 1/16, then 2^J S ... 2S in 1/32 (J >= 2) |

## Problem A, linear: `tail_sweep_linear.py`

The note's fixture: unit box, `UnstructuredSimplexBox(cellSize=1/8, refinement=2,
regular=False, qdegree=2)` (h_b = 1/32), fault (0.30, 0.45)-(0.70, 0.55), unit
viscosity, simple shear v = (y - 1/2, 0) on every wall, frictionless contact
(`add_fault_bc`), tolerance 1e-6. n_rungs = 80, 160, 320 (h_b/S = 6.06, 12.1, 24.2).
np 1 and np 4.

Each run solves twice: the first solve includes the multigrid set-up (`set_custom_fmg`
defers the transfer build to the first solve), the second solves again from zero on
the cached operators with every application of the velocity sub-KSP counted. Set-up
is placement plus the difference of the two solve times.

    ./run_linear.sh 80:H0 80:H1 80:H2 160:H0 160:H1 160:H2 160:H3 320:H0 320:H1 320:H2 320:H3 320:H1c

## Problem B, nonlinear: `tail_sweep_box.py`

The guide's hard state. The faults-in-convection guide's table was measured by
`~/+Simulations/zg95/box_faults/probes/hierarchy_a_vs_c.py` on the fixed-trench fault
run's checkpoint 2000 (`runs/stagnant_tau1x1.00_fault_x2.0_dip45`, t 0.2316, mobility
0.70), not on `mobile_ref_H1.42` 1975 (that is the stagnant source the fault run
started from). This script uses checkpoint 2000 and the probe's solve: one Stokes
solve from rest, `picard=0`, `consistent_jacobian="continuation"`,
`newton_switch_rtol=1e-2`, tolerance 1e-3, np 4. The weak bridge is the probe's (band
cells above the split's upper tip). One change the head forces: it refuses a yield
stress that reads a field unless a floor is declared, and this one,
(tau0 + tau1 depth) x weak with weak >= 1e-3, stays positive, so
`yield_stress_min = -oo` (no floor), as in the guide's runs.

`uw_spacing` = 0.004, 0.002, 0.00125. The spine count is a multiple of max(4, 2^J) at
each spacing (132, 260, 416 intervals), so the finest mesh is the same in every arm at
a spacing; the actual S and h_b/S are in the records (7.9, 15.5, 24.8).

    ./run_box.sh 0.004:H1 0.004:H0 0.004:H2 0.002:H1 0.002:H2 0.002:H0 0.002:H3
    ./run_box.sh 0.00125:H1 0.00125:H2 0.00125:H0 0.00125:H3 0.00125:H1c

These were run as two to three queues side by side (never more than eight ranks); the
start and end of every arm are in `logs/queue_box*.log`, and an arm's log is
`logs/B_s<S>_<H>_np4.log`.

## Which smoother each arm ran (added at the notes session's request)

Every record now carries `level_smoothers` (each level's KSP and PC type as installed;
for a composite level the ASM blocks, their rows summed over the ranks and the block
solver) and `mg_env` (any `UW_FAC_*`, `UW_CUSTOM_MG_*` or `UW_MG_*` variable). Problem A
was rerun to record them (`records_v1/` keeps the first pass; all 24 arms reproduce it
exactly). The B arms run before the change have a set-up probe each in `probes/`: the
same script with `-uw_probe 1`, its rotated loop capped at one Newton increment.

- No `UW_FAC_*`, `UW_CUSTOM_MG_*` or `UW_MG_*` variable was set in any run except the
  `nofac` arms (`UW_CUSTOM_MG_DISABLE_FAC=1`). The queue scripts set only
  `OMP_NUM_THREADS=1`; the pixi activation adds `OPENBLAS_NUM_THREADS` and `PETSC_DIR`.
- The FAC patch smoother is installed only on H0's finest level (S over the welded
  1/32), serial and np 4, both problems. In `custom_mg.py` (4698938f, line 1556) every
  pair touching a split coarse level takes the cell-located transfer and skips the FAC
  detection, so H1, H1c, H2 and H3 run whole-level SOR on every level. H1 with
  `UW_CUSTOM_MG_DISABLE_FAC=1` is therefore the same as H1 (A identical; B 987 against
  990, within the run-to-run spread of the parallel nonlinear solve).
- The FAC blocks run ILU(0), not the LU `custom_mg` writes. `_configure_pcmg` writes
  `mg_levels_<l>_sub_1_sub_pc_type lu` and a nonzero factor shift into the options DB.
  The rotated path (`rotated_bc.py`, after "Force the FAC levels' smoother setup NOW")
  calls `setUp()` on the level smoother and then deletes the keys, but a composite PC
  sets up its children at first application, so the ASM child creates its block KSPs
  after the keys are gone and takes PCASM's default ILU(0). The same code is on
  development. Filed as underworldcode/underworld3#892.
- `-uw_fac_lu 1` (both scripts) keeps the block keys in the DB, so the blocks run LU as
  intended: the `faclu` arms. `nofac` turns the patch off: H0 with whole-level SOR on
  every level.

    ./run_followup.sh     # probes, problem A again (+ H1 nofac), B H1 nofac at S 0.002
    ./run_fac_arms.sh     # B H0 faclu at 0.004, 0.002, 0.00125, B H0 nofac at 0.002,
                          # A H0 faclu and nofac at every ratio, np 1 and 4

## Controlled timing

Wall times elsewhere in the tables are from runs with another run beside them, not
always the same one. `run_timing.sh` ran H0 and H1 at S 0.002 side by side (eight
ranks, the same load on both) with `-log_view` (`timing/`): solve 1135 s (H0) and
1269 s (H1), the iteration counts as in the main runs (1464 and 990 last per
increment). In H1's log the SOR flops are unbalanced across the four ranks (max/min
2.5) and the reductions wait (VecMDot time ratio 6.7); H0's are within 1.3.

## What is recorded

`records/*.json`, one per arm; `collect_records.py` writes `summary.md` and
`records_all.json`. Per arm: the hierarchy, h_b/S, each level's cell count (owned
cells summed over ranks) and the velocity operator's rows and nonzeros per row per
multigrid level, the velocity sub-KSP iterations (`vel_its_last`: the LAST application
per Newton increment, as the guide and the note count them; for B also the total over
every application, from the converged-reason lines in the log), outer and pressure
iterations, Newton iterations and the Picard-to-Newton switch (B), the 200 caps, the
set-up and solve wall times, and the peak slip.

Cost per velocity iteration is compared by two measures, both from the level operators'
nonzeros (`collect_records.py`):

- operator complexity, the nonzeros of every level over the finest level's;
- F-cycle complexity, the same with each level weighted by how often one application
  smooths it. The velocity multigrid is `pc_mg_type full`: it runs a V-cycle from each
  level in turn, so the level d steps below the finest is smoothed d + 1 times. A deep
  hierarchy whose upper levels are nearly as large as the finest (the graded chains)
  pays for that several times over.

"work" is the velocity iterations over every application times the F-cycle complexity.
In problem A, the second solve's wall time divided by this work is flat to about 25%
across the hierarchies (np 1, h_b/S 24: 13 to 17 ms), where per iteration times
operator complexity it is not (19 to 47 ms).

Wall times are from a laptop with two queues at once (eight ranks); compare iteration
counts and work.

## Rerun on development before release (2026-11-24)

Run approved by Louis to check the simple-shear result on the release's build.
underworld3 `development` at a673cd52 (PR #1279 merged, 2026-11-21), built into a
fresh worktree's `default` environment (conda-forge PETSc 3.25.3, OpenMPI, not the
old `amr-dev` worktree; `pip install .`, not editable), macOS (Wombat-3),
`OMP_NUM_THREADS=1`, serial. The script is unchanged. Records and logs are in
`records_dev_a673cd52/`; `records/` is untouched.

    python compare_dev.py records_dev_a673cd52

| arm | velocity its / applications | peak slip | patch blocks |
|---|---|---|---|
| A_r80_H0_faclu | 66 / 17 (3.88), as before | 0.15951006, as before | LU |
| A_r160_H0_faclu | 65 / 17 (3.82), as before | 0.15925955, as before | LU |
| A_r320_H0_faclu | 67 / 17 (3.94), as before | 0.15920954, as before | LU |
| A_r80_H0 (no `-uw_fac_lu`) | 66 / 17; was 180 / 17 with ILU(0) | 0.15951006 | LU |

The LU arms reproduce exactly; peak slip agrees to 1e-15. The default arm now matches
them: #912 (cc839425) made the rotated path install LU on the patch blocks, so
`-uw_fac_lu 1` is no longer needed on development. The note's ILU(0) row remains the
measurement of that smoother, taken when it was what the default ran.
