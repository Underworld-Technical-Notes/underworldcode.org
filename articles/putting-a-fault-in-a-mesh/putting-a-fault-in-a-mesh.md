---
title: "Faults: to mesh or not to mesh?"
description: >-
  A fault is a discontinuity and a mesh represents continuity, so the first
  question is whether the fault has to go into the mesh at all. Shear bands and
  a painted director cost no mesh work; cutting and conforming cost a great
  deal. What each of the four representations asks of the mesh and of the
  constitutive model, where they agree, and why they part company at a junction.
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
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/putting-a-fault-in-a-mesh/
    template: ../../templates/pdf
    output: putting-a-fault-in-a-mesh.pdf
    article_id: UWTN 2026-017
    article_version: 1.0.0
    software_version: underworld3 0.0.0
---

OUTLINE — not yet written.

Faults can dominate the dynamic behaviour of Earth systems at scales from the entire planet to a few 10s of metres. They are an extreme example of localisation: feedback between forcing and response that results in self-reinforcing weakening that does not have a brake at the largest scale. Faults are *extreme* in the sense that their natural length scale is orders of magnitude below that of a typical tectonic simulation.

At the tectonic scale fault is an infinitessimally thin surface across which the rock moves discontinuously. A finite element mesh is a machine for representing continuous fields. Putting the first into the second is work — cutting, conforming, refining, and doing it again every time the fault moves — so the first question is whether it has to be done at all.

## The fault you do not have to mesh

Often it does not. Localisation is something a rheology does on its own: give the material a yield stress or a strain-rate-weakening viscosity and shear bands appear where the stress finds them, at whatever width the physics and the mesh between them allow. Nobody places those bands, nobody meshes them, and they form, rotate and fade as the loading changes. For a model asking how deformation organises itself, that emergence is the answer to the question, and prescribing a fault would beg it.

The same is true of a fault you do want to prescribe. A direction of easy shear can be painted into the constitutive model as a field — a weak viscosity along a director taken from the gradient of the distance to a surface — and the mesh never learns that the fault is there. No cutting, no conforming, no remeshing when it migrates. The fault is a property of the material, not of the discretisation.

So the honest starting position is that meshing a fault is a cost you should have a reason to pay.

## Why that is not always enough

The reason is that a fault is not the same object as a shear band.

Localisation arises on its own wherever the rheology permits it. A shear band forms where the strain rate concentrates, it is as wide as the physics and the mesh between them allow, and it can fade when the loading that produced it changes. Faults behave differently in three ways that matter for how they are put into a model. They are long-lived, outlasting many changes in the flow around them. They localise far more sharply than any band a mantle-scale mesh resolves, down to a gouge zone of metres or less. And they are self-reinforcing: once a fault has accumulated slip it has juxtaposed rocks that were never neighbours, so its weakness belongs to the structure and to the material contrast across it rather than to the strain rate passing through it at this instant.

That is why a plate boundary enters a mantle model as prior knowledge. Ridges, transforms and megathrusts are prescribed, with their positions and their histories taken from observation, and a model that waits for them to emerge is answering a different question. Two consequences run through everything below. The feature needs resolution the domain cannot afford everywhere. And it moves — a rolling-back trench carries the thing that needs the resolution across the domain over tens of millions of years, so whatever the mesh does for the fault it has to do again, repeatedly, without degrading.

The width is the other consequence. No mantle-scale mesh reaches a metre, so every representation here is a sub-grid one: either the fault is given a width the mesh can carry and a rheology to go with it, or it is given no width at all and becomes a surface across which the solution is discontinuous.

TODO(LOUIS) — one paragraph to close the frame, and it is the note's thesis: what actually forces you up the ladder from a painted director to a cut mesh. Candidates, and they are not the same argument: the fault must slip freely rather than shear stiffly; the discontinuity must be sharp because something downstream reads the jump; the fault must carry an interface law of its own. Say which of these is the real trigger in your experience — that is the sentence a reader takes away.

## Say where the fault is, then say how to model it

These are two separate decisions and the machinery keeps them separate. The first is a statement about the Earth: here is my fault surface, sampled as a polyline in two dimensions or a triangulated sheet in three, curved as it likes. The second is a modelling choice: this surface is to become a slippery interface, or a weak band of a stated width, or a direction of easy shear painted into the rheology. The same surface supports all of them, and changing the choice does not send the user back to their geometry.

That separation is also what makes the construction simple. The fault's own discretisation builds the mesh that is added: the band's vertices are offsets of the fault's own points, so there is no remesh and no search for where the fault went. A mesh generator is still needed where faults meet and have to be merged or cut, but it is not asked to invent the fault.

```{figure} figures/s_fault_geometry.png
The worked example. TODO alt text with the numbers.
```

