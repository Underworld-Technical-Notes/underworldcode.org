---
title: Boundary conditions on non-planar boundaries
description: >-
  "No flow through this wall" is a single velocity component on a box and is
  not a component of anything on a sphere, a deformed mesh, or a surface with
  topography. Three ways to impose it — a direct penalty, Nitsche, and rotating
  the degrees of freedom — what each costs, and the one measurement that tells
  them apart.
date: 2026-08-18
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
    origin_url: https://www.underworldcode.org/boundary-conditions-on-non-planar-boundaries/
    template: ../../templates/pdf
    output: boundary-conditions-on-non-planar-boundaries.pdf
    article_id: UWTN 2026-016
    article_version: 1.0.0
    software_version: underworld3 development @ 0addec15
---
A free surface moves under the traction it carries. That makes the wall-normal
stress the quantity driving the model rather than something read off at the
end, and it is the reason we went back to how the boundary condition underneath
it is imposed.

The condition itself is ordinary. Free slip is no flow through the boundary and
no tangential drag along it,

$$
\mathbf{u}\cdot\hat{\mathbf{n}} = 0
\qquad\text{and}\qquad
\hat{\mathbf{t}}\cdot\boldsymbol{\sigma}\hat{\mathbf{n}} = 0 .
$$

On a box the first of those is a single velocity component. You hold $u_x$ on a
vertical wall, the solver removes a row, and there is nothing further to
discuss. On a sphere, an annulus, a mesh that has been moved, or a surface with
topography, $\mathbf{u}\cdot\hat{\mathbf{n}}$ is not a component of anything.
That is the whole difficulty, and everything below is a way around it.

The second condition is worth naming because it is the one people forget. Zero
tangential traction is *natural*: it is what you get by leaving the boundary
term out of the weak form. Nothing has to be done to impose it, and something
has to be done to avoid imposing it accidentally.

## Where the boundary term comes from

Every method below is a statement about one term. Multiplying the momentum
balance by a test function $\mathbf{w}$ and integrating by parts gives

$$
\int_\Omega \boldsymbol{\sigma} : \nabla\mathbf{w} \; \mathrm{d}V
- \int_{\partial\Omega} (\boldsymbol{\sigma}\hat{\mathbf{n}})\cdot\mathbf{w}
  \; \mathrm{d}S
= \int_\Omega \mathbf{f}\cdot\mathbf{w} \; \mathrm{d}V .
$$

Drop the surface integral and you have imposed zero traction in both
directions — free *everything*, not free slip. Free slip keeps the tangential
half of that and replaces the normal half with the constraint. How you do the
replacing is the choice.

## Three ways, in order

### A direct penalty

Add a term that punishes any flow through the boundary:

$$
\dots + \frac{\gamma}{h}\int_{\partial\Omega}
(\mathbf{u}\cdot\hat{\mathbf{n}})(\mathbf{w}\cdot\hat{\mathbf{n}})
\; \mathrm{d}S .
$$

One line, no new machinery, and it works on any geometry. What you are solving
is a perturbed problem, though, and it is perturbed by exactly the amount the
constraint is violated: the discrete solution sits where the penalty term
balances the traction it is fighting, which leaves $\mathbf{u}\cdot\hat{\mathbf{n}}$
small but not zero. Making it smaller means raising $\gamma$, and raising
$\gamma$ conditions the operator worse. The error is traded against the
conditioning, and neither can be driven away.

### Nitsche

The reason the penalty is only accurate in the limit is that it is not
*consistent*: substituting the true solution does not leave the equation
satisfied, because the true solution is subject to a boundary traction the
penalty form ignores. Nitsche's method [@10.1007/BF02995904] restores
consistency by carrying that traction explicitly:

$$
\dots
- \int_{\partial\Omega} (\hat{\mathbf{n}}\cdot\boldsymbol{\sigma}(\mathbf{u})
  \hat{\mathbf{n}})(\mathbf{w}\cdot\hat{\mathbf{n}}) \; \mathrm{d}S
- \int_{\partial\Omega} (\hat{\mathbf{n}}\cdot\boldsymbol{\sigma}(\mathbf{w})
  \hat{\mathbf{n}})(\mathbf{u}\cdot\hat{\mathbf{n}}) \; \mathrm{d}S
+ \frac{\gamma}{h}\int_{\partial\Omega}
  (\mathbf{u}\cdot\hat{\mathbf{n}})(\mathbf{w}\cdot\hat{\mathbf{n}})
  \; \mathrm{d}S .
$$

The first of the three is the consistency term: it is the boundary traction the
integration by parts produced, and putting it back is what makes the true
solution satisfy the discrete equations exactly. The second is its transpose,
which keeps the form symmetric and buys optimal convergence in $L^2$. The third
is the penalty again, and it is still needed — but now for *stability* rather
than for accuracy, and $\gamma$ has a threshold set by an inverse inequality
rather than being a dial you turn up until the answer looks right.

