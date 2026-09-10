---
title: Putting a fault in a mesh
description: >-
  A plate boundary is prior knowledge in a mantle model, and it has to be put
  into the mesh by hand. Four ways to do it in two dimensions — a weak ribbon,
  a transversely isotropic ribbon, split nodes, and a transversely isotropic
  zone that ignores the mesh — what each asks of the mesh and of the
  constitutive model, and how resolution is stacked on a static base so a
  migrating fault does not accumulate mesh damage.
date: 2026-08-23
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
license: CC-BY-4.0
keywords:
  - Underworld Code
  - Tricks of the Trade
  - meshing
exports:
  - format: typst
    template: ../../templates/pdf
    output: putting-a-fault-in-a-mesh.pdf
    article_id: UWTN 2026-017
    article_version: 1.0.0
    software_version: underworld3 0.0.0
---

OUTLINE — not yet written.

## A fault is not the same object as a shear band

Localisation arises on its own wherever the rheology permits it. A shear band
forms where the strain rate concentrates, it is as wide as the physics and the
mesh between them allow, and it can fade when the loading that produced it
changes. Faults behave differently in three ways that matter for how they are
put into a model. They are long-lived, outlasting many changes in the flow
around them. They localise far more sharply than any band a mantle-scale mesh
resolves, down to a gouge zone of metres or less. And they are self-reinforcing:
once a fault has accumulated slip it has juxtaposed rocks that were never
neighbours, so its weakness belongs to the structure and to the material
contrast across it rather than to the strain rate passing through it at this
instant.

That is why a plate boundary enters a mantle model as prior knowledge. Ridges,
transforms and megathrusts are prescribed, with their positions and their
histories taken from observation, and a model that waits for them to emerge is
answering a different question. Two consequences run through everything below.
The feature needs resolution the domain cannot afford everywhere. And it moves —
a rolling-back trench carries the thing that needs the resolution across the
domain over tens of millions of years, so whatever the mesh does for the fault
it has to do again, repeatedly, without degrading.

The width is the other consequence. No mantle-scale mesh reaches a metre, so
every representation here is a sub-grid one: either the fault is given a width
the mesh can carry and a rheology to go with it, or it is given no width at all
and becomes a surface across which the solution is discontinuous. Those are the
four choices below.

## Say where the fault is, then say how to model it

These are two separate decisions and the machinery keeps them separate. The
first is a statement about the Earth: here is my fault surface, sampled as a
polyline in two dimensions or a triangulated sheet in three, curved as it likes.
The second is a modelling choice: this surface is to become a slippery interface,
or a weak band of a stated width, or a direction of easy shear painted into the
rheology. The same surface supports all of them, and changing the choice does
not send the user back to their geometry.

That separation is also what makes the construction simple. The fault's own
discretisation builds the mesh that is added: the band's vertices are offsets of
the fault's own points, so there is no remesh and no search for where the fault
went. A mesh generator is still needed where faults meet and have to be merged
or cut, but it is not asked to invent the fault.

```{figure} figures/s_fault_geometry.png
The worked example. TODO alt text with the numbers.
```

The example throughout is San Andreas geometry in miniature: a tanh S-bend on
the diagonal with a San Jacinto-style through-line branch that stops short of
the bend. The fault line is also the terrane boundary, so the same rule that
paints the strong material draws the diagram — the scene-setting made concrete.
The drive is plate-motion shear, and its sign makes the bend restraining or
releasing.

## Four ways to model the same surface

| | the mesh must | the constitutive model must | width |
|---|---|---|---|
| weak ribbon | resolve the band | carry a weak isotropic viscosity | physics |
| TI ribbon | resolve the band | carry a director and two viscosities | physics |
| split nodes | conform, then split the mid-surface | nothing inside the fault | a convenience |
| TI, non-conforming | nothing | carry a director from the distance gradient | physics |

A paragraph each: what it is, what it asks of you, when to reach for it. Detail
goes to the notes that follow.

```{figure} figures/split-anatomy.png
The split: (a) the conforming chain; (b) exploded for display.
```

The tips are not duplicated, so slip tapers to zero there. That is the crack
condition, and it removes the special case at the front.

## The choice is not free, and the difference is measurable

```{figure} figures/sf_compare_split_ti.png
Split fine, TI coarse, TI fine on one colour scale. TODO alt text.
```

| representation | main | branch | ratio |
|---|---|---|---|
| split, coarse | 0.5368 | 0.2141 | 0.399 |
| split, fine | 0.5363 | 0.2146 | 0.400 |
| TI, coarse | 0.5771 | 0.2488 | 0.431 |
| TI, fine | 0.5358 | 0.2274 | 0.424 |

The split representation does not depend on the band width — 0.1% between the
two — so there w is a mesh convenience and this is the thin-fault reference. The
transversely isotropic band converges onto it from above as the width shrinks,
and too wide is a measured bias of about 8%. The shorter strand converges more
slowly, so a finite-width representation overweights the minor strands of a
network and tilts the slip partitioning toward them.

Which is the practical rule the rest of the series rests on: run a finite-width
model at two widths and judge it against the split reference.

Rig-scale throughout — 1 858 cells coarse, 2 940 fine, sub-second solves. These
are demonstrations of what the representations do, not converged geophysics.

## What the rest of the series covers

- Building the fault mesh: the band from the fault's own points, extents and
  paint honoured, junctions that stop short, resolution stacked on a static base,
  and where a mesh generator is still needed.
- Slippery interfaces: the pair transform, no-opening to machine precision, and
  interface laws on the trace.
- Solvers: a multigrid hierarchy on a stacked mesh.
- Parallel practice and tuning, with a California-scale example.
- Benchmarks against the published lithospheric-deformation solutions, by
  Thyagarajulu Gollapalli. Named here because it is part of the same series;
  nothing in these notes rests on it.

## Cautions to carry into the text

- The toolset is in development on `feature/fault-outcrop-3d-cap`; show usage,
  do not promise API stability.
- Contrast/viscosity-ladder numbers are solver stress tests, not geology.
- Tip-shape questions are parked; do not over-claim tip-zone physics.
- The dCFF reference is a welded solve; the gauge is demeaned pressure.
