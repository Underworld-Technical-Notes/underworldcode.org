# Figures for UWTN 2026-022, "Faults and patch-refinement of the mesh"

The scripts, records and write-ups behind the note's figures and tables, one
section each below.

The bisection-and-cut construction (`base.adapt` toward the fault, every
add-on level split) and its figures were removed from the note on
2026-11-17 at Louis's ruling; their scripts and records remain in the note
branch's history (0085faf) and in underworld3 `scripts/sessions/fault_mg/`.

## The trench figures and movie (`trench/`)

`trench-mesh.png`, `trench-cost.png`, the two movies and their stills, and
every number in the section "Following a
trench", come from one run on kaiju, earth_recipe_movie (job 4417, 12–13 Nov
2026, 800 steps on 26 processes, underworld3 80d3ebe9, driver
zg95_lid_regimes `annulus_faults.py` at d358b97, `uw_chain 0`). The kaiju
science session (K1) assembled the folder `figures_out/uwtn_2026_022/` on
2026-11-17 from the run's existing outputs; Louis rsynced it to wombat
(`~/+Simulations/zg95/kaiju_figures/uwtn_2026_022/`) the same day.
`trench/README.md` is K1's account of the run, the settings, every number and
how each was measured.

Copied here: the scripts, the three JSON summaries, and from `data/` the
trimmed per-step records, the four steps' `state_*.json`, `run_info.json`,
`ARGS.txt`, `no_rebuild_steps.txt` and `SHA256SUMS`. Not copied: the five h5
mesh files (72 MB), which only `trench_mesh.py` reads. They are on wombat at
the path above and on kaiju, and `data/SHA256SUMS` checks them (all OK on
wombat, 2026-11-17).

Changed from K1's folder on 2026-11-17: the two scripts' titles, legends and
axis labels use the note's terms (add-on, not solver mesh; no record field
names or run name), the suptitles are gone, and the PNGs are written to
`figures/`; `make_all.sh` takes the h5 folder as an argument. Regenerated on
wombat (matplotlib 3.10.8, numpy 2.4.6):

    bash trench/scripts/make_all.sh ~/+Simulations/zg95/kaiju_figures/uwtn_2026_022/data

`trench_cost.json` came out identical to K1's and `trench_mesh.json`
identical apart from the panels' new labels and two window coordinates that
differ in the last digit. The movie and the still are byte copies of K1's
(`earth_recipe_movie_meshfixedT_0-799_web.mp4` and `movie-still-step460.png`).
The movie's window is re-centred once, at step 256 (its header text changes
at frames 256 and 280 only, checked over all 800 frames).

`annulus-movie.mp4` and `annulus-movie-still.png` are byte copies of K1's
`earth_recipe_movie_nicefixed_0-799_web_v2.mp4` (sha256 250ec6cc…21b4df70)
and `movie-annulus-still-step460_v2.png` (8c16b1d3…2935e06), rsynced
2026-11-17. "nicefixed" holds the annulus still with the trench's starting
position at the top; its window on the right follows the trench. v2 was
re-rendered at Louis's request with exact unit conversions (step 460 reads
515.1 Myr, not v1's 516.1) and the legend "melange layer" for the drivers'
"crust". `trench/README-annulus-movie.md` is K1's description of every
element, the orientation rules and the stream.

## The 3-D placement (Limits of the construction)

Hyperion, 2026-10-25, library `e135429f` (branch
`feature/coarse-solve-nullspace`), `dev` environment, PETSc 3.25.3. The
script, `library_c_3d.py`, is in underworld3 `scripts/sessions/fault_mg/`
and is not copied here. Checked against the draft's claim that the 3-D sheet
placement on a two-level child is refused by the volume guard:

(c) "The 3-D sheet placement on a two-level child is refused by the volume
guard." **Stale.** `../library_c_3d.py C 2` places the sheet at
`clearance=0.9` and solves: 44382 tetrahedra, 7 velocity iterations, peak
slip 0.17967. No intermediate add-on level survives in the tail
(`split_levels` 0, three levels: two background and the finest), so at k = 2
the 3-D hierarchy still has no split coarse level.

## ladder-construction.png (`fig_ladder_construction.py`)