This is a real improvement and it is still a weak imposition. The constraint
holds to the accuracy of the discretisation, not to the accuracy of the
arithmetic — measured below, it leaks a few parts in a thousand on a mesh of
the resolution people actually run, and the leak falls with the mesh rather
than with the machine.

### Rotating the degrees of freedom

Stop asking for the constraint and impose it. At each constrained node, change
the basis in which the velocity unknowns are expressed, from the global
Cartesian frame to the local $(\hat{\mathbf{n}}, \hat{\mathbf{t}})$ frame. In
that basis "no flow through the boundary" is again a single component, and it
is removed the same way it would be on a box.

Collect the per-node rotations into a block-diagonal $Q$, equal to the identity
at every node that is not constrained. The rotated system is

$$
\hat{A} = Q^{T} A Q, \qquad \hat{\mathbf{b}} = Q^{T}\mathbf{b},
\qquad \mathbf{u} = Q\hat{\mathbf{u}} ,
$$

and the wall-normal row of $\hat{A}$ is struck out. The constraint then holds to
machine precision, because it is not being solved for at all.

**This is the classical answer**, not a new one. It is in the early
finite-element literature, and @10.1002/fld.1650020302 were already reviewing
the alternatives and choosing between them on grounds of global mass
conservation in 1982. What is worth explaining is not the idea but why, given
that it is exact and the others are not, it is the least used of the three.

## What it costs, and the cost is structural

Rotating the degrees of freedom leaves the discrete problem in a **mixed
basis**. Interior nodes hold $(u_x, u_y)$; constrained nodes hold
$(u_n, u_t)$. Nothing about that is difficult in itself, and everything
downstream has to agree about which nodes are which.

```{figure} figures/rotated-basis.svg
:alt: Two panels. On the left, a meshed domain bounded above by a free surface that rises on the left and falls on the right with an inflection between, so that the outward normal points in a different direction at every surface node. Surface nodes are drawn as filled circles each carrying its own rotated pair of arrows labelled n and t; interior nodes are open circles, with one carrying the unrotated x and y arrows shared by all of them. On the right, a block diagram. A red block labelled "Velocity solve, rotated" contains the rotated operator and right-hand side, and encloses a smaller block labelled "Multigrid" listing three rows: prolongation becomes Q-transpose P, coarse operators inherit Q through RAP, and the coarse solve uses SVD for the rigid rotations. A separate green block beside it, labelled "Fieldsplit / Schur solve", carries the pressure and constraints and is marked as never seeing a rotated vector. A single arrow labelled v equals Q v-hat leaves the velocity block at its boundary and branches, one branch entering the Schur block and the other leaving for output, advection and the surface update.

Where the rotation lives. The obligation is contained: the velocity solve is
rotated and carries its multigrid with it, while the Schur complement and the
pressure solve beside it never handle a rotated vector, because the pressure
block carries no boundary condition of this kind. One un-rotation sits on the
boundary between them and feeds both.
```

Four things carry $Q$: the operator, the right-hand side, the solution on the
way out, and the multigrid prolongation. The coarse operators inherit it
through the Galerkin triple product rather than being rotated separately, and
the coarse solve then has to be an SVD, because a Galerkin-coarsened rotated
operator inherits the rigid-rotation null space of the constrained problem and
a redundant LU factorisation meets a zero pivot in it.

That last point is worth dwelling on, because it is the one that surprises. The
constraint never has to be re-imposed on a coarse mesh — which is fortunate,
since we install no discretisation there and could not impose it if we wanted
to. It arrives anyway, algebraically, through $P^{T}\hat{A}P$ with a rotated
$P$. The evidence that it really arrives is that the coarse operator inherits
the null space, which is a property only the constrained problem has.

None of this is an argument against the method. It is an argument for knowing
what is being taken on, and it is the honest reason a weakly imposed condition
survives in codes that could do this instead.

## Which normal

A question with a less obvious answer than it looks. The boundary of a
discretised domain is a set of straight facets, and the assembled constraint is
an integral over those facets. The node normal consistent with that integral is
the average of the adjacent facet normals **weighted by facet measure** — not
the normal of the smooth surface the mesh approximates.

Using the analytic normal is exact for the geometry and therefore inconsistent
with the discretisation, which is the wrong way round: the solver is not solving
on the sphere, it is solving on the polyhedron. In parallel the same argument
has a sharper edge, because a normal accumulated rank-locally is wrong at a
partition boundary, where a node's facets are split across ranks and no rank
sees them all.

