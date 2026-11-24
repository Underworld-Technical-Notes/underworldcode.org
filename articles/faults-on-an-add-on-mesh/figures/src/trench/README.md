<!-- UWTN 2026-022 copy, 2026-11-17: K1's README as rsynced from kaiju. In this copy the h5
files of data/ are not shipped, the scripts' titles and labels use the note's terms, and the
PNGs are written to the note's figures/ (see ../README.md, "The trench figures and movie"). -->

# UWTN 2026-022 figures: earth_recipe_movie

Figures, movie and numbers for the technical note, made on Kaiju on 2026-11-17 from the existing outputs of
one run, earth_recipe_movie. No new model runs. Everything here regenerates from this folder alone (see
"How to regenerate").

| file | what | size |
|---|---|---|
| `trench-mesh.png` | the solver mesh at the trench at four steps (2440 x 2133 px, 200 dpi) | 3.2 MB |
| `trench-cost.png` | cost per step by phase, peak slip rate, the band's cells (2000 x 2240 px, 200 dpi) | 0.4 MB |
| `earth_recipe_movie_meshfixedT_0-799_web.mp4` | the publication movie (index moved to the front, no re-encode; see "Movie") | 8.0 MB |
| `movie-still-step460.png` | a still from the movie's own frames: step 460 (1920 x 1080 px) | 1.7 MB |
| `trench_mesh.json`, `trench_cost.json`, `run_summary.json` | every number quoted below, written by the scripts | small |
| `scripts/` | `trench_mesh.py`, `trench_cost.py`, `run_summary.py`, `make_all.sh`, `trim_records.py` | small |
| `data/` | the four steps' solver-mesh h5 and state json, the base mesh h5, the trimmed records, run_info.json, ARGS.txt, the list of steps that kept their mesh, SHA256SUMS | 75 MB |

No PDF versions: the earlier trench_mesh.py / trench_cost.py these scripts were adapted from wrote PNG only.

## The run

- Path: `/home/louis/+Claude/kaiju/runs/earth_recipe_movie` (read only; its README.md gives the recipe).
- Slurm job 4417, one start, no resume. `run_info.json` holds one start (`restart_from` None), the records run
  steps 0 to 799 with no restart step (no `restart_first` kind), and the job's own log
  (`runs/crust_x_4417.out`) shows one launch, 2026-11-12 07:41:08 AEDT on n2, ending 2026-11-13 09:08:37 with
  exit 0. The names `ARGS_resume.txt` and `slurm_resume.out` come from the launch script
  (`launch/pack3/movie_job.sh` always reads `ARGS_resume.txt` and writes `slurm_resume.out`); `ARGS.txt` and
  `ARGS_resume.txt` are identical.
- np 26, all on one node (26 ranks per node, exclusive), container `uw3-gadi-development-20261021.sif`,
  PETSc 3.25.0.
