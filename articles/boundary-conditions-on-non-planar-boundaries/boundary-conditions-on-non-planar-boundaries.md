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
    software_version: underworld3 development @ 8b7c8b9e
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

## Four ways, in order

### A direct penalty

Add a term that punishes any flow through the boundary:

$$
\dots + \frac{\gamma}{h}\int_{\partial\Omega}
(\mathbf{u}\cdot\hat{\mathbf{n}})(\mathbf{w}\cdot\hat{\mathbf{n}})
\; \mathrm{d}S .
$$

One line, no new machinery, and it works on any geometry. It is still in a
good many working scripts, and deservedly. What you are solving is a perturbed
problem, though, and it is perturbed by exactly the amount the constraint is
violated: the discrete solution sits where the penalty term balances the
traction it is fighting, which leaves $\mathbf{u}\cdot\hat{\mathbf{n}}$ small
but not zero. Making it smaller means pushing harder, and pushing harder
conditions the operator worse. The error is traded against the conditioning,
and measured below, that trade runs out: past $10^4$ the leak stops improving,
and by $10^6$ the solve fails. Nitsche moves the floor down rather than
removing it — it fails too, at its own threshold.

Underworld spells it as a boundary traction opposing normal flow, using the
facet normal at the quadrature points:

```python
G = mesh.Gamma
stokes.add_natural_bc(1.0e4 * G.dot(v.sym) * G, "Upper")
```

### Nitsche

The reason the penalty is only accurate in the limit is that it is not
*consistent*: substituting the true solution does not leave the equation
satisfied, because the true solution is subject to a boundary traction the
penalty form ignores. Nitsche's method [@Nitsche_1971] restores
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

### A constraint equation, with a multiplier

The two above add a *term* to an equation. This one adds an *equation*.

Carry a scalar field $h$ on the boundary and require, as a row of the system in
its own right,

$$
\int_{\partial\Omega} (\mathbf{u}\cdot\hat{\mathbf{n}} - g)\, q
\; \mathrm{d}S = 0 \quad \text{for all } q ,
$$

with $h$ entering the momentum row as the traction $h\hat{\mathbf{n}}$ that holds
the constraint. It is a Lagrange multiplier, and the system becomes a larger
saddle point: velocity, pressure, and now $h$.

The constraint row is exact, so unlike a penalty there is no parameter whose
size decides how well it holds. Two practical things do have to be dealt with.

- $h$ is carried as a full-domain field but only its boundary trace means
  anything, so the interior degrees of freedom are constrained out of the global
  system in the section before the solve sees it. They are not solved for and
  they do not enlarge the $[p, h]$ block. The interior rows are the screening
  block alone, so the interior multiplier is determined by the boundary trace and
  carries no independent signal.
- The $[p, h]$ Schur complement is poorly conditioned on its own, so an
  augmented-Lagrangian term $r(\mathbf{u}\cdot\hat{\mathbf{n}} - g)\hat{\mathbf{n}}$
  is added to the momentum row. It does not change what the constraint enforces,
  because the $h$ row still carries the exact constraint. It does change what $h$
  *is*, which is the subject of a section below.

```python
stokes = uw.systems.Stokes_Constrained(mesh, velocityField=v, pressureField=p)
h = stokes.add_constraint_bc(0.0, "Upper")
stokes.solve()
```

And the reason to care about it beyond the constraint: **at convergence the
momentum row's boundary term is the normal traction.** It is not recovered from
the velocity field afterwards — it is an unknown the solve returned, available
through `multiplier` and, divided by $\Delta\rho g$, through `topography`. With
an augmentation in place that term is $h + r(\mathbf{u}\cdot\hat{\mathbf{n}} - g)$
rather than $h$, and the difference between the two is measured below.

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
finite-element literature, and @Engelman_1982 were already reviewing
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

