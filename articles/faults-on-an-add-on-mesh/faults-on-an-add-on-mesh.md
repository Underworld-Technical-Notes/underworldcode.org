---
title: Faults on an add-on mesh
description: >-
  A fault needs a resolution the rest of the model cannot afford and a geometry
  that changes as the model runs. This note describes building the fault into a
  short-lived mesh stacked on a static base: the base keeps the state and the
  coarse multigrid levels, the add-on is refined toward the fault, cut and split,
  solved, and rebuilt from the base whenever the fault moves.
date: 2026-10-25
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
license: CC-BY-4.0
keywords:
  - Underworld Code
  - Tricks of the Trade
  - development
bibliography:
  - references.bib
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/faults-on-an-add-on-mesh/
    template: ../../templates/pdf
    output: faults-on-an-add-on-mesh.pdf
    article_id: UWTN 2026-022
    article_version: 1.0.0
    software_version: underworld3 feature/coarse-solve-nullspace @ e135429f
---
<!--
DRAFT, hub session 2026-10-25. The three figures were made on hyperion at
underworld3 e135429f (feature/coarse-solve-nullspace) and copied here with their
scripts and records into figures/src/, whose README carries every number. The
iteration table and the moving-fault timings are taken from that README; the
restart table is from the kaiju annulus runs, whose trimmed records ship in
figures/src/restart_table/ and which figures/src/restart_table.py reads.
-->

A fault in a geodynamic model asks two things of the mesh that pull against each
other. It wants cells a hundred times smaller than the rest of the domain needs,
along a trace that wanders where the geology puts it, and it wants to move: a
trench retreats, a fault rotates as the plate it bounds turns, a new fault forms
where the stress says so. A mesh that conforms to the fault answers the first;
the second then means remeshing, and remeshing the whole domain every few steps
costs the state carried on it, the partition it was distributed with, and the
multigrid hierarchy the solver was built on.

The construction described here keeps the whole-domain mesh out of it. A
**base** mesh is built once, distributed once, and never cut. It holds the bulk
fields, the particle swarms, the history, and the coarse levels of the multigrid
tail. The fault lives on an **add-on**: a child mesh refined from the base
toward the fault, made to conform to it, and split along it so the two sides can
slip. The child carries no state of its own. When the fault moves the child is
thrown away and rebuilt from the base, and the fields it needs come across from
the base again.

