---
title: "Faults in parallel: meshing and cutting across the partition"
description: >-
  A fault is a thin object in a large mesh, and the partitioner does not know it
  is there. This note is about building the fault's mesh, and cutting it into a
  slipping surface, without first gathering it onto one processor.
date: 2026-09-08
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
    article_id: UWTN 2026-017
    article_version: 1.0.0
    software_version: underworld3 0.0.0
---
A fault in a geodynamic model is a thin object in a large mesh. It needs its own
resolution — a band a few elements across, along a trace that wanders where the
geology says it wanders — and that band has to be built into a mesh whose cells
are elsewhere a hundred times larger. In serial this is mesh surgery: cut a
cavity out of the background mesh, mesh the fault's own layer, sew the two
together, and if the fault is to slip rather than merely deform, duplicate the
nodes along its mid-surface so the two sides can move past one another.

In parallel none of that is local. The mesh is distributed before the fault is
placed, and the partitioner divides it to balance the cell count, knowing
nothing about where the fault will go. Worse, the partitioner is *attracted* to
the fault: the region is about to be refined, so a balanced partition tends to
put a boundary through exactly the part of the mesh the surgery needs to see
whole.

This note is about doing the surgery anyway. It is the parallel half of a
larger problem; the serial constructions are assumed and described only far
enough to say what breaks.

## What has to be true for the surgery to work

Two operations, two different requirements.

**Placing the band.** A cavity is cleared from the background mesh, the fault's
own layer is meshed to its own resolution, and the space between the layer's
outer skin and the cavity's ring is filled. The fill is a triangulation of a
region bounded by two curves, and it has to be *one* region: the mesher is
handed a closed outline and returns cells inside it. A cavity that straddles a
partition boundary is two half-regions on two processors, neither of which is a
closed outline.

**Cutting the mid-surface.** The nodes along the fault are duplicated and the
cells on one side are rewired to the copies, so that the finite element spaces
carry a jump. Deciding which side a cell is on means walking the fan of cells
around each node of the fault, in order. A node on the partition boundary has
part of its fan on one processor and part on another, and neither can complete
the walk.

Both requirements have the same shape: a local construction that assumes it can
see a whole neighbourhood, applied to a mesh that has been cut into pieces
without regard for that neighbourhood.

## The obvious answer, and what it costs

The obvious answer is to move the fault to one processor. Mark the cells
touching the fault, plus a layer, and reassign them all to the processor that
already owns most of them. That processor then holds the whole neighbourhood,
does the surgery, and every processor rebuilds its part of the result. The
requirement is met by construction.

It works, and for a single fault in a modest mesh it is the right thing to do.
The cost appears in two places. The moved region is thin, so the imbalance is
bounded by the fault's own size rather than by the refined band — but for a
network of faults spread across the domain, moving them all to one processor
moves a great deal, and the processor that receives them is left with a mesh
that is not balanced against anybody else's. On a test with a fault network in a
unit box, the gather moved 91% of the fixture.

The second cost is subtler and matters more. Because everything is gathered
before the surgery, the *answer* is a serial answer computed on one processor
and then redistributed. Nothing is learned about whether the construction is
partition-independent, because it never runs on more than one partition.

## Leaving the seam alone

A cheaper answer is to stop short. Each processor carves its own part of the
cavity but stops one cell before the partition boundary, and the band's
cells there are left as background material — a **ligament** — which the
fault's rheology is painted onto but which the cut does not pass through.
Nothing moves. A fault that crosses a processor twice is cut as two pieces, each
with its own ends.

This is a genuine option for a fault represented as a weak zone, where the
ligament simply carries a slightly coarser weak band across the boundary. On a
long fault crossing one seam it costs a few tenths of a percent in the peak
slip rate, and the cells stay balanced.

It is not an option for a fault represented as a slipping cut. A cut that stops
short leaves a **pinned tip** at every crossing, and a tip is where slip goes to
zero. The fault is welded to itself at the partition boundary. Measured on the
same long fault, the cut lost 13% of its peak slip per crossing, and — the
diagnostic that settles it — the loss did not respond to the weak-plane
viscosity painted on the ligament. No rheology can free a pinned tip.

## Meshing the band through the seam

The alternative is to admit that the cavity straddles the boundary and to mesh
the band on both sides, so that the two processors' meshes agree along a curve
that lies *inside* the band.

The construction that works turned out to be simpler than the one first
sketched. There is no negotiated interface surface and no realignment of the
partition. Instead:

- **Ownership is decided by the cavity.** Every cell of the fault's own layer
  belongs to the processor whose cleared cells contain its centroid; every
  vertex of the layer, and every edge of its outer skin, likewise. Three global
  arrays, one reduction each. The boundary between the two processors' layer
  cells is then a chain of the layer's own edges — the seam *inside* the band —
  and needs no construction at all.

- **Deletion at the seam is one decision.** A vertex of the background mesh that
  lies on the partition boundary is removed only if the band actually reaches
  it, never merely because it falls inside the carve's clearance, and the
  decision is reconciled between the processors that hold it, so both delete it
  or neither does. A boundary that runs *beside* the band keeps its edges, and
  the fills on either side keep their common boundary there.

- **The fill's outline is a graph.** Each processor's fill is bounded by its own
  ring edges that were not cut, its own share of the skin, and one connector
  from each surviving end of a cut span to the nearest free end of its skin
  runs. Every vertex then has exactly two edges, and walking the graph gives the
  outlines, with enclosed loops filled as holes. A junction the boundary crosses
  twice, a band the boundary skirts, and a fault ending near the boundary all
  come out of the same walk.

