---
title: Faults and patch-refinement of the mesh
description: >-
  A slipping fault is a discontinuity the mesh has to represent, along a trace
  that moves as the model runs. We build the fault into a
  short-lived mesh made from a static base. The base holds the state, the
  partition and the coarse multigrid levels; the add-on is a copy of the base's
  finest level with the fault placed into it as a narrow structured band, split
  along the fault, and rebuilt from the base whenever the fault moves.
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
thumbnail: figures/annulus-movie-still.png
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/faults-on-an-add-on-mesh/
    template: ../../templates/pdf
    output: faults-on-an-add-on-mesh.pdf
    article_id: UWTN 2026-022
    article_version: 1.0.0
    software_version: underworld3 development @ 25d62812
---

<!-- Historical development and provenance records: drafting-history-before-cull-2026-11-17.md. -->

In this note we look at how Underworld3 puts a slipping fault into a model without remeshing the whole model each time the fault moves. The mesh must resolve the velocity discontinuity along the fault while supporting an efficient solve across the domain.

We divide the mesh in two. A **base** mesh holds the model's fields, particles and multigrid hierarchy. An **add-on** is a copy of its finest level with a narrow band of cells placed along the fault and split so that the two sides can slip. When the fault moves, we rebuild the add-on and reuse the base hierarchy.

