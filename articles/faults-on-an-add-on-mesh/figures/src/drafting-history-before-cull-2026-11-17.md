# Historical drafting records — 17 November 2026

These records were moved out of the article during the editorial cull. They contain superseded approaches and wording, and are provenance rather than current drafting instructions. The current scope is the patch solver, FMG efficiency and the moving-fault demonstration. Warm starts, restart details and split-coarse-level alternatives are outside that scope.

LOUIS'S RULINGS 2026-11-17 (applied unless marked):
- Split coarse levels are not to be mentioned: "That does keep recurring as a
  theme, and I keep trying to make sure it is shut down." The chain row, the
  chain paragraph and the welded-vs-chain comparison are gone from the
  multigrid section; the annulus paragraph keeps the welded numbers (441 /
  448 s, 2,489 F-cycles, 183 s at pressure rtol 1e-2; budget page
  LvNXEPD4QNkKtr2V7jDYH2, chain-0 arm).
- The bisection route: "I don't even want to mention this approach." Its
  paragraph, figure and files are gone (history at 0085faf).
- The opening reworded to the fault as a discontinuity (his 2 Nov words).
- Where the patch is solved is not mentioned ("so marginal in 2D"); the
  sentences on one block per process / one process are gone, and the
  seams="conform" paragraph with them. His design intent (a distributed
  patch in general) was relayed to the dev hub: underworld3 #1227.
- The trench section is to be REWRITTEN from earth_recipe_movie (kaiju job
  4417, 12-13 Nov, uw_chain 0, rebuilt every step, np 26, 800 steps). The
  25-26 Oct slab runs used uw_chain 2 on every build (K1, from the logs);
  their table, fault/no-fault comparison, threshold paragraph and figures go.
  K1 is building figures_out/uwtn_2026_022/ (trench-mesh, trench-cost, the
  movie earth_recipe_movie_meshfixedT_0-799_web.mp4 with a still, README,
  scripts, data) for Louis's rsync. DONE 2026-11-17 from the rsync; the
  whole-annulus movie (Louis: "the annulus movie will also be in the note",
  trench at the top) is still to come from K1.

DRAFT. Restructured 2026-10-26 to CONTRIBUTING.md, "How the notes read".
Rewritten 2026-10-29 for the ladder, the construction the production drivers
use (journal 2026-10-28-which-fault-mesh-construction-is-used-in-practice,
2026-10-29-which-tail-under-the-finest-ladder..., 2026-10-30-ladder-levels-nest-
along-the-spine...). Rewritten again 2026-11-01 for the production tail Louis
ruled that day (underworld3 #892, issuecomment-6550186134): the base's own levels,
welded, beneath the split child, with the child's patch solved by LU (#912,
development cc839425). The construction, the recipe, the moving-fault loop, the
Multigrid section and figure panel (c) describe it.

Open items for this rewrite:
- The Multigrid table is the tail sweep (figures/src/tail_sweep/, shipped 2026-11-01;
  summary.md b8705fab): fixture = problem A, np 1, vel (last); yielding lid =
  problem B, np 4, velocity iterations per Newton increment in the Newton phase.
  Rows: LU = H0 faclu (799ef021 with -uw_fac_lu 1; #912 says its build reproduces
  these exactly), ILU = H0, SOR = H0 nofac (box at 15.5 only), chain = H1. Patch
  "about a third": A_r80_H0_faclu_np1, 4764 of 14048 velocity rows.