A question with a less obvious answer than it looks, and the measurements
further down say it is the most consequential choice in the note. The boundary of a
discretised domain is a set of straight facets, and the assembled constraint is
an integral over those facets. The node normal consistent with that integral is
the average of the adjacent facet normals **weighted by facet measure** — not
the normal of the smooth surface the mesh approximates, and not the facet
normal on its own.

**This is the consistent normal of @10.1002/fld.1650020302**, and we should say
so plainly: we re-derived it from the assembled boundary integral, and Engelman,
Sani and Gresho derived it in 1982 from global conservation of mass, which is
the same object arrived at from the other side. Their paper is about exactly
this — how to impose a normal or tangential condition on a boundary that does
not line up with the coordinate directions — and the recommendation is the one
here.

Using the analytic normal is exact for the geometry and therefore inconsistent
with the discretisation, which is the wrong way round: the solver is not solving
on the sphere, it is solving on the polyhedron. Using the facet normal is
consistent with each facet separately and over-constrains the nodes between
them, which is the failure measured in "A constraint that is satisfied, and
wrong" below. In parallel the same argument has a
sharper edge, because a normal accumulated rank-locally is wrong at a partition
boundary, where a node's facets are split across ranks and no rank sees them
all.

The consistent normal is not the end of the matter. @Behr_2004 takes it as
the starting point — "preferred from the point of view of conservation" — and
reports that in sloshing problems it still does not guarantee a good discrete
slip condition, with non-physical recirculation appearing at curved walls; the
remedies offered there are the Navier slip condition and a "BC-free" boundary.
We have read the abstract rather than the paper, and have not looked for that
recirculation in our own cases. It is the obvious thing to test next for anyone
running free slip on a strongly curved wall.

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

Here is the awkward part. Solve a convection model with any of these and the
velocity field is the same to plotting accuracy, as long as each is set up
properly. A leak of order $10^{-3}$ in $\mathbf{u}\cdot\hat{\mathbf{n}}$ is
invisible to anything that consumes the velocity, and consuming the velocity is
most of what a model does. If that is your situation, use the simplest thing
that works — and read the section on which normal before you do, because that
is the choice that can spoil the velocity as well.

The difference appears when the wall-normal traction is the answer rather than
a by-product: dynamic topography, a plate-boundary force balance, anything
compared against a geoid or a gravity field. That is what the two sections after
the leak measure, against an exact surface stress, and the answer is not the one
we expected. The treatments that impose the constraint properly all recover the
same surface stress at a given mesh, because the recovery sets the floor rather
than the boundary condition; what the rotated constraint buys is a route to the
traction that does not go through a recovery at all, and it is three times
better on the same solve.

Under the rotated constraint the reaction *is* $\sigma_{nn}$: it is the
multiplier the solve has already computed, and it comes out of
`boundary_normal_traction` without differentiating the answer.

### The leak, measured

An annulus, no slip on the inner radius, the treatment under test on the outer,
driven by a degree-four radial density anomaly. The number is the largest
normal velocity on the outer boundary, taken against the true radial direction
and divided by the flow speed: the fraction of the flow going through a
boundary nothing should pass through. Penalty at $10^4$, Nitsche at
$\gamma = 10$.

The penalty appears twice, because the normal it is written against turns out
to matter more than the method it is written into. One column uses the
quadrature-point facet normal `mesh.Gamma`, which is the documented form; the
other uses the measure-weighted node normal `mesh.boundary_normal`, which is
what Nitsche and the rotated constraint use by default.

| cell size | penalty, facet normal | penalty, node normal | Nitsche | multiplier | rotated |
|---|---|---|---|---|---|
| 0.150 | 4.5 × 10⁻³ | 3.3 × 10⁻³ | 4.6 × 10⁻³ | 8.3 × 10⁻⁴ | 7.3 × 10⁻¹¹ |
| 0.100 | 2.5 × 10⁻³ | 2.7 × 10⁻³ | 2.2 × 10⁻³ | 1.6 × 10⁻⁴ | 6.5 × 10⁻¹¹ |
| 0.075 | 8.5 × 10⁻⁴ | 2.6 × 10⁻³ | 1.7 × 10⁻³ | 5.6 × 10⁻⁵ | 1.0 × 10⁻¹⁰ |
| 0.050 | 9.5 × 10⁻⁴ | 2.6 × 10⁻³ | 5.8 × 10⁻⁴ | 1.2 × 10⁻⁵ | 8.4 × 10⁻¹¹ |

