---
title: "Faults: to mesh or not to mesh?"
description: >-
  A fault is a discontinuity and a mesh represents continuity, so the first
  question is whether the fault has to go into the mesh at all. Shear bands and
  a painted director cost no mesh work; cutting and conforming cost a great
  deal. What each of the four representations asks of the mesh and of the
  constitutive model, where they agree, and why they part company at a junction.
date: 2026-09-18
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
  - name: Thyagarajulu Gollapalli
    orcid: 0000-0001-9394-4104
    affiliations:
      - Australian National University
license: CC-BY-4.0
bibliography:
  - references.bib
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
Faults can dominate the dynamic behaviour of Earth systems at scales from the entire planet to a few 10s of metres. They are an extreme example of localisation: feedback between forcing and response that results in self-reinforcing weakening that does not have a brake at the largest scale. Faults are *extreme* in the sense that their natural thickness is orders of magnitude below that of a typical tectonic simulation.

At the tectonic scale, a fault is an infinitesimally thin surface across which the rock moves discontinuously by overcoming a frictional resistance. A finite element mesh (the mesh we use in Underworld) is a mechanism for representing continuous fields and there is not a native mechanism that perfectly represents a fault. 

There are lots of different potential solutions to this difficulty. They include: 1) ignoring it by using a continuum model of the fault, 2) adding extra interpolation functions that represent discontinuities, 3) splitting the mesh along the line of the fault and dealing with it as a surface, 4) refining the mesh enough that the fault width is invisibly small at the model length scale.  


## Faults in numerical models 

Localisation is something a rheological law produces all by itself: if we give the material a yield stress or a strain-rate-weakening viscosity, shear bands appear where the stress requires them, with an orientation determined by the stress, and at whatever width the physics and the mesh between them allow. Do we really need to do anything more than this to represent faults ? The answer is yes and there are two main reasons. 

First, a fault is not in the same category as a shear band or a damage-zone. At the lithospheric scale a fault is persistent through changes in the tectonic loading.  Faults localise far more sharply than any band a lithosphere-scale mesh resolves, down to a gouge zone of metres or even less. They are self-reinforcing: once a fault has accumulated slip it has juxtaposed distinct rock units; the weakness becomes structural and persistent even when the load is absent. Faults have history.

Second, conceptually, at the tectonic scale fault is an infinitesimally thin surface across which the rock moves discontinuously by overcoming a frictional resistance. A finite element mesh (the mesh we use in Underworld) is a mechanism for representing continuous fields and there is not a native mechanism that perfectly represents a fault. Faults are sub-grid objects with their own constitutive properties. 

That is why it is common to impose plate boundaries in a mantle model as prior knowledge [@Davies_1988], and why those plate boundaries often have additional evolution rules. 

It is also why crustal models of stress build-up and release always try to include known faults. They are very fine-scale structures, they reflect complex geological history and they are not simply emergent from the imposed loading. 


## Describe the fault not the implementation

The fault geometry and its numerical representation ought to be decoupled as far as possible. 
It is the thesis of both @Zhong_1995 and @Sandiford_2019: what the fault surface is, and what the solver is asked to do with it, are distinct choices. The first is a statement about the Earth: this is the fault surface, sampled as a polyline in two dimensions or a triangulated sheet in three, curved as it likes. The second is a modelling choice: this surface is to become a slippery interface, or a weak band of a stated width, or a direction of easy shear painted into the rheology. The same surface supports all of them and is agnostic to the implementation.