- Kaiju's np 16 annulus check (science hub, 2026-11-01; page
  claude.ai/artifact/LiYdWdF3J5pnVPtTU7aDfy; posted on #892
  issuecomment-6550915680): development 25d62812, TAf checkpoint 40, 4 steps,
  chain 0 against chain 2. Velocity its per Newton increment 5.9 vs 7.7 (last
  application only), Stokes 448 vs 467 s/step, vrms to 2e-6, same Newton
  counts. Its "same 465-row patch" was misattributed (see the next item;
  corrected on #892, issuecomment-6552218825). Runs on kaiju ~/campaigns/zg95/runs/
  scale_chain_E_25d62812_TAf_ck40_chain{0,2}. The drivers' default is now 0
  (uw3-campaigns b440b88, with the build move to development; acceptance kaiju
  job 3154, TAf 40, np 16: vrms 1358.9188, slip 5877.77, Newton 6, equal to
  the chain-0 reference). The campaign branch is merged to uw3-campaigns main
  (a7792cd, 2026-11-03); cite main. The drivers' decisions ledger, citable for
  pressure rtol, chain, inset, seams, wall normal and locator:
  zg95_lid_regimes/DECISIONS.md on main. The sweep's own wall times are
  not controlled and are not quoted.
- Kaiju's time budget and warm/cold runs (science hub, 2026-11-01; page
  claude.ai/artifact/LvNXEPD4QNkKtr2V7jDYH2; jobs 2480–2488, runs
  ~/campaigns/zg95/runs/scale_budget_{stage,cold,baseV,presrtol1e-2}_chain{0,2}):
  steps 41–43, solve 441 (chain 0) vs 410 s (chain 2), F-cycles 2489 vs 2527 a
  step, FAC patch 21–28 s a step on rank 4 alone (max/min 165–178) vs under 1 s
  on chain 2; cold, warm and rebuild starts give the same Picard/Newton counts
  and answer in both arms. Reconciled (budget page v3): both arms on the rebuilt
  mesh f8; the applied multigrid has a 3584-row finest patch on rank 4 on chain
  0 and no patch on chain 2 (the 465/503-row patch is a second multigrid under
  the solver's own prefix, applied 50 times in 3 steps); 8.65 vs 8.74 F-cycles
  per velocity solve over all solves. Band ratio (chain page v4): on f8
  h_b = 0.5/2^5 = 0.0156, S = 0.004, h_b/S = 3.9, below the table's 6.06 and
  7.9. Applied hierarchies, cells coarsest first: chain 0 124 / 496 / 1984 /
  7936 / 31744 / 126976 (welded base) / 127705 (S child, patch); chain 2
  124 / 496 / 1984 / 7936 (welded base) / 31914 (4S on base level 4) / 127277
  (2S on base level 5) / 127705 (S child, no patch).
- Pressure tolerance (Louis approved -uw_pres_rtol 1e-2 as the campaign
  default, 2026-11-01, via the science hub): the annulus pair ran at the old
  1e-4 (budget page: not set, as in the TAf launch), and the paragraph says
  so, with the 1e-2 pair (183 / 174 s, vrms to 6 figures, slip within 0.05).
  Kaiju's logs and launch lines (science hub, 2026-11-01): the trench runs
  (runs/slab_fault_B1_*, drivers zg95-fault-drivers d0dca11 and
  zg95-fault-0fb51f9 for rungs8, library 99259d35) and the restart runs
  (dev-restart-runs, library 547ebb7f) all ran the library defaults, uw_tol
  1e-3, pressure 1e-4, inner velocity 3.3e-5; the text says so for both.
  Kaiju's build counts (n_built 29 / 50 / 30) include the initial build and the
  restart segments' builds; the table's rebuilds are the rebuild steps in
  solver_summary.csv (rebuild_same_set + rebuild_changed_set: 27, 47, 35; the
  rungs8 run's 29 is its 30 builds less the initial one).
- Why the patch is on one process (science hub correction, chain page v5;
  checked in the code 2026-11-01): the drivers place with seams="gather", the
  default. On development (25d62812) place_fault_ribbon_2d first calls
  addon_partition.partition_addon (band region on one rank, load diffused to
  within 10 %), then gathers nothing; the trench runs' library 99259d35 has no
  addon_partition, so the add-on kept the base partition and the placement
  gathered. seams="conform" (#670) needs mesher="network" in
  place_fault_ribbon_2d and has never run in these models. The network mesher
  cannot place a wall-reaching fault (science hub serial repro on kaiju,
  2026-11-01, HUB.md 29cd738: "the ribbon's cavity reached the domain wall"),
  so conform is unusable for every crust-law fault, and the ladder raises for
  seams other than gather. The text now says so.
- The trench runs used the chain (uw_chain 2); the text says so. Louis to decide
  whether to rerun them with the welded tail.
- Recipe: runs as written on development 25d62812 (integration session,
  2026-11-01, serial; logs in its scratchpad run_022/). Cells 162, 648, 2592,
  child 3498. Default tolerance: 2 velocity iterations, peak slip 0.1595055; at
  1e-6: 2 then 3, 0.1595099. Live smoothers: redundant coarse solve, gmres+sor on
  1/16 and 1/32, gmres + composite [sor, asm] on the child, 1 block of 4772 rows,
  lu.
- Figure: ladder-construction.png redrawn 2026-11-01 on development 25d62812, (c)
  the welded hierarchy; band and fill 1004 cells of the child's 3498.
- The bisection-route comparison (iterations.png and its paragraph) is kept after
  the chain; Louis to decide keep or cut. Its runs (2026-10-13, rotated path)
  smoothed without an exact patch solve.
- Before finalising: ask Louis again about the unused moving-fault material.
- stack.png is no longer referenced (the bisection-and-cut stack).
- Louis's decision, 2026-11-02 (DEV-HUB.md e6832e0, "DECISION: the add-on is
  the line", his words quoted there): the add-on (welded base, one split level,
  the FAC patch) is the line to invest in; split coarse levels (the chain) are
  not developed further and stay as the measured alternative. (1b) "the fault
  would carry its own resolution (it comes triangulated / as a divided line) and
  this is how we create the ladder. No S parameter defines the along-strike
  resolution." This supersedes the 2026-11-01 "S = h_b or h_b/2" form, which
  was the hub's; so no scope line on a production S. The ladder step now says
  the fault comes as a divided line whose points are the spine; S is the spacing
  of those points. NOT Louis's: corridor refinement (the hub's inference; he
  rejected it, "Let's try to avoid opening up too many new directions"). His
  words on the ladder (DEV-HUB.md, Correction 2026-11-02): "we probably don't
  need a lot of refinement - it's a discontinuity so we need to represent it
  efficiently. The ladder is to allow us to compute stresses and slip-rates
  accurately." For Louis: the opening's "cells an order of magnitude or more
  smaller" (mine, 2026-10-26) and the description's "cells much smaller" say
  the opposite; a rewording is proposed to him, not applied.
- Band ratios: both annulus models are 3.9 (the trench runs are -uw_refinement
  5, uw_cell 0.5, uw_spacing 0.004, the same base as the budget runs; the
  "h_b 0.031, about 8" in the band-ratio paragraph was refinement 4 and is
  corrected). Row 3's 48 and 97 are the note's fixture with more rungs and are
  not in the note. Row 7 (kaiju, 18 arms) now measures how the solver behaves
  as the fault's division changes.
- Recipe v2 (science hub, 2026-11-03; uw3-campaigns main a7792cd; DECISIONS.md
  per knob): development 25d62812, uw_chain 0, pressure rtol 1e-2, envelope
  locator, split inset 1 rung, uw_spacing 0 = one base cell (0.0156 at
  refinement 5), analytic wall normal. Acceptance kaiju job 3830 (TAf 40, np 16,
  one step): vrms 1318.24, slip 5724, Newton 5, 161 s a step (Stokes 138.6),
  FAC patch 1168 rows on one rank. This note's runs are all the old recipe:
  pressure rtol 1e-4, S 0.004, inset 3 rungs, parabola fit; the text states
  each (tolerances in the multigrid and trench sections, S in the band-ratio
  paragraph, the parabola in "Moving the fault", the inset in Limits).
  The ledger's uw_spacing row (main cf91755) quotes Louis: "Looked to me like 1
  base cell is efficient in terms of solver iteration which I thought quite
  positive", and on the inset "I think this is OK"; it marks "S = h_b or h_b/2"
  as the dev hub's reading, and carries 1b (no S parameter) as open against
  the knob. Answered 2026-11-03: see the next-but-one item.
- Spacing arms (dev hub, page claude.ai/artifact/7cbuaxBnoZrfjdPioMHroT; runs
  ~/campaigns/zg95/runs/scale_rung_E_{TAf_ck20,TBf_ck70}_chain0_S*_resampled,
  driver 81db298, chain 0, np 16, 10 steps, pressure rtol 1e-4, inset one base
  cell): TBf 70 (one node, n3) at S 0.004 / h_b/2 / h_b: Stokes 388 / 346 / 335
  s a step; FAC patch 3468 / 1870 / 1070 owned rows, its solve 15-31 / 8-12 /
  4-7 s a step; node pairs 109 / 51 / 25; vrms 1385 / 1381 / 1388; slip_max
  7265 / 7081 / 6967; trench the same. TAf 20 (early slab): slip_max -10 % and
  -18 %, mostly in the top 0.02, where the cut starts one base cell down.
  Velocity its per increment unchanged (ledger). Draft sentence for the
  annulus paragraph, for Louis (not applied): "With the fault divided at the
  base's cell size instead, the patch had about 1,000 rows and its solve took 4
  to 7 s a step rather than 15 to 31 s, and the step was 14 per cent cheaper,
  with the same number of velocity iterations. The peak slip was 4 per cent
  lower, most of the difference in the top base cell, where the split then
  stops." Recipe v2 stands under the equant ruling (next item: rungs at one
  base cell, W = 2 cells), so the sentence compares the note's S = 0.004 with
  the production ladder; still for Louis, not applied.