Nitsche leaks parts in a thousand and improves roughly as $h^{1.9}$ — the rate
consistency buys. The multiplier starts an order of magnitude better and falls
much faster, near $h^{3.9}$, because the constraint row is an equation rather
than a term whose weight has to be chosen.
The rotated constraint does not move at all: it sits at the solver's floor at
every resolution, because the mesh has nothing to do with it. The penalty
against the node normal does not improve with the mesh either, and for the
opposite reason: at a fixed coefficient its leak is set by the coefficient.

The control matters more than the result. With the outer boundary left free the
same measurement reads **0.98** — nearly all the boundary flow is normal — so
the metric can see a leak when there is one.

The first column is the one to be careful with. Its leak falls with the mesh,
which reads as the method working, and it is not: the surface stress measured
further down says that solve is 60% wrong in the velocity and 26% wrong in the
stress, and refining it does not help. The leak is small because the boundary
is being frozen. A metric that only asks whether the constraint is satisfied
cannot tell those apart.

### What each parameter buys

The two weak methods look alike in that table. They are not alike, and their
own parameters are what tells them apart.

| penalty, facet | leak | | penalty, node | leak | | $\gamma$ (Nitsche) | leak |
|---|---|---|---|---|---|---|---|
| 10² | 2.6 × 10⁻¹ | | 10² | 2.6 × 10⁻¹ | | 1 | diverged |
| 10³ | 2.3 × 10⁻² | | 10³ | 2.6 × 10⁻² | | 10 | 1.7 × 10⁻³ |
| 10⁴ | 8.5 × 10⁻⁴ | | 10⁴ | 2.6 × 10⁻³ | | 100 | 2.7 × 10⁻⁴ |
| 10⁵ | 9.6 × 10⁻⁴ | | 10⁵ | 3.0 × 10⁻⁴ | | 1000 | 3.0 × 10⁻⁵ |
| 10⁶ | diverged | | 10⁶ | 4.5 × 10⁻⁵ | | 10⁴ and above | diverged |

Nitsche is bounded at both ends. Below $\gamma = 1$ the form is no longer
coercive and no amount of tuning recovers it; from $\gamma = 10^4$ in this
problem the line search stops converging. The virtue of $\gamma = 10$ is that it
sits in the middle of that window on any mesh, because $\gamma$ is dimensionless
and the term it scales already carries $\mu / h$. The penalty coefficient
carries no such scaling, which is why the value that works is a property of the
problem rather than a default — and, on the second half of this note's test, of
the local viscosity as well.

The two penalty columns are the same method against different normals, and they
behave differently in a way the leak alone does not explain. Against the node
normal the leak keeps falling, a decade of coefficient for a decade of leak, all
the way to $10^6$. Against the facet normal it stops improving after $10^4$ and
the solve fails at $10^6$. That looks like the conditioning wall a penalty is
expected to have. It is not: what stalls is the leak, because by $10^4$ the
boundary is nearly frozen and there is little normal flow left to remove. The
stress section below measures the same runs against an exact answer, and they
are getting worse throughout.

### The stress, measured

The leak says how well each treatment holds the boundary. Whether the answer is
right is a different question, and it needs an exact answer to compare against.

Kramer, Davies and Wilson [@Kramer_2021] give exact Stokes
solutions in a cylindrical annulus, and their `assess` package publishes the
radial stress itself rather than leaving it to be recovered from a velocity
field. Underworld wraps it as `uw.analytic.CylindricalStokes`. The case here is
the smooth one: a density anomaly $(r/r_o)^k \cos n\theta$ with $n = 2$ and
$k = 3$, viscosity 1, free slip on both radii. On the outer boundary the exact
radial stress is a single harmonic,