- Driver: `zg95_lid_regimes/drivers/annulus_faults.py` at commit d358b9775d091b3e307b3f4b5c324f2946f88f85
  (run_info `driver_commit`), clone `kaiju/clones/zg95-v2-d358b97` (branch kaiju/fault-spline-base, per the
  run's README). Checked
  here: the clone's HEAD is d358b97, its working tree is clean and the driver file hashes to blob a85fca4, as
  the run's README says. The run's README gives the pushed commit as 31c7e08 (not checked here: Kaiju has no
  GitHub access).
- Library: underworld3 80d3ebe9 (80d3ebe96c96da16fa3341841a3838375ba5718a, "Merge pull request #1014 ...
  feature/convergence-reference-policy", 8 Nov 2026). run_info's `uw3_commit` is None (the overlay is not a
  git checkout, so the driver could not read a commit), so it was established from:
  1. the job's log, `runs/crust_x_4417.out`, first line: `crust_x earth_recipe_movie (zg95-v2-d358b97,
     /home/louis/+Claude/kaiju/uw3/overlay-dev-80d3ebe9) on n2` (movie_job.sh prints its `$LIB`, the overlay
     its optional third argument names);
  2. movie_job.sh binds that `$LIB` to `/uw3-extra` and puts it first on PYTHONPATH, and run_info's
     `uw3_path` is `/uw3-extra/underworld3/__init__.py`: the imported underworld3 was the overlay's;
  3. the overlay's `BUILD_COMMIT` file reads 80d3ebe96c96...; its build log (`kaiju/uw3/build-80d3ebe9.log`)
     installs from `kaiju/uw3/src-80d3ebe9`, whose git HEAD is 80d3ebe9;
  4. no file in the overlay is newer than the run's start (`find -newermt '2026-11-12 07:41' -type f`: none);
  5. the run's README says "build underworld3 80d3ebe9".
  The run's log has no line naming the library version.
- Steps 0 to 799 (800 steps, every one converged). Model time at the end of step 0 is t = 1.202e-5
  (3.2 Myr) and at the end of step 799 t = 4.1374e-3, 1,102.6 Myr (Myr = t x 266,497; the run's README
  rounds to 1,105 Myr). Time step 0.76 to 3.20 Myr, mean 1.38.
- Annulus r_o 2.2222, r_i 1.2222 (6,444 and 3,544 km); base mesh uw_cell 0.5, refinement 5: base cell
  0.015625 (45.3 km), six levels of 124, 496, 1,984, 7,936, 31,744 and 126,976 cells (records `levels_cells`
  at every build; the base h5 has 126,976 cells).

## Settings

| setting | value | meaning |
|---|---|---|
| uw_chain | 0 | the solver's hierarchy is the base mesh's six levels, uncut, under the faulted finest level (records `levels_cells`: 124 ... 126,976, then 126,976 + the band's cells) |
| uw_rebuild_cells | 0 | rebuild the faulted mesh whenever the fitted fault differs from the built one (threshold 0 base cells) |
| uw_detect_every / uw_detect_start | 1 / 0 | the fault is located (fitted) every step from step 0; uw_fault_lagrange 0, spline fit to the crust layer's base |
| rung spacing S | uw_spacing 0.0078125 = 22.7 km | half a base cell; run_info effective `rung_spacing` 0.0078125; 31 to 45 rungs per build (median 37), mean rung length 0.0077 to 0.0079 |
| band width W | 2S = 0.015625 = 45.3 km | the driver places W = 2S (uw_band_widen 1); records `mesh.width` 0.015625 at every build |
| split inset | uw_split_inset 1.0 rung (22.7 km), uw_split_inset_along 1 | the fault's cut stops one rung inside the outer wall, measured along the fault from where its spine crosses the wall |
| uw_tol | 1e-3 | nonlinear (relative residual) tolerance; final relative residual 5.8e-6 to 9.9e-4 |
| velocity rtol | 3.3e-5 (effective, 0.033 x uw_tol) | velocity sub-KSP, custom FMG preconditioner |
| pressure rtol | uw_pres_rtol 1e-2 (warm solves), uw_pres_rtol_cold 1e-4 (cold: the first solve) | Schur (pressure) sub-KSP, 1/mu mass preconditioner. The value read back after each solve (records `solver.pres_rtol`) is 0.1 at 790 steps and 0.0035 to 0.037 at 10: the library relaxes the sub-KSP rtol on a solve's last increments, by how far the absolute floor relaxed the outer target, capped at 0.1 (rotated_bc.py `_set_absolute_target`, #911) |
| Picard to Newton | uw_newton_switch 0.01, uw_warm_newton_switch 0.1, uw_rebuild_newton_switch 0.01; uw_picard 0 | consistent_jacobian "continuation" |
| checkpoint | uw_ckpt_every 1 | every step; its write time is recorded as its own phase |

KSP iteration-cap hits: none. Counted from the records: for each of the 5,580 nonlinear iterations, the
outer count (`ksp_its`) against the outer cap 300, and the velocity and pressure sub-KSP counts (`vel_its`,
`pres_its`) against their caps 200 (caps from underworld3 80d3ebe9, `utilities/rotated_bc.py`, the rotated
free-slip solve this run uses). Largest counts: outer 1, velocity 14, pressure 38. The log has no
"DIVERGED" line. Caveat: the sub-KSP counts in the records are those of the last application in each
nonlinear iteration, not of every application.

Every placement that succeeded did so at the first attempt (no "placed with" retry line in the log).

## Summary numbers

Steps by kind: 1 `init_first` (step 0, the base mesh, no fault yet: the fault forms at the end of step 0),
1 `rebuild_changed_set` (step 1, the first faulted mesh), 758 `rebuild_same_set`, 40 `ordinary`. So the
faulted mesh was rebuilt at 759 of steps 1 to 799; the 40 `ordinary` steps kept the step before's mesh:
28 because the fit found no slab top reaching the cap ("the fault keeps its place"), 12 because the placement
was refused ("the fault touches the domain boundary"; this driver kept the previous fault). They are listed,
with the log line, in `data/no_rebuild_steps.txt`.

Wall time per step, seconds, np 26, all 800 steps (records `solver.wall`; the record's `step` is timed before
the checkpoint write; "other" is `step` minus the seven phases before the checkpoint):

| phase | mean | median | min | max | share of the step | share with the checkpoint |
|---|---|---|---|---|---|---|
| build (the solver mesh) | 4.41 | 4.63 | 0 | 5.06 | 4.5 % | 3.8 % |
| transfer (fields onto it) | 2.83 | 2.87 | 2.26 | 3.09 | 2.9 % | 2.5 % |
| stokes | 81.66 | 82.91 | 5.10 | 168.75 | 82.5 % | 71.3 % |
| to_base (solution back) | 2.73 | 2.78 | 1.02 | 3.76 | 2.8 % | 2.4 % |
| energy_strain | 2.30 | 2.29 | 2.28 | 7.89 | 2.3 % | 2.0 % |
| swarm | 2.18 | 1.41 | 1.18 | 5.51 | 2.2 % | 1.9 % |
| detection | 0.07 | 0.07 | 0.01 | 0.11 | 0.1 % | 0.1 % |
| other | 2.80 | 2.79 | 2.61 | 3.20 | 2.8 % | 2.4 % |
| step, without the checkpoint | 98.98 | 100.32 | 18.71 | 189.68 | 100 % | 86.4 % |
| checkpoint write | 15.57 | 15.28 | 12.67 | 38.80 | | 13.6 % |
| step with the checkpoint | 114.54 | 115.87 | 32.13 | 204.55 | | 100 % |

Totals: 21.99 h of steps and 3.46 h of checkpoint writes, 25.45 h (the job ran 25.46 h). The swarm
phase's mean sits above its median because the crust is refilled every 5 steps (5.3 to 5.5 s those steps).

The three phases the separate solver mesh brings, per step:

| phase | the 759 steps that built a faulted mesh: mean / median / range | the 40 that kept the mesh: mean / median / range |
|---|---|---|
| build | 4.59 / 4.64 / 3.84 to 5.06 s | 1.08 / 0 / 0 to 3.70 s (0 when the fault kept its place; 3.5 to 3.7 s for the 12 refused placements, whose build was attempted) |
| transfer | 2.85 / 2.88 / 2.68 to 3.09 s | 2.37 / 2.38 / 2.26 to 2.42 s |
| to_base | 2.82 / 2.78 / 2.74 to 3.76 s | 1.04 / 1.03 / 1.02 to 1.24 s |

Together 10.3 s at a building step, 10.0 % of those steps' mean (102.8 s without the checkpoint); over all
800 steps 9.97 s, 10.1 % of the step (8.7 % with the checkpoint).

Iterations: 5,580 nonlinear iterations, 6.98 per step (median 7, 1 to 19), of which 3,139 Picard (3.92 per
step, 0 to 10) and 2,441 Newton (3.05 per step, median 2, 1 to 16); 1,063 line-search cutbacks; one cold
solve (step 0), all others warm. Linear: the outer KSP took 1 iteration in every nonlinear iteration; the
velocity sub-KSP 4.54 iterations on average at its last application (median 4, max 14), the pressure
sub-KSP 11.84 (median 11, max 38).

Trench (records `theta_trench`): -0.45 deg at step 0; rolls back to -20.26 deg at step 460 (515.1 Myr),
19.81 deg or 2,228 km at the surface; then advances to -15.35 deg at step 799, 4.90 deg or 551 km
(km = r_o x 2900 km x radians, 112.48 km per degree).

Peak slip rate on the fault (`slip_max`, model velocity units x 1.08819e-3 cm/yr, kappa 1e-6 m2/s over
2900 km): 0.65 to 3.74 cm/yr over steps 1 to 799 (minimum at step 3, maximum at step 51; 0.74 at step 799;
step 0 has no fault in its mesh).

## trench-mesh.png: the four steps and the caption numbers

The steps span the trench's motion: early (step 10), half-way through the rollback in angle (step 130: the
trench is closest there to the mean of -0.45 and -20.26 deg), the furthest rollback (step 460), and the
last step, after the advance (step 799). All four built their mesh at that step (`rebuild_same_set`).

| | step 10 | step 130 | step 460 | step 799 |
|---|---|---|---|---|
| why | early | mid-rollback | maximum rollback | late advance (last step) |
| model time | 26.2 Myr | 149.8 Myr | 515.1 Myr | 1,102.6 Myr |
| trench (records theta_trench) | -1.24 deg | -10.38 deg | -20.26 deg | -15.35 deg |
| fault dip | 29.7 deg | 24.8 deg | 23.5 deg | 26.1 deg |
| solver-mesh cells | 127,225 | 127,245 | 127,308 | 127,248 |
| cells the band adds (solver minus base 126,976) | 249 | 269 | 332 | 272 |
| Band label's cells (= records band_cells_per_rank, on one rank) | 131 | 144 | 174 | 144 |
| base cells replaced / cells put in their place | 127 / 376 | 124 / 393 | 163 / 495 | 121 / 393 |
| fault segments on each side (F0Plus = F0Minus labels) | 23 | 27 | 33 | 27 |
| base edges kept, of 191,168 | 190,995 (99.91 %) | 190,999 (99.91 %) | 190,947 (99.88 %) | 191,003 (99.91 %) |
| farthest changed base edge from the trace | 79 km | 97 km | 99 km | 95 km |
| base edges kept beyond 145 km (0.05) of the trace | 100 % of 190,784 | 100 % of 190,785 | 100 % of 190,686 | 100 % of 190,794 |
| base edges kept beyond 58 km (0.02) | 99.993 % | 99.990 % | 99.995 % | 99.991 % |

The base mesh's finest level has 126,976 cells (records `levels_cells`, and the base h5). How the edges were
counted: from the h5 topology itself (`geometry/vertices` and `viz/topology/cells` of each step's
`annulus.solver_mesh.NNNNN.h5` and of `annulus.mesh.00000.h5`). Each solver vertex is matched to the base
vertex at the same coordinates (within 1e-9) or marked new; a base edge is kept when the solver mesh has an
edge joining the two matched vertices. An edge is "beyond d" of the trace when both its vertices are farther
than d from the fault trace (`state_NNNNN.json` "traces": the fault built into that checkpoint's mesh),
using exact point-to-segment distances. The Band label's cells are the Band label's points that are
triangles in the checkpoint's `celltype` label. Each window is 858 x 630 km, the same for all four panels.

## Caption drafts

**trench-mesh.png.** The solver mesh around the trench of earth_recipe_movie at four steps: (a) step 10
(26 Myr), early; (b) step 130 (150 Myr), half-way through the trench's rollback; (c) step 460 (515 Myr), the
furthest rollback, 19.8 deg (2,228 km) from the start; (d) step 799 (1,103 Myr), the last step, after a
4.9 deg advance. Each window, 858 x 630 km, is rotated so that its trench is at the top; the inset locates it
on the annulus. Blue: the base mesh's edges; black: the solver mesh's edges, drawn over them, so an edge the
solver mesh keeps shows dark and a base edge it replaced shows light blue; red: the fault. The band adds 249
to 332 cells to the base's 126,976 (its own 131 to 174 cells and the cells that join it to the base mesh).
Every base edge farther than 100 km from the fault is unchanged; overall the solver mesh keeps 99.88 to
99.91 % of the base mesh's 191,168 edges.

**trench-cost.png.** Cost per step of earth_recipe_movie, 800 steps over 1,103 Myr on 26 processes of one
node. (a) Wall time per step by phase, without the checkpoint write (15.6 s a step on average, not shown): the
Stokes solve takes 82.5 % of the step; building the solver mesh, moving the fields onto it and the solution
back to the base mesh together take 10 %. (b) Those three phases per step. The low points are the 40 steps
that kept the step before's mesh: 28 at which the fit found no new fault position and 12 at which the new
placement was refused and the previous fault kept. (c) The peak slip rate on the fault, 0.65 to 3.74 cm/yr.
(d) The band's cells, always on one of the 26 processes, and the cells the solver mesh adds to the base
mesh's finest level, at each of the 759 builds.

**Movie.** The solver mesh of earth_recipe_movie over its 800 steps (3 to 1,103 Myr), 12 frames per second.
The window stands still in the planet's frame and is re-centred when the trench nears its edge. Base mesh
grey, the band black, the fault (where the mesh is split) thick black, the fault the next mesh is built on
red dashed, the oceanic-crust marker line yellow, the temperature faded behind (blue cold, red hot).

**movie-still-step460.png.** Step 460 (515.1 Myr), the furthest rollback (trench -20.3 deg), the movie's own
frame; the same step as trench-mesh.png (c).

## Movie

Shipped: `earth_recipe_movie_meshfixedT_0-799_web.mp4`, the same streams as
`/home/louis/+Claude/kaiju/movies/out/earth_recipe_movie/web/earth_recipe_movie_meshfixedT_0-799_web.mp4`
(8,026,300 bytes), remuxed with its index (moov) at the front for web playback
(`ffmpeg -i in.mp4 -c copy -movflags +faststart out.mp4`, `/home/louis/+Claude/kaiju/launch/uwtn/faststart.py`). Not re-encoded. Stream, from the container's ffmpeg 7.0.2 (imageio_ffmpeg, `ffmpeg -i`):
H.264 High, yuv420p (progressive), 1920 x 1080, SAR 1:1, 12 fps, 66.67 s (800 frames), 963 kb/s. The x264
settings embedded in the file give crf=28.0 (the full-quality version, crf=18.0, H.264 High yuv420p
1920 x 1080 12 fps, is `movies/out/earth_recipe_movie/earth_recipe_movie_meshfixedT_0-799.mp4`,
23,565,546 bytes). Made on 17 Nov by `launch/movies/meshfixed_T_frames.py` (frames) and
`launch/movies/meshfixed_T_encode.sh` (libx264, yuv420p, CRF 18, then the web copy at the first CRF from 28
that came in under 15 MB). The Kaiju copies keep the index at the end; the shipped file has it at the front.

The still `movie-still-step460.png` is a byte-identical copy of
`movies/out/earth_recipe_movie/meshfixedT/frame_00460.png`, one of the frames the movie was encoded from.

The other existing movies of this run (`/home/louis/+Claude/kaiju/movies/out/earth_recipe_movie/`), MB:

- whole run (steps 0-799): `earth_recipe_movie_meshfixedT_0-799.mp4` 23.6 (17 Nov, CRF 18),
  `earth_recipe_movie_meshfixed_0-799.mp4` 36.8, `earth_recipe_movie_nice_0-799.mp4` 25.6,
  `earth_recipe_movie_nicefixed_0-799.mp4` 24.4 (13 Nov)
- web copies (`web/`): `earth_recipe_movie_meshfixedT_0-799_web.mp4` 8.0 (shipped here),
  `earth_recipe_movie_meshfixed_2to1_0-799_web.mp4` 12.6, `earth_recipe_movie_nice_0-799_web.mp4` 13.4,
  `earth_recipe_movie_nicefixed_0-799_web.mp4` 13.1
- partial renders made while the run was going (12-13 Nov): `earth_recipe_movie_mesh_0-{29,59,79,110,113,117,174}.mp4`
  3.1, 5.9, 7.7, 10.5, 10.7, 11.1, 16.2; `earth_recipe_movie_meshfixed_0-{79,110,113,117,174,449}.mp4` 4.0, 5.4,
  5.5, 5.7, 8.9, 21.5; `earth_recipe_movie_meshfixed_square_0-174.mp4` 7.7;
  `earth_recipe_movie_nice_0-{29,59,79,110,113,117,174,449}.mp4` 1.3, 2.4, 3.1, 4.1, 3.6, 3.7, 5.4, 13.9;
  `earth_recipe_movie_nicefixed_0-{117,174,449}.mp4` 3.5, 5.0, 13.1

## Is there a fault-free twin of earth_recipe_movie?

No. No run under `/home/louis/+Claude/kaiju/runs` has earth_recipe_movie's model without a fault. Searched:
every run directory's `run_info.json` parameters compared with earth_recipe_movie's (the fault switches
uw_max_faults and uw_fault_law, and the model parameters), and the run READMEs for "no fault", "nofault",
"fault-free", "unfaulted", "without a fault". The nearest is `earthW_nofault_weak` (job 4117, 2026-11-06,
uw_max_faults 0, uw_fault_law none), which is not a twin: its crust is the weak plate boundary
(uw_crust_weak 0.001; earth_recipe_movie's crust is passive, 0.999) and twice as thick (0.0078125 against
0.0039), it ran an older driver (ccfd98d) and library (f631ce42), packed two runs to a node, for 71 steps
(0-70, 137 Myr). The workbench runs without these switches (wb_*) use a different driver (slab_workbench.py), and the fault-free
runs in `~/campaigns/zg95/runs` (slab_control_*, scale_*) are older models (20 to 40 parameters differ).
Step 0 of earth_recipe_movie has no fault in its mesh, but it is a single cold first solve. No twin was
launched.

## How to regenerate

From this folder's `data/` alone (Python 3 with numpy, scipy, h5py and matplotlib; on Kaiju the uw3
container's python3). On Kaiju, as one plain command (a compute node):

    srun --ntasks=1 --cpus-per-task=4 --mem=16G --exclude=n1 --time=00:30:00 apptainer exec /home/louis/uw3/images/uw3-gadi-development-20261021.sif bash /home/louis/campaigns/zg95/figures_out/uwtn_2026_022/scripts/make_all.sh

Elsewhere: `bash scripts/make_all.sh`. It runs, with default paths relative to `scripts/`:

    python3 scripts/trench_mesh.py   # -> trench-mesh.png, trench_mesh.json   (-uw_steps 10,130,460,799, -uw_far 0.02,0.05,0.1)
    python3 scripts/trench_cost.py   # -> trench-cost.png, trench_cost.json
    python3 scripts/run_summary.py   # -> run_summary.json (the README's run numbers)

Checked 2026-11-17: a copy of `scripts/` and `data/` in another directory regenerated `trench-mesh.png`,
`trench-cost.png` and the three JSON files byte for byte (same container; another matplotlib may change the
PNG bytes, not the content). The shipped data files match the run's (`data/SHA256SUMS`, checked against the
run directory).

The trimmed records and the list of steps that kept their mesh come from the run directory (plain python3):

    python3 scripts/trim_records.py /home/louis/+Claude/kaiju/runs/earth_recipe_movie data

The movie and the still are copies (see "Movie"); their makers are in `/home/louis/+Claude/kaiju/launch/movies/`.

## Notes

- Not every step rebuilt the mesh: 759 of steps 1 to 799 did, 40 kept the step before's (see "Summary
  numbers"). trench-cost.png has no rebuild markers; its caption explains the low points in (b).
- The run was not resumed (see "The run"); the `_resume` file names come from the launch script.
- Cells per process are not recorded for the whole mesh, so they are not plotted; (d) shows only the band's
  cells, which the records give per rank (all on one rank at every build).