- Louis's clarification of 1b, 2026-11-03 (relayed by the science hub; in the
  drivers' ledger as a principle row, uw3-campaigns main db758b3 / febbb87, and
  HUB.md 7efb5ef), verbatim: "In terms of resolution - the along-fault
  resolution is set by the discretisation of the fault, the fault width is set
  by the local mesh size (which may not be uniform everywhere that the fault is
  embedded, but an average of some sort seems sensible here). What is going
  wrong in our model is that we are also defining the fault and its
  discretisation as a knob we can control. Generally this is not true - the
  ladder is built from the fault points and we can see if that is sufficient or
  not, but we generally can't just change it." Consequences:
  - Drivers, ruled the same day (ledger main 28021dd / 017b84d, HUB.md
    1575048), Louis on kaiju's division design (page UANqhA82AfRoh7fjgrPwYG):
    "This is a lot of design for what is, actually, a simple driver to test a
    concept. If we implement this, then we should consider it part of a
    plate-boundaries module. I'd say - make the ladder equant if given the
    choice. The half-width is one cell (I think) and so the discretisation
    along the length would be similar." So the ladder is equant: half-width
    one cell, rungs at about one cell, band two cells wide: recipe v2 as
    accepted (uw_spacing 0 = one base cell, W = 2S). The earlier reading "W =
    the local cell size, one cell wide" (kaiju's and the hubs', carried into
    journal 05f9ef5 by this session) is superseded. The division design (f393fd7)
    is shelved as input for a library plate-boundaries module (dev hub). The
    first v2 baselines (TAf-v2, Earth run 2) are launched on kaiju.
  - The library already takes the fault's points verbatim as the spine
    (place_fault_ribbon_2d's docstring, development af6f19b3: "its points,
    sampled by the user at fault scale, become the band's spine vertices
    verbatim") and the width separately: the rails are at +-width/2
    (_ladder_curved_assembly_2d). The docstring suggests "about 2 elements
    across width".
  - This note: "the spacing along the fault is a parameter" (Conforming
    section; mine, 2026-10-26) is changed to "that of the fault's own points,
    which can be finer than the cells". Step 2's "rails a distance S either
    side ... two rows of S x S squares" is what the recipe does, because it
    passes width 2S; every measurement in the note ran at W = 2S. Keep the
    runs at W = 2S and say so (the science hub's relay of Louis's answer,
    2026-11-03; HUB.md 1575048 has the equant ruling, not this sentence in
    his words): the recipe paragraph now says the width argument is 2S, so
    the ladder is equant. The note's ladders are finer than the cells (band
    ratios 3.9 to 24); production's is at one cell. The table's band-ratio
    sweep reads as faults given at different divisions: the solver has to
    cope with whatever division the fault comes with, and the exact patch
    keeps the count flat (proposed sentence, not applied).
  - Journal: follow-up decision entry committed by the docs hub
    (underworld3-journal 05f9ef5, entries/2026-11-03-the-faults-division-and-
    the-bands-width-are-not-knobs-...). Its "where enforced" names this note's
    changed sentence (done, unsaved) and the width question (with Louis). Its
    "one local cell wide" is superseded by the equant ruling: the correcting
    entry is journal 90e1423 (05f9ef5's entry marked superseded by it; its
    quotation stays the record of the principle), and the guides give the
    equant form from #862 d02e2d6f.
  - Why the ladder (Louis, on kaiju's design page, ledger main 4338da5): "we
    looked at whether to cut the band in the centre using the original nodes
    of the fault and found that this was best. Otherwise the cell cuts are
    another calculation to make rather than just having the fault use its own
    nodes. One cell either side of that gives a good mesh and there is no
    benefit to having more cells in the fault itself." The evaluation is
    underworld3 #595 (2026-08-17; scripts and write-up on wombat only,
    ~/+Simulations/ribbon_network_2d/README.md, "The cut-in-band
    configuration"): a default band cut along its centre-line snapped a rail
    onto the cut (min angle 32.2 -> 13.0 deg, zone 104 -> 144 cells); a band
    three nodes across (one cell either side), cut at its own spine vertices,
    stayed 28.8 deg and 132 cells, slip 0.4315 against the w/4 band-only
    reference 0.428-0.433. "No benefit to more cells" was not measured as such.
    Not in any note or journal entry; told to the science hub for the ledger.
    The note could cite #595 where step 2 or the Conforming section says the
    split consumes the fault's own points (for Louis). The ledger cites it
    (main 837f723). Louis agreed (relayed by the science hub, 2026-11-04)
    that the evaluation comes off wombat beside the note that cites #595;
    placed here, in figures/src/cut_in_band_595/: the two scripts and the six
    they import, unchanged, their four caches, the original write-up, and
    audit_cached.py, which repeats #595's numbers from the caches with numpy
    alone (13.0 deg, 104 -> 144; 28.8 deg, 132 -> 132; slip 0.4286 / 0.4315;
    free slit 0.4290). The solves were not rerun on development. Unsaved, with
    the note. The ledger names the folder (main f6d07ee); when 022 is saved,
    send the commit to the science hub (ledger) and the docs hub (DOCS-HUB.md).
- Journal decision entry for 2026-11-02: drafted by this session, committed by
  the docs hub (underworld3-journal a4e5852, entries/2026-11-02-the-add-on-is-
  the-line-for-split-faults-...). Its "where enforced" names this note's ladder
  step (done, unsaved) and the chain described as the alternative (done). The
  guides on #862 now carry ruling 4 (the fault carries its own resolution).
- The split stopping short of the wall (Louis, 2026-11-02, via the dev hub): an
  implementation detail, because the surface degrees of freedom cannot be
  rotated, with damage carrying the rest; not a physical depth. The Limits
  paragraph now says so. The drivers' trace_inset() is 3 rungs (0.012 at S
  0.004, under one base cell of 0.0156); Louis says one element. At S = h_b, 3
  rungs would be three base cells, so the inset should be set in cells.