$$
\sigma_{rr}(r_o, \theta) = 0.1506696\,\cos 2\theta ,
$$

fitted to a residual of $10^{-16}$, so the whole of the surface stress is that
one amplitude and the metric is its relative error.

The inner boundary carries the exact velocity as a Dirichlet condition instead
of a free-slip treatment of its own. The exact solution satisfies both, so the
problem is unchanged, and the treatment under test is then the only free-slip
condition in the model.

There are two routes to the surface stress and the difference between them is
the point of the section:

- **recovered** — project $\hat{\mathbf{n}}\cdot\boldsymbol{\sigma}\hat{\mathbf{n}}$
  out of the solved velocity and pressure. Every treatment can do this, and it
  is the only route the weak ones have.
- **reaction** — `boundary_normal_traction` for the rotated constraint, and the
  multiplier field for the constraint method. Not recovered from the solution:
  an unknown the solve returned.

Both are taken against the true radial direction, which is also the direction
the oracle publishes, so no treatment is scored against its own normal. The
reaction and the multiplier come back with the opposite sign to $\sigma_{rr}$ —
they are the traction holding the boundary rather than the traction the fluid
exerts, and `dynamic_topography` carries the sign back — so amplitudes are
compared unsigned.

| cell size | penalty, facet | penalty, node | Nitsche | constraint | rotated | rotated, reaction | multiplier field |
|---|---|---|---|---|---|---|---|
| 0.150 | 1.5 × 10⁻¹ | 2.5 × 10⁻² | 5.9 × 10⁻² | 2.4 × 10⁻² | 2.4 × 10⁻² | 6.8 × 10⁻³ | 8.6 × 10⁻³ |
| 0.100 | 1.3 × 10⁻¹ | 1.1 × 10⁻² | 2.4 × 10⁻² | 1.0 × 10⁻² | 1.0 × 10⁻² | 3.3 × 10⁻³ | 8.5 × 10⁻⁴ |
| 0.075 | 1.1 × 10⁻¹ | 7.2 × 10⁻³ | 1.5 × 10⁻² | 6.3 × 10⁻³ | 6.2 × 10⁻³ | 2.1 × 10⁻³ | 1.7 × 10⁻³ |
| 0.050 | 6.3 × 10⁻² | 3.6 × 10⁻³ | 6.3 × 10⁻³ | 2.7 × 10⁻³ | 2.7 × 10⁻³ | 1.1 × 10⁻³ | 1.4 × 10⁻³ |

The first five columns are all the recovered stress, so they differ only by
which boundary condition produced the field. The last two are the reaction and
the multiplier on the same solves. Penalties at $10^4$, Nitsche at
$\gamma = 10$, which are the values the leak table used. With the outer
boundary left free the same measurement reads 1.0 — the surface stress is
gone — so the metric can see the condition being removed.

**Once the constraint is imposed against the node normal, which treatment
imposed it stops mattering to the recovered stress.** At cell 0.075 the rotated
constraint gives 6.2 × 10⁻³, the multiplier 6.3 × 10⁻³, the penalty at $10^5$
6.3 × 10⁻³ and Nitsche at $\gamma = 100$ 6.6 × 10⁻³. Those are the same number.
What sets it is the recovery — a projection of a stress differentiated out of a
piecewise-quadratic velocity — and not the boundary condition underneath. The
reasoning this note began with — that a traction recovered from an approximate
constraint inherits the approximation — is not what the measurement shows once
the constraint is written against the right normal. It shows a floor that all of
them share.

**The reaction is about three times better than the recovery, on the same
solve.** 2.1 × 10⁻³ against 6.2 × 10⁻³ at cell 0.075, and it converges at the
same rate rather than a better one. It costs nothing — it is the residual the
solve has already assembled, and no field is differentiated to get it — and the
timings below put a number on "nothing".