```{figure} figures/s_fault_geometry.png
:width: 60%
:name: fig-s-fault-geometry
:alt: A square domain with a red fault trace running from lower left to upper right, gently S-bent in the middle, drawn inside a pale blue ribbon labelled w = 0.03 and annotated main (tanh S); the trace continues as a red dashed line out of each corner, and the whole region above and left of it is shaded beige and labelled STRONG (eta x contrast) against a white region below and right. Beyond the main trace's upper tip a short collinear segment carries on in its own ribbon, labelled main segment (stepover) gap = 0.010. Just past the bend, three short parallel strands in pale green ribbons climb away into the beige region at a shallow angle to the main trace, labelled splay (kissing) + en-echelon zone; the lowest of the three almost touches the main trace, labelled Y gap = 0.010, and the other two are stepped up and to the left of it. To the right of the bend a straight dark red trace in its own blue ribbon, labelled branch (through-line), runs parallel to the strike and stops short of the main trace, marked gap = 0.071. Near the lower tip a short segment parallel to the main trace sits just below it in the white region, labelled lower stepover (offset 0.035). Every trace ends in a black dot. Two black arrows, one in each half of the domain, point up-right and down-left.

A synthetic fault network that we use to validate the different fault algorithms.
```

[](#fig-s-fault-geometry) shows a synthetic fault network for our 2D and 3D experiments. The network is described by a number of independently meshed vertical segments in 3D and their surface traces for 2D models. It has a number of characteristics designed to test the fault implementation: multiple faults in a single domain; curved faults; junctions; steps and segment breaks for a single fault. There is a material property jump across the main fault in this network. The system is driven by boundary shear. 


## Three implementations

There is no perfect choice in how we model a fault in a geodynamic context and that means keeping several possible choices on hand to see which one works best for a specific problem. 
Underworld3 offers three: a weak zone, a weak zone with a direction, and a cut. Each of them can be built on the unstructured mesh, or on a mesh modified to conform to the fault.

| | Mesh untouched | Mesh conforms to the fault |
|---|---|---|
| Weak zone | painted band — the mesh sets the width | ribbon — the width is prescribed |
| TI weak zone | painted, director from the distance gradient | TI ribbon — the width is prescribed |
| Cut | XFEM: enrichment functions carry the jump through the elements (not in Underworld) | split nodes with additional degrees of freedom |

The **non-conforming, transversely isotropic (TI)** rheology requires no changes to the mesh to represent the mechanics of the fault. It simply creates a near-fault band of material that has a lower frictional strength parallel to the fault. There is a zone of weakness that depends on the perpendicular distance to the *fault object*, and the internal orientation is given by the perpendicular vector to the fault surface. The band is whichever cells fall within $w/2$ of the fault, so its width is set by the mesh as much as by $w$. The resulting zone of weakness crosses element boundaries and can produce anomalous stress concentrations along the fault. These are mitigated at the large scale by refining the triangulation and smoothing the fault's influence function but they never disappear [@Yang_2021]. This is the representation of @Sharples_2015 and of @Sandiford_2019.

Material property jumps can be incorporated into finite element representations when they lie along element boundaries. It is therefore possible to represent a fault as a rheologically distinct volume if we are prepared to remesh. The **weak ribbon** is a band of width $w$ meshed along the fault trace — its vertices are the fault's own points offset by $w/2$ either side — with a contrasting rheology in that region (a weak zone, or a zone with its own plasticity coefficients). For this we do need the ability to remesh so it is more difficult to implement in models where the fault system evolves. In this model, the fault, as a volume under normal stress, can deform internally and violate the frictional surface *approximation*. This is primarily an issue when $w$ is significantly larger than the fault's true physical width.

The latter problem can be alleviated by combining the first two approaches. A **TI ribbon** is the same band but using the transversely isotropic frictional model of @Moresi_2006 within the remeshed band: the same rheology as the non-conforming case, with the remesh taking control of the width. This has the same desirable properties from the finite element solver's point of view as the weak band model, but it can transmit normal stresses across the fault without internal flow.  


The **split** algorithm is the one that embraces the notion of the fault as an embedded surface. It produces a cut through the mesh to create a new internal surface boundary. In general this is also a remeshing step: the mesh is cut along the fault line, dividing the elements it crosses, and degrees of freedom are added along the cut; @Zhong_1995 put slippery nodes into a convection model this way, on a hexahedral grid nudged towards the fault. We make the mesh conform to the fault beforehand, so that what remains is the duplication alone. Faults are surfaces that conform to element boundaries but they are implemented as pairs of surfaces to represent the two sides of the fault. The constitutive model lies in the interaction of these two coincident surfaces. This is a good choice of model when the physical scale completely precludes resolving $w$, but there are some limitations: because the mesh is cut into sliding surfaces, there are incompatible constraints when two faults meet or cross. 


```{figure} figures/fault-anatomy.png
:width: 72%
:name: fig-fault-anatomy
:alt: Three panels, each the same rectangular triangulation twelve cells across and four deep, pale grey, stacked vertically. (a) The grid is flat and a red arch is drawn across the middle two thirds without dots, cutting through the triangles; the tinted green cells form a ragged band around it, two rows deep on the flanks and three at the crest, with a saw-toothed outline, each with a short dark-green stroke tilted perpendicular to the arch. (b) The grid is gently bowed upward in its middle rows so that the same red arch, now with nine dots, runs along mesh edges; the cells immediately above and below it are tinted green, each with a stroke perpendicular to the local trace; a bracket at the right marks the two-cell band height as w. (c) The bowed grid again, with the row of cells above the arch tinted pale blue and the row below pale pink; the pink block has dropped, so the red line has opened into two — a solid upper arch with seven filled dots labelled v-plus (original) and Gamma-plus, and a dashed lower arch with open circles labelled v-minus (replica) and Gamma-minus — still meeting at a black ringed vertex labelled tip at each end, with the cells at the two ends sheared where the block has dropped.

One fault, three strategies, on one mesh. (a) The non-conforming paint: the trace across the flat grid, and the band is whichever cells fall within $w/2$ of it. (b) The ribbon: the mesh is bent so that the same trace runs along element edges, and the band is the cells either side of it, each carrying a director; nothing is duplicated and every field is continuous. (c) The split, on the bent mesh: each interior vertex of the chain is duplicated and the cells on the Minus side are rewired to the replica; the tips are not duplicated. The copies are coincident — the lower block is pulled away only so that they can be seen.
```

[](#fig-fault-anatomy) compares the three strategies on one mesh. Panel (a) shows the fault running through the mesh with elements identified as fault / not-fault depending on their centroid distance to the fault. Panel (b) shows the ribbon near the fault constructed so that the fault volume itself is defined by element boundaries.  Panel (c) is what the split does. The trace has first been made a chain of element edges, so that the two cells at every facet share it and every field is continuous across it, as anywhere else in the mesh. The split then duplicates each interior vertex of the chain. The original stays with the cells on one side, which we label Plus; the cells on the other side, Minus, are rewired to a replica at the same position. In this simple example, no elements are added or divided, but, across the fault, the two sides no longer share a degree of freedom, so the velocity is free to jump.

The fault is just the pair of surfaces and the condition we impose between each vertex and its replica. The simplest condition is no-opening: the two normal velocities of a pair are equal and the tangential velocities are free, which is a frictionless slippery interface. The slip rate is read off the pair as the tangential jump. A friction law is a relation between that jump and the traction the pair carries, and it lives on the pair as well.

The two end vertices of the chain are not duplicated. Slip therefore goes to zero at the tips, which is the crack condition, and the front of the fault needs no treatment of its own. This is also a limitation: a vertex that belonged to two chains would be a tip of each, pinned on both, so two cuts cannot meet.

## Difficulties with branching faults

```{figure} figures/sf_note_stress_slip.png
:width: 64%
:name: fig-stress-and-slip
:alt: A three-by-two grid of panels; the left column is the cut, the right the band, both at w = 0.005. The top row shows the whole square domain coloured by log10 of the second stress invariant on a black-purple-orange-white scale from -1.18 to 0.99: a flat mid-orange background, a dark low-stress lobe flanking each trace, and a bright concentration at every tip. Each trace is a tube coloured by its signed slip rate on a blue-grey-green scale, blue sinistral down to -0.029 and green dextral up to 0.54: the S-bent main trace is dark green, the branch and the lower stepover segment mid green, the three en-echelon strands pale, and the splay nearest the main carries a short blue reach where it meets it. The two columns look the same at this scale. The middle row zooms the Y junction with the mesh in faint white: in the cut the splay's tube stops a short distance from the main trace and the stress there is smooth; in the band it runs into the main trace and the two merge, with a bright knot at the join and dark lobes either side. The bottom row zooms the upper stepover, where the main trace ends and a collinear segment carries on one element beyond it. In the cut, a bright four-lobed stress concentration sits on the one-element bridge between the two tips, the continuation segment's tube is noticeably paler than the main trace's, and a dark lobe lies along its far side. In the band, one green tube runs straight through with no break and no change of shade, a narrow dark band runs along it, and there is no concentration at the old tip at all — only a single dark speck on the line where the two tips were.

The same network as a cut (left) and as a band (right), both at w = 0.005 with `eta_1/w` = 0.1. Background: log10 of the second stress invariant on one scale. Traces: each representation's own slip rate. Below, the Y junction, and the collinear stepover closed to one element — the least gap a cut can leave.
```

Consider one un-branched strand by itself. If we look at the slip rate across the fault for the transversely isotropic ribbon and compare it to the split mesh, we find that the two representations converge as the fault ribbon shrinks in width (in a background mesh of fixed resolution), provided the ratio $\eta_1/w$ remains fixed. The band's mechanical strength is the ratio `eta_1/w`, not `eta_1`: halving the width at fixed viscosity effectively doubles the interface strength (see table).

| Main strand alone, peak slip rate | w = 0.03 | w = 0.01 | w = 0.005 |
|---|---|---|---|
| split | 0.5149 | 0.5154 | 0.5152 |
| TI band, `eta_1/w` = 0.1 | — | 0.5232 | 0.5133 |
| TI band, `eta_1` = 1e-3 fixed | — | 0.5232 | 0.5000 |


Branching of the fault breaks this convergence because a junction is the one place where the two representations describe genuinely different objects. A band can fork: two weak zones meet and merge into one continuous weak region. Two cuts cannot: if they touch they would share a node that would carry two incompatible sets of constraints. The branch in the model is therefore represented slightly differently. The rheological bands merge smoothly in the mesh, but the cut branch stops short of the main fault. 

The band's junction is not free of choices either: in the cells the two bands share there can be only one director, and it is the orientation of whichever band was painted last.

Where the branches touch, slip is significantly higher, with a noticeable reversal of polarity in the slip orientation along the branch. The effect is present but more muted for the cut-in branch that does not quite reach the main fault. 


## Choices 

The split-node approach is by far the most efficient representation of a discontinuous, frictional fault that works well when the fault-width is completely unreachable with meshing. It does require cutting into the mesh each time the mesh is adapted or the fault is moved. The surface conditions are well-behaved when the solver sees them. 

The transversely isotropic, meshed ribbon does a good job of faults that have branching structures or multiple, overlapping segments (or even segments that butt against each other). It requires mesh adaptation to keep the solver happy, and there is some tuning required to ensure the implementation converges to the split-node formulation. 

The non-conforming transversely isotropic fault representation trades fault fidelity and solver efficiency against simplicity. This is the choice for cases where remeshing or mesh adaptation is difficult, and fluctuations in the near-fault stress-field can be tolerated. 

<!--
## What the rest of the series covers

- Building the fault mesh: the band from the fault's own points, extents and paint honoured, junctions that stop short, resolution stacked on a static base, and where a mesh generator is still needed.
- Slippery interfaces: the pair transform, no-opening to machine precision, and interface laws on the trace.
- Solvers: a multigrid hierarchy on a stacked mesh.
- Parallel practice and tuning, with a California-scale example.
- Benchmarks against the published lithospheric-deformation solutions, by Thyagarajulu Gollapalli. Named here because it is part of the same series; nothing in these notes rests on it.-->

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=putting-a-fault-in-a-mesh">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=putting-a-fault-in-a-mesh">Start one</a></div></div>