- The patch's LU and the pin (docs hub, 2026-11-08; checked on GitHub and in
  custom_mg.py on development). Two sentences hold for 25d62812, this note's
  pin, and not for development since PR #934 (for issue #925, which stays open;
  merged 2026-11-04 UTC, 60dbf0e4):
  - the Multigrid section's "as one block on each process";
  - the annulus paragraph's "The patch is solved on the processes that hold
    the fault. The placement puts the whole band on one process ... so that
    process solved the patch ... alone", and its "with several faults in one
    partition".
  On development, `_gathered_patch_blocks` gathers every rank's rows on rank 0
  and sends each block whole to the rank that owns most of its rows. With no
  zone keyed the structural patch is one block, so it is one LU on one process
  at any rank count and under any placement, and the rows of several faults
  are in that one block wherever they lie. `fac_block_rows` cuts only
  `fac_zone` masks, in serial and in parallel. #934 found row 3 (#918's case,
  already one block on one rank) unchanged to 10 digits at np 1-16; the annulus
  runs were not repeated. #895 now carries the one-rank LU (a MUMPS probe,
  campaigns ac4ed5a). Keeping the pin changes nothing. A re-pin needs the
  recipe and figure (c) rerun, and the wording: "as one block, on the process
  that holds most of its rows"; "The patch is solved by the process that holds
  most of its rows, and the placement puts the whole band on one process ...";
  "or with several faults". For Louis, not applied. The fault-multigrid guide
  on #862 (86b17b0a) has the new wording.