The multiplier's traction is the same story from the other side, and lands in the
same place: 8.5 × 10⁻⁴ to 1.7 × 10⁻³ over the three finer meshes. Its column does
not fall smoothly with $h$, because part of what it reports is the augmentation
times the constraint residual, and how far a particular solve drove that residual
is not a function of the mesh.

**The parameter that was enough for the leak is not enough for the stress.**
Nitsche at $\gamma = 10$ leaks 1.2 × 10⁻³ in this problem and gets the stress
amplitude 1.5% wrong. At $\gamma = 100$ the leak improves by a factor of nearly
forty and the stress by a factor of two, to the recovery floor, where more
$\gamma$ buys nothing. Reading the leak alone would have said $\gamma = 10$ was
converged.

### A constraint that is satisfied, and wrong

The facet-normal penalty column does not converge. That is not a slow rate; the
error grows slightly as the mesh is refined, and the leak is excellent
throughout.

| cell size | leak | velocity error | stress error |
|---|---|---|---|
| 0.150 | 8.9 × 10⁻⁶ | 0.60 | 0.21 |
| 0.100 | 8.2 × 10⁻⁶ | 0.61 | 0.24 |
| 0.075 | 1.1 × 10⁻⁵ | 0.61 | 0.25 |
| 0.050 | 1.9 × 10⁻⁵ | 0.60 | 0.26 |
| 0.035 | 2.3 × 10⁻⁵ | 0.59 | 0.26 |

```{figure} figures/locking.png
:alt: Three annuli side by side on one colour scale from zero to 5.0e-3, blue for slow and red for fast, with the triangular mesh drawn over each. The left panel is the exact solution: two deep red patches of fast flow sit against the outer boundary on the left and right of the annulus, with a blue slow ring inside them. The middle panel is the same problem solved with a direct penalty against the facet normal: the red patches at the outer boundary are gone and the whole outer half is blue, the peak speed having fallen from 5.0e-3 to 3.8e-3, while a pale ring survives near the inner boundary. The right panel is the same penalty against the measure-weighted node normal and is indistinguishable from the exact panel, with a peak speed of 5.0e-3.

The same problem, the same coefficient of $10^6$, the same colour scale, and the
only difference between the middle and right panels is which normal the penalty
is written against. Against the facet normal the flow along the outer boundary
is suppressed: the peak speed falls by a quarter and the two fast lobes at the
boundary are gone. Refining the mesh does not bring them back.
```

The coefficient is $10^6$ and the normal is `mesh.Gamma`, the facet normal at
the quadrature points. The same coefficient against the measure-weighted node
normal, on the same meshes, gives velocity errors of 1.0 × 10⁻², 2.4 × 10⁻³,
1.0 × 10⁻³ and 4.9 × 10⁻⁴ and stress errors of 2.4 × 10⁻², 6.3 × 10⁻³,
2.7 × 10⁻³ and 1.4 × 10⁻³. One difference, one line of code, and one method
converges while the other does not.

The mechanism is old and well understood. Imposing
$\mathbf{u}\cdot\hat{\mathbf{n}} = 0$ facet by facet asks a node shared by two
facets to satisfy two different constraints, and two independent constraints on
a two-component velocity leave nothing. Push the coefficient up and the vertex
velocities go to zero: the flow is being asked to stay inside a polygon rather
than a circle, and the polygon is not a good enough approximation of the circle
for that particular question. The discrete limit is a different problem from
the smooth one, so refining the mesh does not approach the smooth answer.

Two things follow for practice. A direct penalty is a perfectly good method,
but it has to be written against the node normal. And the leak is not a
sufficient check: at a coefficient of $10^3$ the facet-normal penalty leaks
3 × 10⁻² and gets the stress amplitude right to 1.9 × 10⁻³, while at $10^8$ it
leaks 1 × 10⁻⁷ and is 26% wrong. Over that range the constraint improves by five
orders of magnitude and the answer gets steadily worse.