I have written elsewhere about what a fault is asked to represent and the
choices between a weak band, a directed weak band and a slipping cut
([Faults: to mesh or not to mesh?](https://www.underworldcode.org/putting-a-fault-in-a-mesh/)),
about moving a mesh rather than remaking it
([UWTN 2026-011](https://www.underworldcode.org/moving-the-mesh-without-remaking-it/)),
and about building a multigrid preconditioner from a real hierarchy of meshes
([UWTN 2026-014](https://www.underworldcode.org/setting-up-full-multigrid/)).
This note is about the piece in the middle: how the fault's resolution, its cut
and its multigrid levels are stacked on a mesh that does not change.

## The static base and the ephemeral add-on

The base mesh is the persistent object of the model. It is built with a
refinement hierarchy, so its coarse levels exist from the start, and it is
partitioned once. Every quantity with a history is a variable on the base or a
particle in a swarm attached to it: temperature, plastic strain, the material
markers, the stress history of a viscoelastic material. The fault's own history,
its slip and its damage, lives on the fault object, not on either mesh.

The add-on is a child of the base and is rebuilt whenever its geometry is
stale. It is made in three moves, each of which leaves the base untouched:

1. **Refine toward the fault.** The base's finest level is bisected locally,
   driven by the fault's exact signed distance, until the cells near the trace
   are the size the fault needs. Each round of bisection is a new level of the
   hierarchy, so the child arrives with its own multigrid levels already in
   place beneath it, continuing the base's.
2. **Make the mesh conform to the trace.** The fault's points become mesh
   vertices and its segments become element edges, by placing the fault's own
   points into the mesh and refilling the cavity around them. No cell straddles
   the fault afterwards.
3. **Split.** Each interior vertex of the chain is duplicated and the cells on
   one side are rewired to the copy, so that velocity may jump across the fault.
   The coupling between a vertex and its copy is the fault's constitutive law.

Two transfers connect the two meshes, and they are the only coupling. Bulk
fields go from the base to the child before a solve and back after it, by
interpolation. The multigrid tail goes from the base's coarse levels to the
child's finest, through the add-on levels. Everything else about the child is
local to one solve.

```{figure} figures/stack.png
:alt: Five panels of mesh edges near a straight fault drawn in red, coarsest at the left and finest at the right, titled with their cell counts. The two left panels are the base's own levels, 242 and 968 cells at sizes 0.1 and 0.05, welded, with the fault trace running through cells without following their edges. The three right panels are the add-on levels, 1274, 1644 and 2006 cells at sizes 0.025, 0.0125 and 0.00625 along the trace, grading back to the base size within a few cells; in each of them the trace runs along element edges and is drawn as two lines, red and blue, opened by a small offset to show the split, meeting at a single vertex at each tip.

The stack. The two left levels are the base's own, welded and never cut. The
three right levels are the add-on, refined toward the fault, conforming to it,
and split along it; the two copies of the trace are drawn apart so they can be
seen. The levels on the right are rebuilt when the fault moves; those on the left
never change.
```

## Refining toward the fault

The refinement is driven by a function of position. A metric sampled from a
mesh variable is only as sharp as the mesh it is sampled on, and a metric peaked
on a line one cell wide aliases into a patchy band. The fault object gives its
exact signed distance at any point, so the metric is evaluated at each new
level's cell centroids and resolves itself at the new resolution:

```python
import underworld3 as uw

base = uw.meshing.UnstructuredSimplexBox(cellSize=0.1, refinement=1, qdegree=3)

fault = uw.meshing.Surface("fault", base, fault_points, symbol="F")
fault.discretize()

metric = fault.refinement_metric_function(h_near=0.00625, h_far=0.1,
                                          width=0.05, profile="linear")
child = base.adapt(metric, max_levels=4)
```

The engine is newest-vertex bisection with a bounded closure, so each pass
halves the cells it marks and repairs the hanging nodes with a bounded number of
further bisections. The grading is set by the metric; `max_levels` caps the
depth. The result is deterministic and non-cumulative: a second call with the
same metric, from the same base, gives the same child, which is what lets the
child be discarded and remade.

The base's cell size near the fault should be about twice the first add-on
level's target. A base much coarser than that leaves the first level to do too
much, and its closure spreads; a base already as fine as the fault needs leaves
the add-on nothing to do and the whole domain paying for the fault.

## Making the mesh conform to the fault, then cutting it

The conforming step can be done two ways, and which one applies decides what
geometries are allowed. **Cutting** splits the edges the fault crosses and moves
the new vertices onto the trace: every crossing is a function of the coordinates
alone, nothing moves, and it runs on a distributed mesh without communication.
It refuses a fault that ends inside the mesh, because a triangle entered and not
left has no split that represents it, and it cannot resolve a fault finer than
the cells it crosses. **Placing** asserts the fault's own points as mesh
vertices, deletes the mesh vertices in the way and retriangulates the cavity
with the fault embedded in it, which is standard mesh generation and works the
same way for a curve in two dimensions and a sheet in three. A tip is an
ordinary placed vertex, the spacing along the fault is a parameter, and two
faults closer than one cell are refused as a pair of zero-thickness surfaces but
accepted as one finite-width zone. Both leave a chain of labelled facets with
no straddling cell, and both leave the base untouched.

The split follows on the conforming mesh and is the construction of
@Zhong_1995, with the mesh conforming beforehand so that what remains is the
duplication alone. Each interior vertex of the chain is copied; the cells on the
Minus side are rewired to the copy; the two end vertices are not copied, so
slip goes to zero at the tips. The condition between a vertex and its copy is
written in the fault's frame, mean and jump, normal and tangential: no opening
is the equality of the two normal velocities, a frictionless fault leaves the
tangential jump free, and a friction law relates that jump to the traction the
pair carries. The slip rate is the tangential jump, read off the pair.

Nothing below the add-on's finest level is cut by this step. The base stays a
continuous mesh, and a field on it is continuous across the fault's position.
That is the right representation of the bulk state, which does not jump, and
the velocity's jump is reconstructed on the child at each solve.

## The multigrid levels carry the fault

The velocity solve on the child is preconditioned by geometric multigrid on the
stack: the base's levels at the bottom, the add-on levels above them, the split
finest at the top. How the fault is represented on the add-on levels decides
whether the solve stays mesh-independent as the fault is refined.

I measured four hierarchies on a box in simple shear with a straight fault,
incompressible Stokes at unit viscosity, base cell sizes 0.1 and 0.05, and the
add-on refined by factors of two toward the fault. The finest level is split in
every case. The alternatives were a welded Galerkin tail (the add-on levels
coarsened without the fault), the same tail with a transversely isotropic weak
band rediscretised on each level to stand in for the fault, split add-on levels
with a welded base, and split add-on levels over a base carrying a broad weak
zone.

**Splitting every add-on level, and leaving the base welded, is the one to
use.** The add-on levels are cut and split exactly as the finest is, so the
coarse spaces contain the discontinuity. A smeared weak band on a coarse level
is a continuous shear that the split fine operator rejects: the welded tail
with such a band converged more slowly than the welded tail alone at every
depth, 14, 22 and 30 iterations against 8, 13 and 18. The split levels over a
weak-zone base match the split levels at depth and add a rediscretised base
operator to assemble at every step and band parameters to choose, for no gain.

| add-on levels $k$ | near-fault $h$ | split add-on levels | welded add-on levels |
|---|---|---|---|
| 2 | 0.0125 | 5 | 8 |
| 3 | 0.00625 | 5 | 13 |
| 4 | 0.0031 | 4 | 18 |

The table gives velocity iterations per solve to a relative tolerance of $10^{-6}$
for a frictionless fault. The count stays flat or falls slightly with refinement
on the split levels and grows on the welded ones. A viscous fault at $k = 3$ took
5 iterations against 12. The peak slip agrees between the two tails to six figures: the
levels change the cost of the solve and nothing about its answer.

```{figure} figures/iterations.png
:alt: Two panels. Left, a line chart of velocity iterations per solve against the add-on depth k from 2 to 4 for four hierarchies: the welded tail rises 8, 13, 18; the welded tail with a transversely isotropic band rises faster, 14, 22, 30; the split add-on levels go 5, 5, 4; the split levels over a weak-zone background go 7, 4, 4. Right, a bar chart for a viscous fault at k = 3: 5 iterations for the split add-on levels and 12 for the welded tail.

Velocity iterations per solve against the depth of the add-on, for the four
hierarchies measured, frictionless fault on the left and viscous fault on the
right. The two split hierarchies are the ones whose count does not grow with
refinement.
```

Two constructions make the split levels usable. The **transfer between levels
has to know which side it is on**. For each fine node one fine cell containing
it is taken, and that cell's centroid is located in the coarse mesh; a centroid
is never on the fault, so the coarse cell found is on the node's own side, and a
node on the slit interpolates from its own side only. The coarse cell's
interpolant is evaluated at the node. Because each level's cut pulls its own
vertices onto the trace, the levels are conforming but not nested there, and a
fine node can fall slightly outside its located coarse cell; the evaluation
point is clamped into the cell, so every weight stays within the Lagrange basis.
Without the clamp, extrapolated weights of five appeared near a tip, and the
coarse operator built from them had a near-zero diagonal that made the smoother
return NaN.

Each split level also **carries its own pair frame**. The rotation into mean
and jump is built from the level's own pairing and facet normals, the opening
rows are removed on every level, and the transfer between two split levels is
written between their frames. A coarse unknown that no fine unknown reaches,
which happens for a few near the tips, is a null mode of the Galerkin coarse
operator; it is removed from the level, never repaired by injecting a value.
That rule turned out to apply to every geometric hierarchy with a custom
transfer, split or not: the nearest-node repair used before put a second unit
entry on a fine row that already carried one, which is two identical columns
and a singular coarse operator.

Under rotated free-slip walls, on an annulus or a spherical shell, the coarse
levels are rotated too. Each level takes the same per-node frame as the finest,
built on its own wall nodes, and its normal rows are removed. With Cartesian
coarse levels and only the finest's normal rows zeroed, a coarse wall node's
normal component was reached only through the fine tangential rows, weighted by
the sine of the angle between the two nodes' normals: a nodal block of $10^{-3}$
against 2.5 near an axis, and $10^{-20}$ on it. The block smoother reported a
zero pivot and the solve failed before its first iteration. A box with
axis-aligned walls never shows this, because its sines are exactly zero. The
measure-weighted frame and its reaction are described in
[UWTN 2026-016](https://www.underworldcode.org/boundary-conditions-on-non-planar-boundaries/).

## Moving the fault

A moving fault is the case the construction is for. The child is non-cumulative
and deterministic, so the step is: move the fault's points, build a fresh child
from the static base, carry the fields across, solve.

```python
for step in range(n_steps):
    fault_points = advance(fault_points, velocity, dt)
    fault = uw.meshing.Surface(f"fault{step}", base, fault_points, symbol="F")
    fault.discretize()

    child = base.adapt(fault.refinement_metric_function(h_near=0.00625,
                       h_far=0.1, width=0.05), max_levels=4)
    mesh = child.add_fault([("Flt", fault_points)])      # every add-on level split

    stokes = uw.systems.Stokes(mesh)
    stokes.add_fault_bc(0, "Flt")                        # frictionless, no opening
    ...                                                  # body force from base fields
    stokes.solve()
    # read the velocity back onto the base; advect the base's state
```

The transfer of a smooth field from base to child and back is bounded by the
representation error of the coarser mesh and does not accumulate: a field
carried through many rebuilds is no worse than one carried through one. A sharp
front loses more per transfer, and a quantity with a history is therefore kept
on the base and never round-tripped. The velocity read back onto the base is
continuous across the fault, as a base field must be, and the slip is kept on
the fault object.

The cost of a rebuild is small against the solve it enables. On the box above at
$k = 4$, with the fault moved along its own line to three positions and the
add-on rebuilt and re-split at each, a step at eight processes took 0.3 to 0.6 s
to refine, 0.75 to 0.9 s to conform and split every level, and 4.5 to 4.8 s to
build the solver and solve, in 7 velocity iterations; in serial the same steps
took 0.8 to 1.4 s, 1.1 to 1.2 s and 6.0 to 6.5 s, in 4 or 5 iterations. The
rebuild costs between a fifth and a half of the solve, and at this depth the
welded tail needs 18 iterations to the split levels' 4.

```{figure} figures/moving-fault.png
:alt: Three panels across the top show the mesh and the logarithm of the second invariant of the stress near a fault centred at x = 0.3, 0.5 and 0.7, titled 3102, 3034 and 3080 cells and 4, 4 and 5 velocity iterations; the refined band follows the fault and most base cells away from it are unchanged. Below, stacked bars give the wall time of each step at eight processes and at one: at eight, 0.3 to 0.6 s to refine, about 0.8 s to conform and split, and 4.5 to 4.8 s to solve; at one, 0.8 to 1.4 s, 1.1 to 1.2 s and 6.0 to 6.5 s.

A fault moved through three positions. The add-on follows it, and about nine in
ten of the base cells away from the band are the same in every panel. The bars
give the wall time of each step at eight processes and at one, split into
refining the add-on, conforming and splitting its levels, and the velocity solve,
which includes building the solver and its transfers.
```

## Warm starts and restarts

A rebuilt child is a new mesh, and the velocity and pressure of the previous
step are transferred onto it as the initial guess. For a nonlinear rheology this
matters more than the mesh: the yield-stress problem of a faulted lithosphere
takes a Picard sweep before Newton converges from rest, and a warm start skips
most of it. Two things have to be true for the warm start to work.

The convergence test and the switch from Picard to Newton have to measure
against the **rest-state residual**, not against the residual of the initial
guess. A warm start begins at a few per cent of the rest residual. Measured
against itself, a relative tolerance of $10^{-3}$ asks for a solution a thousand
times better than the one an uninterrupted run accepts, and the solve either
runs to the iteration cap or reports a failure that is not one. The reference is
$\max(\|F_0\|, \|F_\text{rest}\|)$, and the switch to Newton fires against it.

The initial guess has to be the **two-sided velocity**, not the base field. A
rebuild after a step that did not move the fault far starts at about three per
cent of the rest residual and converges in the same four Newton iterations an
uninterrupted step takes. A rebuild after the fault set has changed, a fault
formed or retired, starts at about sixty per cent of rest and is outside
Newton's basin: the residual is localised to the band where the geometry
changed, and the first iterations are Picard whether or not the guess is warm.
The base's velocity, evaluated on the child, is continuous across the fault and
carries no pressure; a solve started from it does better than one started from
rest, and worse than one started from the child's own previous solution.

The same two rules decide what a **checkpoint** has to hold. The base fields and
the fault state are what the model is; the child is rebuilt from them, exactly,
on any number of processes, because the placement is deterministic. A restart
that rebuilds the child and starts the solve from rest, or from the base
velocity, pays for it on the first step. A restart that also saves the child's
velocity and pressure, each degree of freedom at its coordinate with the split
copies tagged by side, and gives each degree of freedom of the rebuilt child the
saved value at its own coordinate, takes exactly the warm step the uninterrupted
run would have taken.

| first step after a restart, annulus with four faults, 16 processes | Newton iterations | Stokes wall (s) |
|---|---|---|
| child rebuilt, solve from rest | 36 | 783 |
| child rebuilt, base velocity as the guess | 17 | 387 |
| child rebuilt, saved child velocity and pressure as the guess | 4 | 103 |
| uninterrupted run, same step | 4 | 94 to 101 |

The table is from an annulus model of a yielding lid with slipping faults, the
split representation of
[UWTN 2026-017](https://www.underworldcode.org/putting-a-fault-in-a-mesh/),
base cell size 0.5 degrees with four halvings, 16 processes, restarted at a
step with four faults in place. With the child's
velocity saved, the first step after the restart reproduces the uninterrupted
run's velocity to $3 \times 10^{-15}$ in its root mean square; over the following
ten steps the two agree to $4 \times 10^{-4}$, within the solve's tolerance, and
the fault decisions are identical. The table is regenerated
from the runs' step records by `restart_table.py` in `figures/src/`, which also
prints each run's directory and provenance.

## A fault following a trench

The construction's working case is a fault that is not placed once but follows
the model. The example is an annulus with a subducting plate: a thin, weak
crustal layer rides on the slab, the plate yields where the stress demands it,
and a fault is to lie along the base of the crust where it bends into the
mantle, after @Sandiford_2019. The trench retreats as the slab founders, so
the fault's trace has to move with it.

The fault is found rather than prescribed. Every five steps the subducted crust
particles are gathered, the cluster nearest the trench is fitted by a parabola
along its lower envelope, and that curve, from just below the surface to a cap
depth, is the fault. When the fitted trace has moved by more than a set number
of cells the add-on is rebuilt from the static base at the new position, the
velocity and pressure of the previous step are carried onto it, and the solve
continues. The base mesh, the temperature, the plastic strain and the particles
never move between meshes; only the add-on does.

```{figure} figures/trench-mesh.png
:alt: Four panels of mesh edges in a window 0.30 wide and 0.22 deep on a subduction trench in an annulus, at steps 10, 100, 200 and 290 of one run, the trench at -0.9, -10.8, -24.1 and -28.9 degrees, each with the whole annulus inset showing the window. The base mesh is drawn in blue and the solver mesh's edges in black over it, with the fault trace in red dipping from the trench into the mantle; between panels the trace has moved along the surface and the band has moved with it, while the base edges away from the band coincide exactly.

The add-on mesh at steps 10, 100, 200 and 290 of the run with no weak crust, in
which the trench moves 29 degrees over 300 steps and the fault is rebuilt 47
times. The band follows the fitted trace, adding 430 to 570 cells to a base of
126,976; every base edge more than 0.1 from the trace is the same in all four
panels.
```

Four runs of 300 steps at sixteen processes measure what following the trench
costs. They are demonstrations of the mesh, not a subduction result: the slab is
compositional and its physics is a stand-in for the thermal one. Every step
converged in one nonlinear iteration, a Newton step on ordinary steps and a
Picard step after each rebuild, and no linear solve reached its iteration cap.

| run | rebuilds | ordinary step (s) | rebuild step (s) | velocity / pressure iterations | 300 steps (s) |
|---|---|---|---|---|---|
| weak crust, no fault | 0 | 26.4 | | 4 / 17 | 7802 |
| weak crust, fault at the crust base | 27 | 25.7 | 44.8 | 3 / 18 | 8324 |
| no weak crust, fault at the crust base | 47 | 23.8 | 48.6 | 3 / 15 | 8471 |
| weak crust, fault, overriding plate | 35 | 37.1 | 55.8 | 5 / 20 | 12082 |

A step on the split mesh costs what a step without the fault costs: the fault
adds degrees of freedom along one curve and the multigrid levels carry it. A
rebuild adds about 24 s. Measured on rank 0 over 21 rebuilds at sixteen
processes, 9 s of that is carving the cavity in the base, filling it with the
band and splitting every level (4.3 s in the carve, fill and sew, 2.5 s building
the new meshes, 1.5 s cutting along the trace, 0.5 s in the split), 1.5 s is the
partition, 4 s is the solver's set-up (1.4 s compiling its functions, 1.1 s
building the multigrid transfers), and the first solve on the new mesh takes
about 11 s longer than an ordinary step's because it begins with a Picard
iteration. Measured as the extra over an ordinary step, 19 to 25 s per rebuild,
following the trench through 27 rebuilds costs 7 per cent more wall time than
the run without a fault, and through 47 rebuilds, when the trench moves far and
fast, about 14 per cent; in that run the rebuild steps, each about twice an
ordinary one, hold 27 per cent of the wall time.

The partition has little to do here. The base mesh of 126,976 cells is divided
once, 8192 or 7168 cells per process on every level, and the band adds 430 to
570 cells to the process that holds the trench. The largest load on the finest
level stays within 3 per cent of the mean while the band sits on a lighter
process and within 9 per cent once the trench has moved onto a full one; the
add-on levels follow the same pattern, and every transfer found its nodes
without a cross-partition search. The balance is the base partition's, as the
design intends, and the fault region's cost is one process's few hundred cells.

```{figure} figures/trench-cost.png
:alt: Two panels for the run with 47 rebuilds. Top, wall time per step stacked by phase over 300 steps, about 24 s on ordinary steps and about 49 s on the rebuild steps, which are marked by vertical lines every five steps or so; the extra is 12 s of build and about 11 s more in the Stokes solve. Bottom, the number of cells per process on the finest level at seven checkpoints, minimum 7168, mean about 7965, maximum 8192 up to step 100 and 8600 to 8700 from step 150 on.

The run with 47 rebuilds. Above, wall time per step by phase; the rebuild steps
stand out and cost about twice an ordinary step. Below, the load per process on
the finest level after each rebuild's partition, measured at seven checkpoints:
the owner of the fault region carries the band's few hundred cells, and the
largest load stays within 3 to 9 per cent of the mean as the fault moves.
```

The fit that finds the fault is also where the method is sensitive. Whether the
trace has moved enough to rebuild is a threshold on a fitted curve, so two runs
that differ at the level of the solver tolerance can fall on different sides of
it and take different rebuild decisions; and each rebuild's transfer carries the
velocity onto the new mesh but not the jump across the old fault's position, so
the slip on the fault drops at a rebuild, by about half in these runs. Neither
changes the plate-scale answer here, where the fault under a weak crust
reproduces the trench history of the run without one, but a slip record has to
be read with the rebuilds marked.

## What it costs, and what is refused

The add-on's load is proportional to the fault's length rather than the
domain's area. A fault band two cells wide at $h = 0.003$ along a trace of unit
length is a few thousand cells on a base of a few thousand; a network of faults
is the sum of its bands. The base pays nothing for the fault, which is the
reason to build it this way.

A **junction** between two faults is where the construction is narrowest. Two
cuts cannot share a vertex, since it would be a pinned tip of both, so a branch
stops one cell short of the fault it meets, and that ligament is one fine cell
wide. The replay of a network onto the coarser add-on levels stops at the first
level below the finest, and that level and those beneath it stay welded: a
junction needs a side assignment the replay does not yet define, and on a deeper
add-on the coarser level's snap can invert a cell. A network therefore gets the
welded tail below the finest, and converges as the welded tail does.

A **placed band** that is not cut, the weak or transversely isotropic ribbon,
keeps its mesh on every level but is not replayed as a cut, and takes the
welded tail with a patch smoother on the band. A **fault near a boundary** needs
the band to meet the wall, and the outcropping ladder that does this is serial.
In **three dimensions** a fault is a triangulated sheet placed into the child.
On a child with two add-on levels the sheet places, at a clearance of 0.9
(44,382 tetrahedra, 7 velocity iterations), but no intermediate add-on level
survives in the multigrid tail, so a three-dimensional fault on an add-on mesh
has no split coarse level yet.
These are the limits of the construction as it stands, and each is a statement
about the mesher rather than the method.

One cost is a defect rather than a design. Each rebuild of the add-on currently
leaves the previous child, or the solver objects built on it, in memory: on the
annulus runs above, 7 GB per node of sixteen processes at every rebuild, the same
on a fresh process and an old one, so that a run with 24 rebuilds filled a 188 GB
node. The runs were completed as chains of restarts, each a fresh process
restoring the saved child exactly, which the restart design above makes
possible. The reference that holds the old child is being traced; until it is
released, a long run with many rebuilds is a sequence of restarts.

## In parallel

The base is distributed once and its partition is never changed for a fault; a
rebalance of the base would be a rebuild of everything above it. The add-on
inherits the base's partition when it is refined, and the surgery that follows
is local: the region of cells a cut or a split touches is made interior to one
process before the surgery runs, and the load the band adds is balanced across
the add-on by moving cells far from the faults between neighbouring processes,
with the one assignment applied to every add-on level so that the levels stay
co-partitioned with each other. The base's levels never move, and the transfer
between the base's finest level and the first add-on level is built from the
recorded parent of each add-on cell rather than by searching for it.

On the refined box with a split fault at eight processes, the process owning the
fault held 1.4 times the mean number of velocity nodes after balancing, against
2.1 before, and the velocity solve took six iterations against four in serial.
Meshing and cutting a fault across a partition boundary, which is what the band
constructions need and the cut does not, is a separate subject with its own
measurements, and it is not treated here.

## Using it

The recipe below is the whole method in one place, for a two-dimensional box.
The same calls take a triangulated sheet in three dimensions.

```python
import underworld3 as uw

# The base: built with a hierarchy, refined once, never cut.
base = uw.meshing.UnstructuredSimplexBox(cellSize=0.1, refinement=1, qdegree=3)

# The fault as a geometric object; its distance drives the refinement.
fault = uw.meshing.Surface("fault", base, fault_points, symbol="F")
fault.discretize()
metric = fault.refinement_metric_function(h_near=0.00625, h_far=0.1, width=0.05)

# The add-on: refined toward the fault, conforming to it, split on every level.
child = base.adapt(metric, max_levels=4)
mesh = child.add_fault([("Flt", fault_points)])

# The solve picks up the stack as its multigrid hierarchy.
stokes = uw.systems.Stokes(mesh)
stokes.add_fault_bc(0, "Flt")
stokes.solve()                          # slip is the tangential jump on each pair
```

`add_fault(..., split_levels=False)` keeps the welded tail for comparison. The
solve's own record (`stokes._rotated_freeslip_info`) carries the iteration
counts and the convergence reference, which is where to look when a warm start
seems not to help.

<!--
FIGURES (delivered from hyperion at underworld3 e135429f; scripts, records and README in figures/src/)

stack.png          one panel per level near the fault, base levels and split
                   add-on levels, copies drawn apart.
                   from scripts/sessions/fault_mg/fig_hierarchy_render.py (k=3)
iterations.png     iterations vs k for the four hierarchies, frictionless and
                   viscous.  from scripts/sessions/fault_mg/fig_fmg_behaviour.py
moving-fault.png   three fault positions, mesh + stress, cost bars at np 8.
                   from scripts/sessions/fault_mg/stage6_moving.py +
                   summarise_moving.py (library route preferred: library_c.py)

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
-->

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=faults-on-an-add-on-mesh">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=faults-on-an-add-on-mesh">Start one</a></div></div>
