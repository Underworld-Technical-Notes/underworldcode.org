---
title: "Faults in parallel: partitioning the add-on once"
description: >-
  A fault is cut into a mesh that is already distributed, and the cut, the
  placement and the split each need a whole neighbourhood on one processor.
  This note partitions the refined part of the mesh around the faults once,
  before any surgery, so that every construction runs on cells one processor
  already holds and the multigrid levels stay together.
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
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/faults-in-parallel/
    template: ../../templates/pdf
    output: faults-in-parallel.pdf
    article_id: UWTN 2026-018
    article_version: 1.0.0
    software_version: underworld3 feature/parallel-addon-distribution @ 8fe9ad76
---
A fault in a geodynamic model is a thin object in a large mesh. It needs its own
resolution — a band a few elements across, along a trace that wanders where the
geology says it wanders — inside a mesh whose cells are elsewhere a hundred times
larger. Building it is mesh surgery: refine toward the trace, cut the trace into
the mesh or place it there, and, if the fault is to slip rather than merely
deform, duplicate the nodes along it so that the two sides can move past one
another.

The cut, the placement and the split all assume they can see a whole
neighbourhood. In parallel the mesh is distributed before the fault is placed,
by a partitioner that balances cells and knows nothing about the fault, so a
partition boundary is as likely to run through the fault's neighbourhood as
anywhere else. This note describes how Underworld3 resolves that: the refined
part of the mesh is partitioned once, with the faults in view, before any
surgery, and every construction afterwards runs on cells that one processor
already holds. A fault represented as a weak band needs less than that, and has
a second answer of its own.

## The add-on frame