### The multiplier was not the whole traction

The multiplier column of the table above used to sit near 3 × 10⁻² for three
resolutions and then drop, which is not a convergence rate. The cause was the
augmented-Lagrangian term, and it was a defect rather than a property of the
method.

The momentum row carries both the multiplier and the augmentation,
$(h + r(\mathbf{u}\cdot\hat{\mathbf{n}} - g))\hat{\mathbf{n}}$, so the traction
holding the boundary is $h + r(\mathbf{u}\cdot\hat{\mathbf{n}} - g)$ and not $h$
alone. The second term vanishes only where the constraint row is satisfied
exactly. Discretely it is satisfied to the solver's tolerance, and $r$ multiplies
that residual straight back into the traction. Underworld returned $h$.

On the annulus, with a uniform viscosity and the default $r = 10^4\mu$, the
omitted share is a few per cent. On SolCx it is nearly everything, because the
default $r$ is viscosity-weighted and the step takes it to $10^{10}$ on the stiff
half. At a contrast of $10^6$, against an exact surface topography whose
deviation peaks at 0.381:

| read | peak | correlation with the exact | relative $l_2$ |
|---|---|---|---|
| the multiplier $h$ | 0.042 | **−0.52** | 0.96 |
| $h + r(\mathbf{u}\cdot\hat{\mathbf{n}} - g)$ | 0.382 | +0.999 | 0.084 |

An order of magnitude low and pointing the wrong way, on a solve whose velocity
error is 8.8 × 10⁻⁶. Underworld3 issue #607: `traction()` now returns the sum and
`topography()` is built on it, so the tables here are the corrected read and a
caller who asks for topography gets it.

Worth saying how it survived. The method's own validation scored a *correlation*
of 0.9999 between the multiplier and the recovered normal stress. A correlation
is scale-free, so it cannot see a systematic amplitude deficit — which is exactly
what a missing share of the load is. The replacement guard scores a relative
$l_2$ against an exact answer and carries the bare multiplier as its negative
control.

### The multiplier and the consistent boundary flux are the same object

The correction above is not a patch. Write the momentum row's boundary term out
and the identity is immediate: the assembled load is
$M_\Gamma\,(h + r(\mathbf{u}\cdot\hat{\mathbf{n}} - g))$, and at convergence it
balances the volume residual restricted to the boundary, which is precisely the
nodal load the consistent boundary flux back-calculation reads
[@Zhong_1993]. So

$$
h + r(\mathbf{u}\cdot\hat{\mathbf{n}} - g)
  = -M_\Gamma^{-1} \left. (A\mathbf{u} - \mathbf{b}) \right|_\Gamma ,
$$

the CBF traction de-smeared with the boundary mass. The multiplier is not a
second, independent estimate of the surface stress: it is the same computation
the rotated constraint's reaction performs, arrived at by carrying the traction
as an unknown instead of reading it out of the residual afterwards. Dropping the
$r$ term is dropping part of the load, which is why it fails exactly where $r$ is
large.