The example throughout is San Andreas geometry in miniature: a tanh S-bend on the diagonal with a San Jacinto-style through-line branch that stops short of the bend. The fault line is also the terrane boundary, so the same rule that paints the strong material draws the diagram — the scene-setting made concrete. The drive is plate-motion shear, and its sign makes the bend restraining or releasing.

## Four ways to model the same surface

| | the mesh must | the constitutive model must | width |
|---|---|---|---|
| weak ribbon | resolve the band | carry a weak isotropic viscosity | physics |
| TI ribbon | resolve the band | carry a director and two viscosities | physics |
| split nodes | conform, then split the mid-surface | nothing inside the fault | a convenience |
| TI, non-conforming | nothing | carry a director from the distance gradient | physics |

A paragraph each: what it is, what it asks of you, when to reach for it. Detail goes to the notes that follow.

```{figure} figures/split-anatomy.png
The split: (a) the conforming chain; (b) exploded for display.
```

The tips are not duplicated, so slip tapers to zero there. That is the crack condition, and it removes the special case at the front.

## They agree on a fault, and disagree at a junction

```{figure} figures/sf_compare_split_ti.png
Split fine, TI coarse, TI fine on one colour scale. TODO alt text.
```

Take one strand on its own, with no branch to complicate it, and the two representations converge. The split does not care about the band width — its peak slip rate moves by a tenth of a percent across a sixfold change — so there the width is a mesh convenience and the split is the thin-fault reference. The band approaches it from above as the width shrinks:

| Main strand alone, peak slip rate | w = 0.03 | w = 0.01 | w = 0.005 |
|---|---|---|---|
| split | 0.5149 | 0.5154 | 0.5152 |
| TI band, `eta_1/w` = 0.1 | — | 0.5232 | 0.5133 |
| TI band, `eta_1` = 1e-3 fixed | — | 0.5232 | 0.5000 |

The middle row converges; the bottom row overshoots. The difference between them is the whole of what a finite-width representation asks you to hold fixed. A band's mechanical strength is the ratio `eta_1/w`, not `eta_1`: halving the width at fixed viscosity doubles the interface strength and carries the answer past the split rather than towards it. Hold the ratio and the band goes from 1.5% above the cut to 0.4% below as the width halves, tracking the split's profile along the whole strand to within a couple of per cent.

Put a branch on it and that agreement stops, and not because of resolution. The junction is the one place where the two representations describe genuinely different objects. A band can fork: two weak zones meet and merge into one continuous weak region. Two cuts cannot — where they touch they would share a node, and a shared node is a pinned tip with no slip on it — so a cut network leaves an intact ligament at every junction, and that ligament is rock that carries load.

The consequence is measurable as a conservation statement. Along the main strand, slip steps up across the junction by what the branch takes in the opposite sense. In the band that budget closes: the step and the branch's slip sum to within a tenth of the step, at every ligament length and at the full join. In the cut it does not — the sum is 25 to 40% short, and the missing motion is deforming the ligament instead of slipping on either surface. Shrinking the ligament shrinks the shortfall, exactly as a smaller bridge should, and cannot take it to zero.

So the branch's slip near a junction is a property of the representation, at the twenty per cent level, and no amount of refinement closes it. The through-going strand, which is what a regional model is usually after, is untouched by all of it.

TODO(LOUIS) — the practical rule. The old draft said: run a finite-width model at two widths and judge it against the split reference. That still holds for a single fault, with `eta_1/w` held fixed rather than `eta_1`. What it should say about a NETWORK is the open question: whether to reach for the band because it conserves slip through junctions, or the cut because its ligament is arguably the more honest picture of a real fault intersection, or to bracket with both. This is a modelling judgement, not a measurement, and it belongs in your voice.

Rig-scale throughout — 1 858 cells coarse, 2 940 fine, sub-second solves. These are demonstrations of what the representations do, not converged geophysics.

## What the rest of the series covers

- Building the fault mesh: the band from the fault's own points, extents and paint honoured, junctions that stop short, resolution stacked on a static base, and where a mesh generator is still needed.
- Slippery interfaces: the pair transform, no-opening to machine precision, and interface laws on the trace.
- Solvers: a multigrid hierarchy on a stacked mesh.
- Parallel practice and tuning, with a California-scale example.
- Benchmarks against the published lithospheric-deformation solutions, by Thyagarajulu Gollapalli. Named here because it is part of the same series; nothing in these notes rests on it.

## Cautions to carry into the text

- The toolset is in development on `feature/fault-outcrop-3d-cap`; show usage, do not promise API stability.
- Contrast/viscosity-ladder numbers are solver stress tests, not geology.
- Tip-shape questions are parked; do not over-claim tip-zone physics.
- The dCFF reference is a welded solve; the gauge is demeaned pressure.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=putting-a-fault-in-a-mesh">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=putting-a-fault-in-a-mesh">Start one</a></div></div>