The fault formulation is described in [Faults: to mesh or not to mesh?](https://www.underworldcode.org/putting-a-fault-in-a-mesh/). Here we concentrate on the solver: how a continuous base hierarchy and a local patch solve handle the discontinuity, and what this costs when a fault moves through a convection model. The underlying full-multigrid setup is described in [UWTN 2026-014](https://www.underworldcode.org/setting-up-full-multigrid/).

## The base mesh and the add-on

The base mesh covers the whole domain and is continuous across the fault. It is built and partitioned with a refinement hierarchy. Temperature, material markers and bulk history variables remain on the base; the fault's own history is stored on the fault object.

Underworld fault objects already carry a discretised geometry: points along a trace in two dimensions, or a triangulated surface in three. This supplies the geometry for the add-on. The ladder can be sized to match the fault discretisation or the local base mesh; resampling the fault object is another option. In the example here, we construct the fault points ourselves and match the ladder to their spacing.

The add-on is a child of the base, built in three steps:

1. **Copy the base's finest level.** Away from the fault, the add-on retains the base's cells.
2. **Place the fault as a ladder.** The supplied fault points form the spine. Here they have uniform spacing $S$, and we choose to place a rail a distance $S$ on either side. The resulting two rows of squares are divided into triangles. A margin rung closes each end, and graded triangles connect the band to the remaining base cells.
3. **Split the spine.** Interior spine vertices are duplicated and the cells on one side are connected to the copies. The fault's constitutive law couples each pair.

For this matched construction, the **band ratio** $h_b/S$ measures the ladder resolution relative to the base's finest cell size. In the construction below, $h_b = 1/32$ and $S = 0.0052$, giving a ratio of about 6. The fault adds 906 cells to the base's 2,592 cells. The base cell count stays fixed as the fault resolution increases.

```{figure} figures/ladder-construction.png
:alt: Three parts. (a) Mesh edges near the left tip of a straight fault: a tinted band two cells wide, made of squares of side S each divided into two triangles, with the spine along the fault, a rail S either side, a rung across the band at every spine point and a margin rung one spacing beyond the tip, which is marked by an open circle; graded triangles surround the band and grow to the base cell size h_b, marked by a dimension line. (b) The same band after the split: the two copies of the spine drawn apart, one solid and marked plus, one dashed and marked minus, every interior spine vertex doubled and the tip vertex single. (c) Four panels of the multigrid hierarchy, in the same window: the split child, with its band and graded fill tinted; then the base's three levels, whose cells are h_b, 2h_b and 4h_b, with no fault in the mesh and the fault drawn as a hidden line.

The fault ladder and multigrid hierarchy. (a) The spine follows the fault, with rails a distance $S$ either side and graded triangles connecting the band to the base mesh. (b) The split duplicates interior spine vertices, allowing slip; the tips remain single. (c) The split child sits above the continuous base levels. The tinted cells and a surrounding layer of base cells form the patch solved exactly by the smoother.
```

The child becomes the finest multigrid level, above the base's existing levels. Model fields are interpolated onto it for the Stokes solve, and the resulting velocity is transferred back to the base for advection. Rebuilding the child leaves the base mesh and its history variables in place.

## The solve workflow

The fault object supplies the discretised trace. We choose the ladder resolution relative to that trace and the local base mesh, resampling the fault if needed. For the simple-shear example, the trace is a straight line with uniform spacing $S$, and a band width of $2S$ gives equant ladder cells.

The algorithm is:

1. Build the base mesh and its multigrid hierarchy, and initialise the model fields and fault object.
2. Construct the add-on around the fault geometry and split it along the trace.
3. Transfer the fields needed for the Stokes solve from the base to the add-on.
4. Solve on the add-on, using the base hierarchy and an exact patch solve around the fault.
5. Transfer the velocity back to the base, advance the model and update the fault geometry. Rebuild the add-on when the fault moves.

Bulk history variables remain on the base throughout, and the fault object carries the fault's own state.

## Multigrid with a split finest level

The velocity solve uses geometric multigrid with the split child above the continuous base levels. Prolongation evaluates the base's finite-element field at the child's nodes. The two copies of a spine vertex therefore receive the same correction: the base can correct their mean velocity, while corrections to the slip must come from the finest-level smoother. With Galerkin coarse operators, $P^T A P$, and restriction $P^T$, the residuals at the paired vertices are summed on transfer to the base.

A pointwise smoother such as SOR reduces slowly varying slip errors along the fault only slowly, particularly as the band is refined. We therefore follow each SOR sweep with an exact solve on a **patch** containing the band, the graded fill, the split vertices and a surrounding layer of base cells. The patch is identified from the mesh transfer and factorised by LU when the preconditioner is set up.

We measured velocity iterations in the simple-shear example at band ratios of 6, 12 and 24, and in a yielding-lid convection model at ratios of 8, 16 and 25. The latter is a 4 × 1 box with a fault through the lid, solved on four processes from rest at a state where the lid is mobilising. Each velocity Krylov iteration uses one full-multigrid cycle.

| Smoother on the child | Simple shear: iterations per velocity solve, ratios 6, 12, 24 | Yielding lid: velocity iterations per Newton iteration, ratios 8, 16, 25 |
|---|---|---|
| SOR, then patch LU | 3, 3, 3 | 7, 7, 7 |
| SOR, then patch ILU(0) | 8, 12, 16 | 28–200, 73–200, 86–200 |
| SOR | 12, 17, 24 | 161–175 at ratio 16 |

With an exact patch solve, the iteration count stays constant across the tested band ratios in both problems. Incomplete factorisation increases the count, with one yielding-lid solve at each ratio reaching the limit of 200 iterations. SOR alone is also increasingly expensive. Peak slip agrees within solver tolerance across the tests.

For curved free-slip walls, each multigrid level also uses its own wall-normal frame, as described in [UWTN 2026-016](https://www.underworldcode.org/boundary-conditions-on-non-planar-boundaries/).

## Following a trench

Our moving-fault example is a subducting plate in a mantle-depth annulus, with free-slip walls, basal and internal heating, and a continent behind the incoming plate. An 11 km melange layer marks the plate interface [@Sandiford_2019]. A frictionless fault follows its base, with a weak zone continuing the fault to the surface. The melange itself is a passive marker in this run. We use the model here to demonstrate the numerical method; the subduction science is still being developed.

```{figure} figures/annulus-movie.mp4
:label: fig-annulus-movie
:placeholder: figures/annulus-movie-still.png
:alt: Movie in two panels over 800 steps. On the left, the whole annulus coloured by temperature, with a cold lid at the surface. A slab sinks from a trench near the top, reaches the bottom of the mantle and spreads along it, and thin hot plumes rise from the base as the run goes on. Outside the surface, a black arc grows clockwise from a tick marked start as the trench rolls back, and the centre of the annulus reads the rollback in km and degrees, 2,228 km at the furthest. A box marks the window shown on the right. On the right, a close-up of the trench, in which the slab descends steeply beneath a thin green melange layer and a black fault, with streamlines of the flow, and above it a line plot of the surface velocity across the trench.

The trench run, 3–1,103 Myr. Left: the annulus, with the initial trench at the top and the black arc marking rollback. Right: a view centred on the moving trench, with surface velocity above it. Temperature runs from blue (cold) to red (hot); green marks the melange layer, orange the oceanic crust and black the fault. The PDF shows step 460, at maximum rollback.
```

The fault follows the material interface and also defines the surface along which slip occurs. These can drift apart during advection, so we reposition the fault consistently by fitting its trace to the material markers.

The base's finest cells are about 45 km across, with ladder rungs 22.7 km apart: a band ratio of 2. As the trench moves, we rebuild the child around the fitted trace and reuse the base hierarchy. The trench rolls back 2,228 km by step 460, then advances again before the run ends at step 799. The band adds only 249–332 cells to the base's 126,976 cells. The [mesh movie](figures/trench-movie.mp4) and [four snapshots](figures/trench-mesh.png) show the band following the fault through the fixed base mesh.

On 26 processes, a step took 99 s on average, excluding a further 16 s for checkpoint output. The Stokes solve accounted for 82 s. Building the child took 4.4 s, transferring fields onto it 2.8 s and transferring the solution back 2.7 s: together about 10 per cent of the step.

The add-on was rebuilt on 759 of the 799 steps after the first. On 28 steps the fit found no new position; on 12, placement was refused because the fitted trace reached the boundary. These 40 steps reused the previous mesh. The run averaged seven nonlinear iterations per step; the final velocity and pressure solves of each step averaged 4.5 and 12 iterations respectively. No linear solve reached its iteration limit. Relative tolerances were $10^{-3}$ for Stokes, $10^{-2}$ for pressure ($10^{-4}$ on the first solve) and $3.3 \times 10^{-5}$ for velocity.

```{figure} figures/trench-cost.png
:label: fig-trench-cost
:alt: Four panels against step, 0 to 799. (a) Wall time per step stacked by phase, about 99 s, most of it the Stokes solve, with thin bands for building the add-on, transferring the fields onto it, carrying the solution back to the base, and the rest of the step. (b) The build, transfer and carry-back times per step, about 10 s together, with low points at the 40 steps that kept the previous mesh. (c) The peak slip rate on the fault per step, between 0.65 and 3.74 cm/yr. (d) The band's cells and the cells the add-on adds to the base's finest level, at each of the 759 builds.

The cost of following the trench. (a) Wall time per step, excluding checkpoint writes. (b) Mesh construction and transfers; the low points are the 40 steps that reused the previous mesh. (c) Peak slip rate. (d) Cells in the band and the net number added to the base mesh.
```

## Current limits

Separate fault ladders must remain apart, so junctions retain a gap between bands. At a domain boundary the split stops short of the wall; the trench example continues it to the surface with a weak zone. The efficiency measurements here are two-dimensional. The cost of factorising a patch around a fault surface in three dimensions remains to be measured.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=faults-on-an-add-on-mesh">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=faults-on-an-add-on-mesh">Start one</a></div></div>