Measured across the two solves — they are different discrete problems, so this
is agreement rather than an identity check — the corrected multiplier and the
rotated reaction differ by 3.2% at a contrast of 100 and 4.9% at $10^6$, both
inside each route's own error against the exact answer (5 to 9%). They cannot be compared within a single solve, and the reason is the identity
itself: on a multiplier-constrained boundary the constraint enters the row it
constrains, so the assembled residual there is balanced at convergence and the
CBF back-calculation reads zero (measured: rms 4 × 10⁻¹³ against a traction of
0.37). There is no reaction left to read because the multiplier is holding it.
`boundary_flux` now says so instead of returning that zero quietly
(underworld3#614).

This also settles a question the free-surface work left open. That work used
SolCx the same way, to choose among topography recoveries, and landed on a
rotated free-slip lid with the CBF reaction and a continuous pressure — corr
0.999, relative $l_2$ 0.04 — while rejecting the multiplier. Both conclusions
were right about what was in front of them: the multiplier *as returned* is
missing the augmentation share, and the CBF reaction is the same quantity with
nothing missing.

### The other half: a lateral viscosity contrast

No exact solution has both a curved boundary and a laterally varying viscosity,
so the case where weak constraints are most often reported to give trouble is a
separate test with a trivial geometry. SolCx is that test: the unit box, free
slip on all four walls, viscosity 1 to the left of $x = 0.5$ and $\eta_B$ to the
right. `uw.analytic.SolCx` publishes the exact dynamic topography on the top
wall. Three walls carry the ordinary component condition and the treatment under
test is on the top wall alone.

On a box every treatment reduces to holding one velocity component, so nothing
here is about normals. What it can say is whether a treatment holds the traction
it was given when the viscosity beside it jumps.

Relative $l_2$ error of the surface topography along the top wall, mean removed,
at 32 × 32 elements. Each entry is the whole wall and then the wall with two
elements trimmed from each end.

| $\eta_B/\eta_A$ | component Dirichlet | penalty, $10^4$ | multiplier | rotated |
|---|---|---|---|---|
| 10 | 0.048 / 0.054 | 0.045 / 0.051 | 0.048 / 0.054 | 0.048 / 0.054 |
| 10² | 0.072 / 0.081 | 0.056 / 0.060 | 0.072 / 0.081 | 0.072 / 0.081 |
| 10³ | 0.075 / 0.084 | 0.234 / 0.230 | 0.075 / 0.084 | 0.075 / 0.084 |
| 10⁴ | 0.076 / 0.085 | 0.698 / 0.697 | 0.076 / 0.085 | 0.076 / 0.085 |
| 10⁶ | 0.076 / 0.085 | 0.992 / 1.000 | 0.075 / 0.084 | 0.076 / 0.085 |

**The three exact treatments agree to three figures at every contrast**, whole
wall and trimmed alike. That is the result to take from this half, and it took
two fixes to get: the multiplier had to report the whole traction rather than
$h$, and the rotated constraint had to hold the corner where it meets the side
walls. Before them the rotated column read 0.322 at a contrast of 10 — six times
the reference, all of it two nodes — and the multiplier column was an order of
magnitude out at $10^6$.

**Read the first column as the floor.** The component Dirichlet condition is
exact and has no parameter, and its velocity error is 8.8 × 10⁻⁶ at a contrast of
$10^6$. It still reads 0.085. That number is the recovery's error, not a boundary
condition's: on the stiff half the recovered $\sigma_{zz}$ is a difference between
the pressure and $2\eta\,\partial_z u_z$ with $\eta = 10^6$, so a relative velocity
error of $10^{-5}$ arrives in the stress at the size of the signal. Nothing here
is worse than the reference except the penalty.

**A bare penalty coefficient cannot serve both halves.** At $10^4$ it is the best
column in the table at low contrast — the constraint is weak enough not to fight
the recovery — and by $10^6$ it is useless: 0.992, which is to say the recovered
topography carries none of the signal. Scaling the coefficient by the local
viscosity is the obviously right thing to want, and it does not solve here at any
magnitude we tried, from $\mu$ to $10^3\mu$ (a `Piecewise` viscosity inside the
boundary term fails the line search). This is the same lesson as $\gamma$'s window
on the annulus, in a place where the window closes entirely.

**Nitsche is missing from this table**, and honestly so. Our configuration of it
on this box converges at a contrast of $10^6$ and fails the line search at $10$ —
the opposite way round from every expectation — at 16 × 16 and 32 × 32 alike and
at $\gamma = 10$, $100$ and $1000$. Where it does converge, $\gamma$ has to rise
with the contrast exactly as the annulus said: at $10^6$ and 16 × 16 the surface
stress error is 25 at $\gamma = 10$, 1.2 at $100$ and 0.17 at $1000$, while the
constraint is held to $10^{-3}$ or better throughout. We are not confident enough
in that configuration to put a column of numbers behind it.

:::{note} A measurement we withdrew
An earlier draft of this section carried a Nitsche column and different numbers
throughout. They were taken while several runs shared one mesh-cache file:
`StructuredQuadBox` keys its cache on the box corners and not on the element
resolution, so concurrent runs at different resolutions silently swap meshes
(underworld3#618). A marginal solve then flips between converged and diverged for
reasons that look like the method. Every number in this section was re-measured
sequentially, on a cleared cache, with nothing else running.
:::


### What each one costs

Accuracy is half the choice. Seconds on the annulus, median of three timed
repeats after an untimed warm-up, run sequentially — the solve, and then the
recovery of the surface traction by whatever route that treatment has.

| cell size | velocity nodes | penalty | Nitsche | multiplier | rotated |
|---|---|---|---|---|---|
| 0.075 | 2 174 | 0.01 / 0.153 | 0.01 / 0.037 | 0.02 / 0.001 | 0.01 / 0.003 |
| 0.050 | 4 802 | 0.03 / 0.058 | 0.03 / 0.060 | 0.04 / 0.002 | 0.03 / 0.004 |
| 0.035 | 9 406 | 0.06 / 0.095 | 0.06 / 0.099 | 0.08 / 0.004 | 0.05 / 0.006 |

**The solve costs the same whichever you choose.** Within the spread, all four
are the same number at every size — 0.06 s at 9 400 nodes. The multiplier is the
one that carries a visible premium, about 30%, which is the extra field and the
larger saddle point; its interior degrees of freedom are constrained out of the
global system, so what is left is the boundary trace.

**The recovery is where they differ, by a factor of 15 to 25.** Projecting
$\hat{\mathbf{n}}\cdot\boldsymbol{\sigma}\hat{\mathbf{n}}$ is a second solve, and
it costs more than the Stokes solve did at the coarser sizes. The reaction and
the multiplier are arithmetic on the boundary trace: 4 to 6 ms where the
projection takes 95 to 99.

That ratio is the practical argument, and it points the same way the accuracy
did. The route that does not differentiate the answer is both the more accurate
one and the cheaper one, and on a time-dependent model it is paid at every step.

:::{note} What these timings are not
Two-dimensional problems of ten thousand nodes, on one core, with a direct
solver. They separate a recovery solve from boundary arithmetic, which is a
structural difference and will survive scaling. They say nothing about how the
four compare on a large parallel spherical shell, where the rotated velocity
block's multigrid and the multiplier's larger Schur complement are the terms that
matter and neither is exercised here.
:::

### Which one to use

For a model that consumes the velocity and nothing else, all four are the same to
plotting accuracy — provided the constraint is written against the node normal.
That proviso is the only one that can spoil the velocity, and it costs one line.

When the wall-normal traction is the answer:

- **Rotated free slip is the default.** It holds the constraint to machine
  precision rather than to the discretisation, its reaction is the most accurate
  surface stress measured here, and that reaction is nearly free. The price is
  structural — a mixed basis that the multigrid has to carry — and it is paid
  once, inside the solver, rather than by the person setting up the model.
- **The multiplier is its equal on accuracy** and returns the same object by a
  different route; take it when you want the traction as an unknown of the
  system, or when the constrained problem's conditioning suits you better. It
  costs about 30% more to solve.
- **Nitsche is the one to reach for when the boundary condition must change
  during the model** — a wall that begins as a prescribed velocity and relaxes to
  a prescribed traction is a Nitsche problem, because a hard constraint cannot
  morph. Budget for tuning $\gamma$ against the stress and not against the leak,
  and expect the window to move with the viscosity contrast.
- **A direct penalty is fine for a velocity-only model** and needs the node
  normal, a coefficient chosen per problem, and a check on something physical
  before the answer is believed.


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