- **The new shared points enter the mesh's own bookkeeping.** Vertices of the
  layer that more than one processor creates are the same point, owned by the
  lowest-numbered of them, and they are registered as such before the mesh's
  edges and faces are built — an ordering that matters, because the alternative
  leaves each processor's faces oriented however its own local construction
  chose them.

In serial the whole path reduces to the previous one exactly.

## Cutting through the seam

With the band meshed through the boundary, the cut can follow. The obstruction
is the fan walk, and the answer is to give every processor the same fault.

The fault's facets are exchanged as pairs of *global* vertex identities — the
owning processor and its local index, which the mesh's own sharing structure
already provides — together with their positions. Every processor assembles the
same paths from the union, so a vertex on the partition boundary has the same
two neighbours everywhere, and the walk order, which decides which side is which,
is one decision taken identically rather than several taken locally.

At a vertex not on the boundary the fan is walked as before. At a vertex on it,
the fan cannot be walked, but it does not need to be: the two fault facets there
are edges of cells, so every local cell lies wholly within one of the two
angular sectors those facets bound, and the sector containing its centroid is
its side. Either sector may be empty, which is what happens when the partition
boundary touches the fault without crossing it.

The duplicate node is then created on *every* processor that holds the original,
owned where the original is owned. That last clause is not bookkeeping fussiness:
the two nodes of a coincident pair carry the constraint that couples them, and a
pair split across processors would put that constraint in nobody's diagonal
block.

One quantity has to be repaired afterwards. The interface condition needs a
normal at each pair of nodes, and it is accumulated from the fault facets around
the node, weighted by facet length. At a node on the partition boundary a
processor holds one of the two facets. Rather than exchange normals at solve
time — a collective call inside a routine that can fail locally, which is how
deadlocks are made — the split records the whole sum, which it already has from
the global fault, and the accumulator uses it in place of its own half.

## What it measures

The test is not that the parallel run completes. It is that the parallel run
gives the serial answer while the cells stay balanced, because the whole point
of not gathering is that nothing was quietly serialised.

A single fault of 35 elements across a unit box, crossed once by the partition
boundary at two processors and twice at three, solved as a frictionless
slipping cut:

| processors | cells per processor | coincident pairs | peak slip rate |
|---|---|---|---|
| 1 | 2264 | 69 | 0.5094 |
| 2 | 1212 / 1042 | 69 | 0.5094 |
| 3 | 785 / 890 / 571 | 69 | 0.5094 |

The pair count is the serial count, including the pair at the crossing itself;
the slip rate is the serial one to four figures; and no processor holds more
than 60% of the cells. Where the ligament construction lost 8 to 15% per
crossing, this loses nothing that can be measured. A three-strand network
crossed mid-fault gives the same result on every strand.

```{figure} figures/mesh-at-the-seam.png
:alt: Four zoomed meshes at the place where the partition boundary crosses the fault, drawn as edges on white with the fault traces in red; in the parallel case the two processors' cells are drawn in different colours and the shared vertices are marked.

The mesh where the partition boundary crosses the fault. The band keeps its own
resolution through the crossing; in the parallel case (third panel) the boundary
between the two processors' cells runs along the band's own edges, and the
vertices both processors hold are marked.
```

```{figure} figures/stress-and-slip.png
:alt: Four panels of the stress invariant on a logarithmic scale with the fault traces coloured by signed slip rate; the serial and parallel cut are indistinguishable.

Stress and slip for the same network: the cut in serial at two resolutions, the
cut through the partition boundary at two processors, and the weak-band
representation for comparison. The traces carry the signed slip rate, positive
for right-lateral.
```

## What is refused

Three configurations are declined rather than approximated, and saying so
plainly is more useful than a construction that silently produces something
else.

**A partition boundary that runs along the fault.** If the boundary follows the
fault's own facets rather than crossing them, the two cells of a fault facet
belong to different processors, and the two copies of that facet after the cut
would too. There is nothing to build the constraint in. The placement now also
keeps both cells of a fault facet with a single processor, which is what closed
a case where a three-processor partition had put one such facet on the boundary.

**A fault tip exactly on the partition boundary, beside a junction.** The fill's
outline walk doubles back on itself there and the resulting outline crosses
itself.

**A junction within a band width or two of the boundary.** The connector that
closes the fill's outline runs from a ring end to the nearest free end of a skin
run, in a straight line, with no check that the line is clear — and next to a
junction it can cross the bump that another strand's tip margin makes on the
skin. The fix is a retarget that both processors agree on, which needs an
exchange they do not currently have.

The last two are refusals rather than failures because a self-crossing outline
is detected before the mesher sees it. That check was worth adding on its own
account: handed a self-crossing outline, the mesher does not refuse, it spins,
and a run that has stopped producing output is considerably harder to diagnose
than one that has stopped with a message.

## Where this leaves things

For a fault represented as a weak band, or as a slipping cut, in two dimensions:
the band is meshed through the partition boundary, the cut passes through it,
nothing is gathered, and the answer is the serial answer. For three dimensions
the constructions carry over one dimension up — the fault is a surface rather
than a curve, its cut needs a global patch rather than a global chain, and the
side rule at a shared rim vertex comes from the patch's own face normals — but
that is not built, and the three-dimensional thin volume still gathers.

The refusals above are the honest boundary of the two-dimensional case, and two
of the three are about a fault junction sitting close to a partition boundary,
which is a coincidence of the decomposition rather than anything a modeller
chooses. A partition-steering answer — deciding where the boundary may fall
before the mesh is divided, rather than working around where it fell — would
retire all three, and is the obvious next thing to try.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=faults-in-parallel">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=faults-in-parallel">Start one</a></div></div>