Redrawn on wombat, 2026-11-01, by the laptop integration session, for the
production tail Louis ruled that day (underworld3 #892): library underworld3
`development` at 25d62812 (it has #912, the LU patch, and #915,
`Mesh.multigrid_levels`), PETSc 3.25, serial. PNG sha256
db38a2af…4f37f6bd; script sha256 1764616a…4d49b08f. The figure uses the
production construction, `place_fault_ribbon_2d(host, [("Fault", trace)],
width=2S, margin_rings=1, mesher="ladder", split=...)`, and lives in this
repository only.

    cd figures/src && python fig_ladder_construction.py \
        -uw_skills <underworld3>/.claude/skills/uw-line-diagrams

Serial, about a minute; writes `../ladder-construction.{pdf,svg,png}` in the
`uw-line-diagrams` house style, 183 x 102 mm, no caption text on the figure.
The note uses the png.

- (a) The finest ladder at the left tip, unsplit: the spine (the fault's own
  sample points), the two rails S either side (band 2S wide, tinted), a rung
  joining rail, spine and rail at every spine point (one element each side),
  the margin rung one spacing beyond the tip (dashed spine), the tip vertex
  (open circle), the graded fill out to the base cells. Dimensions S (rung
  spacing), S (spine to rail) and h_b (a base cell edge).
- (b) After the split: the Plus (solid) and Minus (dashed) facets drawn apart,
  every interior spine vertex duplicated, the tip vertex single.
- (c) The multigrid hierarchy as `set_custom_fmg(base.multigrid_levels)`
  builds it: the split child (S on h_b), then the base's own levels h_b, 2h_b
  and 4h_b, welded, with no fault in the mesh (the fault drawn hidden). Same
  window in all four. On the child, the cells that are not cells of the
  base's finest level are tinted (`new_cells`: cells whose vertex triple is
  not a base cell's): the band and its graded fill, 1004 cells. Their nodes,
  with a layer of base cells around them, are the finest level's patch, which
  the smoother solves by LU (4772 velocity rows in the recipe's run).

Numbers: fault (0.30, 0.45) to (0.70, 0.55), the stack fixture's. Base levels
1/8, 1/16, 1/32, so h_b = 1/32. S = L/80 = 0.00515, band ratio h_b/S = 6.06.
Cells per level, coarsest first: 162, 648, 2592, then the child 3498 (the
script prints them); 83 spine points with the two margin points. The child
has 906 cells more than the base's finest level: 1004 band and fill cells
replace 98 base cells.

`count_cells.py` (sha256 8e9fd16d…6edc471563) counts each mesh two ways. It
still includes the chain's ladders from the 2026-10-29 drawing (4S on 1/16:
878; 2S on 1/32: 3006). Those are no longer in the figure. It ran unchanged on
25d62812. The counts depend on the last bit of the trace. Sampled as
A + kS (B - A)/L, the tail sweep's form, instead of the figure's A + kS t with
t = (B - A)/L (the two differ by at most 1.1e-16), the S mesh has 3496 cells
and its patch 4764 rows; `count_cells.py -uw_trace figure|sweep` prints both.
The note quotes the figure's meshes.

Both scripts try the placement at clearance 0.7 and fall back to 0.5 and 0.3
if it fails; which value each level took is not printed. The note's recipe
calls 0.7 only. The recipe ran as written on 25d62812 (2 velocity iterations
at the default tolerance, peak slip 0.1595055).

History: the 2026-10-29 drawing (4698938f, PNG bc8e02cd…942c7af7c, source
`~/+Simulations/uwtn_2026_022_ladder/`) drew (c) as the lean chain, S and 2S on
h_b and 4S on 2h_b over the welded 4h_b, before the tail was ruled.

## The Multigrid section's table (`tail_sweep/`)

The band-ratio sweep of the multigrid hierarchy under the child, run on wombat
2026-10-29/30 by the laptop integration session at the notes session's request.
Library: underworld3 `feature/fault-split-integration` at 799ef021 (source
identical to 4698938f, PR #890), PETSc 3.25.0. `tail_sweep/README.md` gives
the hierarchies, both problems, the run commands and what each record holds.
`summary.md` (sha256 b8705fab…c8c5b9bb) is written by `collect_records.py`
from `records/*.json`.
Copied from `~/+Simulations/uwtn_2026_022_tail_sweep/` on wombat, 2026-11-01,
without the logs, probes and timing runs. Script sha256:
`tail_sweep_linear.py` be5988bd…473031abd,
`tail_sweep_box.py` f1d2d824…a37bde5e8,
`collect_records.py` 18705197…1e9a641c.

The table's rows, by arm:

| row | arm | smoother on the child |
|---|---|---|
| SOR, then the patch by LU | H0 `faclu` (`-uw_fac_lu 1`) | composite SOR + ASM, LU blocks with the nonzero shift |
| SOR, then the patch by ILU(0) | H0 | the same, with PCASM's default ILU(0) blocks (underworld3 #892) |
| SOR | H0 `nofac` (`UW_CUSTOM_MG_DISABLE_FAC=1`) | whole-level SOR |

The sweep's H1 arm (split ladders on coarse levels) is in the records but not
in the note. The fixture column is problem A at np 1, `vel_its_last`, h_b/S 6.06, 12.1,
24.3. The yielding-lid column is problem B at np 4, the velocity iterations
per Newton increment in the Newton phase, h_b/S 7.9, 15.5, 24.8. The SOR row
has problem B at 15.5 only. "About a third" is `A_r80_H0_faclu_np1.json`:
4764 patch rows of 14,048 finest velocity rows, one block per rank.

`-uw_fac_lu 1` keeps the block solver's keys in the options database, which
is what underworld3 #912 (development cc839425) makes the default. #912 reports
that its build reproduces these LU arms exactly.

Problem B needs the uw3-campaigns drivers (`zg95_lid_regimes/drivers/box_model.py`)
and the box run's checkpoint 2000 (`stagnant_tau1x1.00_fault_x2.0_dip45`), which
are not shipped; their paths are parameters of `tail_sweep_box.py`.

## The cut-in-band evaluation (`cut_in_band_595/`)

The scripts and cached runs of underworld3 #595 (2026-08-17), copied from
wombat on 2026-11-04. They show why the ladder's split uses the band's own
spine vertices. A default band cut along its centre line snapped a rail onto
the cut: min angle 13.0°, band cells 104 → 144. A band three nodes across, cut
at its spine, kept 28.8° and 132 cells. `cut_in_band_595/README.md` has the
provenance, and `audit_cached.py` repeats the numbers from the caches with
numpy alone.