- Before publication, from main since 2026-11-16 (#71): add this note's slug
  under 2026 in acknowledgements-nci.yml, in the note's own pull request; it
  is a 2026 note with computation behind it. (A `## History` section, #51,
  comes only with a later version.) A movie of the fault moving through the mesh
  would take #65's form (MP4 with a `:placeholder:` still; the docs hub
  expects one from kaiju's runner); none has arrived.

Drafted 2026-11-17 from kaiju's figures_out/uwtn_2026_022/ README
(K1's text, relayed). Checked 2026-11-17 after Louis's rsync: every number
against figures/src/trench/README.md, run_summary.json, trench_mesh.json,
trench_cost.json and the records (records_trimmed.json); the captions and alt
text against the PNGs and the movie's frames. The starting residuals, 0.9 and
0.03, are K1's reading of the run's log, not in the shipped records. The panel
(c) paragraph is from records_trimmed.json (slip_max x 1.08819e-3 cm/yr) and
no_rebuild_steps.txt. Orientation (Louis, 2026-11-17): the insets and the
whole-annulus movie put the trench's starting position at the top. The
whole-annulus movie is K1's nicefixed v2 (re-rendered 2026-11-17 with exact
unit conversions and the legend "melange layer", at Louis's request);
caption and alt text from figures/src/trench/README-annulus-movie.md and the
frames at steps 0, 460 and 799.
K1 checked against driver d358b97, run_info and the log (2026-11-17): the
warm start (faulted.warm_start of the previous child's V, P, split copies
nudged 0.1 S to their side, lines 1924-1938, 3218-3220), the model (free
slip both walls; T = 1 base, T = 0 top with a warm ridge patch; internal
heating H 1.4175; buoyant continental layer uw_over_dT -0.5; Ra 2.386e7),
the fit (melange particles, 10 % base pass, lambda = L^4/0.005, L 0.02) and
the surface weak zone (eta_w 0.001 on viscosity and yield, 1726-1772).
DERIVED, not measured: the 2.3 km reach of the transfer as the reason for
the 0.9 starting residual (trench 2,228 km in 460 steps = 4.8 km a step);
the viscosity floor limiting the weak zone.

Panel (d) no longer says where the band's cells are solved (K1's label
"all on one rank of 26" removed, Louis's ruling); it shows the band's size
only. Louis may still drop the panel.

FIGURES (scripts, records and README in figures/src/)

ladder-construction.png  (a) finest ladder, (b) split, (c) the hierarchy: the
                   child with band and fill tinted (1004 cells), then the
                   base's h_b, 2h_b, 4h_b, welded. Wombat, development
                   25d62812, fig_ladder_construction.py, 2026-11-01.
                   Cells: base 162 / 648 / 2592, child 3498.
trench-mesh.png    earth_recipe_movie (kaiju job 4417, 12-13 Nov, uw_chain 0,
trench-cost.png    rebuilt every step, np 26, 800 steps). K1's scripts, with
trench-movie.mp4   the note's terms in the titles, redrawn on wombat
trench-movie-still.png  2026-11-17; movie and still are K1's files. See
annulus-movie.mp4  figures/src/README.md, "The trench figures and movie".
annulus-movie-still.png  K1's nicefixed v2 movie and its step-460 frame.

Removed 2026-11-17 (the bisection route, Louis: "I don't even want to mention
this approach"): iterations.png, stack.png, moving-fault.png and their
scripts and timings; in the branch's history at 0085faf.

LADDER NUMBERS (the Multigrid section's table)
  figures/src/tail_sweep/ (README.md, summary.md b8705fab, records/*.json;
  tail_sweep_linear.py, tail_sweep_box.py, collect_records.py), from wombat
  ~/+Simulations/uwtn_2026_022_tail_sweep/, underworld3 799ef021
  (src = 4698938f), PETSc 3.25.0.
  fixture = problem A, np 1, vel_its_last at h_b/S 6.06, 12.1, 24.3:
    LU H0 faclu 3/3/3; ILU H0 8/12/16; SOR H0 nofac 12/17/24; chain H1 4/6/7.
  yielding lid = problem B, np 4, checkpoint 2000 of
    stagnant_tau1x1.00_fault_x2.0_dip45, one solve from rest, tol 1e-3, velocity
    its per Newton increment in the Newton phase at h_b/S 7.9, 15.5, 24.8:
    LU 7-7 x3 (0 caps); ILU 28-200, 73-200, 86-200 (1 cap each); SOR (nofac,
    15.5 only) 161-175; chain 28-40, 45-53, 67-76 (0 caps).
  patch: A_r80_H0_faclu_np1 asm_rows 4764 of 14048 finest velocity rows; one
    block per rank (asm_blocks = np).
  -uw_fac_lu 1 kept the block keys, which is what #912 (cc839425) now does by
  default; #912's body reports the fixed build reproduces these exactly.

SOURCES (underworld3, branch feature/parallel-addon-distribution unless noted)
  docs/developer/subsystems/fault-split-multigrid.md        (tables, rotated walls)
  docs/developer/design/FAULT_MULTIGRID_HIERARCHIES.md      (the four hierarchies)
  docs/developer/design/fault-parallel-placement-2026-09.md (the frame)
  docs/developer/design/parallel-addon-distribution-2026-10.md (load numbers)
  docs/developer/subsystems/conforming-surfaces-and-fault-zones.md (cut vs place)
  docs/developer/guides/adapt-on-top-faults.md               (API)
  uw3-campaigns zg95_lid_regimes/RESTART_AND_RECORDS.md      (restart table)
  uw3-campaigns 788f481 zg95_lid_regimes/analysis/restart_table.py (the table's
  script; runs ~/campaigns/dev-restart-runs/{old,new,i3}_{a,b*} on kaiju, np 16,
  overlay-warmonly / uw3 547ebb7f; the i3 pair's run_info.json driver_commit
  values are stale (a worktree HEAD), cite the runs' paths, not those hashes;
  the trimmed records ship in figures/src/restart_table/, from kaiju
  ~/campaigns/zg95/figures_out/restart_table/ by Louis's rsync, 2026-10-26)
  underworld3 bugfix/rotated-solve-diagnostics 210c7307, feature/box-faults-warm
  371d3bd (the convergence reference)
  kaiju slab runs: ~/+Simulations/zg95/kaiju_figures/slab_fault/*/solver_summary.csv
  (the four-run table; rebuild extra = (rebuild - ordinary s/step) x rebuilds,
  1174 s of 8471 in the 47-rebuild run, 519 s of 8324 in the 27-rebuild run)