:::{note} Worth checking against the literature
@10.1002/fld.663 addresses this question directly for slip conditions on curved
boundaries. We have not read it against our own derivation. If it reaches the
same measure-weighted normal, this section should say so and cite it as the
source rather than presenting the result as ours.
:::

## The option this note leaves out

Solving in spherical or cylindrical components makes the wall-normal direction
a coordinate direction again, and the constraint returns to being "hold one
component". That is the same rotation as above, applied once for the whole
domain instead of node by node, and applied that way it costs nothing
structurally: there is no mixed basis, because every node is in the same basis.

It works exactly when the boundary lies along a coordinate surface. A sphere, an
annulus, a cylinder. It does nothing for topography, for a mesh that has been
deformed, or for a tilted internal surface, which is the general case this note
is about. The per-node rotation is what remains once the geometry stops
cooperating, and its structural price is what buys the generality.

## When the choice matters

Here is the awkward part. Solve a convection model with any of the three and
the velocity field is the same to plotting accuracy. A leak of order $10^{-3}$
in $\mathbf{u}\cdot\hat{\mathbf{n}}$ is invisible to anything that consumes the
velocity, and consuming the velocity is most of what a model does. If that is
your situation, use the simplest thing that works and stop reading here.

The difference appears when the wall-normal traction is the answer rather than
a by-product: dynamic topography, a plate-boundary force balance, anything
compared against a geoid or a gravity field. Then the three separate, and they
separate for a structural reason rather than by a matter of degree.

Under a penalty or a Nitsche condition the constraint is approximate, so a
traction recovered from the solution inherits the approximation — you are
differentiating a field that was never made to satisfy the condition exactly.
Under the rotated constraint the reaction *is* $\sigma_{nn}$: it is the
multiplier the solve has already computed, and it comes out of
`boundary_normal_traction` without a recovery step or an augmented-Lagrangian
splitting.

### The leak, measured

An annulus, no slip on the inner radius, the treatment under test on the outer,
driven by a degree-four radial density anomaly. The number is the largest
normal velocity on the outer boundary, taken against the true radial direction
and divided by the flow speed, so it reads as the fraction of the flow that
goes through a boundary nothing should pass through.

| cell size | Nitsche | rotated |
|---|---|---|
| 0.150 | 4.6 × 10⁻³ | 7.3 × 10⁻¹¹ |
| 0.100 | 2.2 × 10⁻³ | 6.5 × 10⁻¹¹ |
| 0.075 | 1.7 × 10⁻³ | 1.0 × 10⁻¹⁰ |
| 0.050 | 5.8 × 10⁻⁴ | 8.4 × 10⁻¹¹ |

The refinement is what separates them, and a single resolution would not have.
Nitsche's leak falls as about $h^{1.9}$ — it is limited by the discretisation,
which is what "consistent" buys and all that it buys. The rotated constraint
does not move: it is at the solver's floor at every resolution, because the
mesh has nothing to do with it.

The control matters here more than the result. With the outer boundary left
free, the same measurement reads **0.98** — nearly all the boundary flow is
normal — so the metric can see a leak when there is one.

:::{note} What is measured, and what is still inferred
Two honest limits. Underworld exposes no separate direct-penalty condition, so
the first row of the table above has no measured counterpart here; the argument
for it is the standard one and it is not ours to demonstrate.

And this measures the *constraint*, not the traction. That a traction recovered
from a constraint satisfied to $10^{-3}$ inherits that error, while the rotated
reaction is exact because it is the multiplier itself, follows from how each is
computed — but the surface-stress comparison against a known answer has not
been run, and until it is, the last two paragraphs of this section are
reasoning rather than measurement.
:::

## Using it

```python
import underworld3 as uw

mesh = uw.meshing.Annulus(radiusInner=0.5, radiusOuter=1.0, cellSize=0.05)
stokes = uw.systems.Stokes(mesh)

# Value first: 0 is free slip. A non-zero scalar or expression prescribes the
# wall-normal datum u.n = u_n strongly instead.
stokes.add_rotated_freeslip_bc(0.0, "Upper")
stokes.add_rotated_freeslip_bc(0.0, "Lower")

stokes.solve()

# The constraint reaction, which is the boundary normal traction.
sigma_nn = stokes.boundary_normal_traction("Upper")
```

Leave the normal to Underworld unless the constraint has to follow the true
surface rather than the mesh. Passing an analytic normal — `X / |X|` on a
sphere — is exact for the geometry and keeps a consistency error against the
faceted assembly, which is usually not what you want.

Reach for Nitsche when the boundary condition has to **change during the
model**. A hard constraint cannot morph: a wall that begins as a prescribed
velocity and relaxes to a prescribed traction is a Nitsche problem, because the
rotated constraint is either imposed or it is not.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=boundary-conditions-on-non-planar-boundaries">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=boundary-conditions-on-non-planar-boundaries">Start one</a></div></div>