The constructions here work on a mesh in two parts. The **base** is a mesh
hierarchy built once and refined uniformly in place, so that all its levels are
partitioned together; it carries the bulk fields and supplies the coarse levels
of the multigrid solver, as described in
[Setting Up Full Multigrid](https://www.underworldcode.org/setting-up-full-multigrid/).
The **add-on** is built on the base's finest level whenever the faults are
placed: a few levels of local refinement toward the fault traces, with the fault
cut into the finest of them and carried down through the others, split on every
level so that the coarse spaces contain the discontinuity too. The add-on holds
no state of its own and is rebuilt whenever a fault moves. The bulk state lives
on the base and the fault's history on the fault object, so the add-on can be
discarded and remade at any time.

The solver's multigrid hierarchy is the base's levels followed by the add-on
levels. Two kinds of transfer connect them: between consecutive add-on levels,
and from the base's finest level to the first add-on level. The base's own
partition is never changed by anything in this note.

## What the surgery needs from the partition

Three constructions need a neighbourhood on one processor, each for its own
reason.

**Placing the surface.** A fault that is placed rather than cut deletes the mesh
vertices in its way and fills the cavity with a mesh that carries the fault as
element edges, or faces in three dimensions. The rebuilt mesh carries the old
sharing structure across by renumbering, so no point the surgery deletes or
creates may be shared between processors. That takes about three layers of cells
around the fault on one processor: the cells deleted, the ring the fill attaches
to, and one more so that the ring's own points are unshared.

**Splitting.** The nodes along the fault are duplicated and the cells on one side
rewired to the copies. Which side a cell is on is decided by walking the fan of
cells around each fault node in order, and a fan divided between processors
cannot be walked.

**Solving.** The two nodes of a coincident pair are tied by the no-opening
constraint, assembled as a small block in the fault's own frame, and that frame's
normal is accumulated from the fault facets around the node. A pair whose nodes
live on different processors puts its block in no processor's diagonal, and a
node whose facets are divided accumulates half a normal.

## One partition for the add-on

The add-on is partitioned once, on its finest level and before any surgery, and
the same assignment is applied to every add-on level through the relation
between each cell and its parent on the level below. Four rules make the
assignment.

**The unit of assignment** is a cell of the coarsest add-on level together with
all its descendants on the finer add-on levels. Every cell of a unit goes to the
same processor, so consecutive add-on levels stay partitioned together exactly.

**Fault regions** are the cells the surgery will touch: the star of the cells
within reach of the fault, plus growth layers — one for a cut, two for a
three-dimensional placement — so that every point the surgery touches is
unshared. They are marked on every add-on level, because a coarser level's star
reaches further than the finest's, then lifted to units and glued. Each region
is one indivisible block, sent to the processor that already holds most of it,
or left where it is if it is already interior to one. Regions whose shells touch
merge, and surfaces placed earlier are glued the same way, so a second placement
never divides the first.

**The balance** is restored by diffusion across the partition boundaries. In each
sweep a processor heavier than a neighbour by more than the tolerance offers it
units that belong to no region, up to half the difference, the cells farthest
from the faults first. The sweeps stop when every processor is within the
tolerance of the mean or nothing more can move.

**The surgery** then runs on regions each processor holds whole — the cut, the
placement and the split of every add-on level — and moves nothing. A split that
finds a fault node shared between processors refuses on every processor at
once, rather than redistributing to get round it.

% FIGURE PENDING (hyperion): parallel_pipeline.png from fig_schematics.py,
% redrawn for the partition-once pipeline. Script to figures/src/.
```{figure} figures/parallel-pipeline.png
:alt: A schematic of the parallel pipeline. The base hierarchy's levels sit at the bottom, unmoved. Above them the add-on levels, with the fault region marked on every level and glued into one block, are assigned to processors once; the cut and the split of every add-on level then run inside that assignment, and the transfers between levels are drawn as local except the one from the base's finest level, which reads the recorded parent cells.

What moves, and when. The add-on is assigned to processors once, with every
fault region kept whole; the surgery on every add-on level then happens inside
that assignment, and the base never moves.
```

The other way to meet the requirements is to keep the partitioner's assignment
and make the split work across it. In two dimensions that was built: the fault
is exchanged as one chain that every processor walks identically, a cell at a
shared fault node takes its side from the sector containing its centroid, and
the normal at a shared node is completed from the global chain. It is rejected
for the split for three reasons. The pair block and the normal both lean on a
fan that one processor holds; in three dimensions the chain becomes a global
surface patch with a side rule at every shared rim vertex; and the case that a
base graded toward the fault makes common — a partition boundary running along
the fault rather than across it — is refused by it outright. Stopping the split
one cell short of each partition boundary avoids the exchange and fails on
physics: every stop is a pinned tip, where slip goes to zero. On a long fault
crossing one boundary the stopped cut lost 13% of its peak slip per crossing,
and the loss did not respond to the viscosity of the weak zone painted across
the gap.

## The transfers between levels

The partition keeps the multigrid transfers local. Every pair of consecutive
add-on levels is partitioned together, so each fine node is found in a coarse
cell that the processor already holds. Where a level is split, the coarse cell
for a fine node is located from the centroid of a fine cell containing it, which
is never on the fault, so each copy of a node on the fault interpolates from its
own side.

The one pair the partition separates is the base's finest level against the
first add-on level, where a unit that moved has taken its cells away from the
base cells they refine. That pair uses the refinement relation itself instead of
searching for nodes. Each add-on cell records its parent on the level below, and
the record travels with the cell when it moves. The transfer fetches each fine
cell's parent — its nodes and their coordinates — from wherever it lives, in one
exchange, and evaluates the parent's Lagrange basis at the fine node. Nothing is
located across processors.

## What it measures

The test is that the parallel solve converges like the serial one while the load
stays balanced, and that the partition costs little next to the surgery it
serves.

The first fixture is a three-dimensional box with an internal fault patch,
refined twice and split, 19,072 cells after the split, with quadratic velocity
and a solver tolerance of $10^{-4}$. The load is the number of finest-level
velocity nodes per processor, reported as the largest over the mean. The second
column is the same fixture when each surgery instead moves the cells it needs
onto one processor afterwards.

| processors | load, moved after surgery | load, partitioned once | velocity iterations | wall time |
|---|---|---|---|---|
| 1 | — | — | 4 | — |
| 2 | 1.16 | 1.08 | 5 | 65 s |
| 4 | 1.27 | 1.06 | 6 | 34 s |
| 8 | 2.12 | 1.41 | 6 | 25 s |

At eight processors the heaviest one holds the fault region and nothing else:
3,524 of the 19,072 cells, after 13 balance sweeps. A region is the indivisible
unit, so a single fault is at least one processor's load, and that is where the
balance stops.

% FIGURE PENDING (hyperion): per-processor load, from probe_load_3d.py's
% records, before and after the partition at np 2, 4, 8. Script to figures/src/.
```{figure} figures/load-per-processor.png
:alt: Bar charts of finest-level velocity nodes per processor for the faulted three-dimensional box at two, four and eight processors, with surgery moving cells afterwards and with the add-on partitioned once. The largest-over-mean load falls from 1.16 to 1.08 at two processors, 1.27 to 1.06 at four, and 2.12 to 1.41 at eight, where the heaviest processor holds exactly the fault region.

Load per processor on the faulted box, with the cells moved after each surgery
and with the add-on partitioned once.
```

In two dimensions, on an add-on built toward a fault trace with 1,360 cells on
its finest level, the load at two processors falls from 1.38 to 1.09, every pair
of add-on levels is partitioned together, and the base-to-add-on transfer
fetches every parent with no search. At four and eight processors on that
fixture the fault region, 544 cells with its growth layers, already exceeds the
mean load, so its owner keeps it whole and carries the excess.

Splitting every add-on level is what keeps the iteration count flat as the
add-on deepens. On a box in simple shear with a straight fault, the velocity
solve takes 6, 5 and 4 iterations at two, three and four add-on levels, against
13, 18 and 23 when the add-on levels are left unsplit, and the peak slip agrees
between the two to six figures. In parallel, measured on 13 October with the
fault's cells moved after the split rather than partitioned beforehand, the
split levels took 6 and 5 iterations at two processors and 7 and 6 at four, for
two and three add-on levels. A fault moved through three positions at four
add-on levels, with the add-on rebuilt and re-split at each, took 7 iterations at
eight processors against 4 to 5 in serial, and its slip agreed with the serial
slip to six figures.

The partition is cheap. On four processors it takes 1.35 s for a
three-dimensional add-on of 87,525 cells around one fault sheet, and 0.64 s for
a two-dimensional add-on of 94,910 cells. For comparison, splitting the 19,072
cells of the box above takes 3.6 s, most of it in building the meshes.

## The band through the partition boundary

A fault represented as a weak or transversely isotropic band needs less than a
slipping one. Its rheology carries the fault, nothing is duplicated, and the
only requirement is a continuous mesh across the partition boundary. The band
can be placed after the partition above, like any other surface, and in two
dimensions it can also be meshed straight through the partitioner's own
boundary, with nothing moved and the balance left as the partitioner made it.
That second construction works as follows.

- **Ownership is decided by the cavity.** Every cell of the band belongs to the
  processor whose deleted cells contain its centroid, and every band vertex and
  every edge of the band's outer skin likewise. The boundary between two
  processors' band cells is then a chain of the band's own edges and needs no
  construction of its own.
- **Deleting a vertex on the boundary is one decision.** A shared vertex is
  removed only if the band itself reaches it, never merely because it lies
  within the carve's clearance, and the decision is reconciled so that both
  processors delete it or neither does. A boundary the band runs beside keeps its
  edges.
- **Each processor's fill outline is a graph** of its uncut ring edges, its share
  of the skin, and one connector from each end of a cut span to the nearest free
  end of the skin. Every vertex has exactly two edges, and walking the graph
  gives the outlines, with enclosed loops filled as holes.
- **Vertices of the band that more than one processor creates are one point**,
  owned by the lowest-numbered processor and registered as shared before the
  mesh's edges and faces are built.

In serial it reduces to the placement exactly. On a single fault crossed once by
the boundary at two processors and twice at three, the band's peak slip rate is
0.5688 in every case, the serial value, with 1,212 and 1,042 cells on the two
processors and 784, 891 and 571 on the three. On a four-strand network at fine
resolution, three strands match the serial profile to within 0.1% and the
strand the boundary crosses to within 2%, which is the noise of the fill at the
crossing.

% FIGURE PENDING (hyperion): the band meshed through the boundary, TI, np = 2,
% from the S-fault rig, replacing the September mesh-at-the-seam.png whose
% third panel is labelled as a split. Script to figures/src/.
```{figure} figures/band-through-the-boundary.png
:alt: Zoomed meshes where a partition boundary crosses a fault band, drawn as edges on white with the fault traces in red. In the parallel panel the two processors' cells are drawn in different colours, the boundary between them runs along the band's own edges, and the vertices both processors hold are marked.

A band meshed through the partition boundary. The band keeps its own resolution
through the crossing, and the boundary between the two processors' cells runs
along the band's own edges.
```

## What is refused

Several configurations are declined rather than approximated, each with a
message on every processor.

**A slipping fault with a node on a partition boundary.** After the partition
this does not arise; a split that finds one refuses rather than moving cells to
get round it, so a refusal means the partition was bypassed.

**A fine node in no recorded parent cell.** The transfer from the base's finest
level refuses rather than search for it.

**A partition boundary along a band that is meshed through it.** When the
boundary follows the band along strike, every vertex on it is deleted and the
two fills have no common boundary to keep. A crossing so oblique that the band's
skin changes hands at fewer than two vertices is refused for the same reason.

**A fault tip exactly on the partition boundary beside a junction, or a junction
within a band width or two of the boundary**, again for a band meshed through
the boundary. In both the fill's outline crosses itself. The outline is checked
before the mesher sees it, because a mesher handed a self-crossing outline does
not refuse but spins, and a run that has stopped producing output is much harder
to diagnose than one that has stopped with a message.

Some things are not built. In three dimensions the band is placed after the
partition; there is no construction that meshes it through the partitioner's
boundary, and none that splits through one. A direct call to the placement
routines, outside the mesh's own interface, still moves its region onto one
processor before placing. A layer extruded from a faulted sheet is built on one
processor and then distributed, which bounds its size by one processor's memory.
Reloading a partitioned add-on from a checkpoint is not supported; the add-on is
rebuilt from the base and the fault objects instead.

## Where this leaves things

For a slipping fault, the add-on is partitioned once with each fault region
whole, the surgery on every add-on level runs inside that partition, and the
solve converges in close to the serial number of iterations, with the load
within a few percent of the mean wherever the fault region is smaller than one
processor's share. For a weak band the same partition serves, and in two
dimensions the band can instead be meshed through the partitioner's boundary
with nothing moved. The base is never repartitioned for a fault.

The limit is granularity. A fault region is indivisible, so one long fault is
at least one processor's load, in proportion to its length in two dimensions and
its area in three. Cutting a long fault along strike into pieces that different
processors own would lift that limit; it is not built, and will be when a model
needs a fault longer than one processor comfortably holds.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=faults-in-parallel">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=faults-in-parallel">Start one</a></div></div>
