---
title: Model Derivatives and Their Uses
description: >-
  A model derivative says how a prediction moves when a parameter does.
  Underworld3 takes it from one adjoint solve, assembled from the Jacobian
  blocks its Newton solver already uses, for a scalar parameter or a field.
  We use it to find how low a viscosity floor has to go before a
  viscoplastic solution stops depending on it, and to recover the friction
  coefficient of a listric fault, segment by segment, from the uplift rate
  along the surface and the shear stress near five points.
date: 2026-10-06
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
license: CC-BY-4.0
bibliography:
  - references.bib
keywords:
  - Underworld Code
  - adjoint
  - inversion
  - faults
  - viscoplasticity
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/model-derivatives-and-their-uses/
    template: ../../templates/pdf
    output: model-derivatives-and-their-uses.pdf
    article_id: UWTN 2026-021
    article_version: 1.0.0
    software_version: underworld3 0.0.0
---
A model derivative, $\mathrm dJ/\mathrm dm$, says how a prediction $J$ moves when a parameter $m$ does: whether the parameter matters to the prediction, which way to move it, and how far. [Symbolic FEM and Adjoint Forms](/symbolic-fem-and-adjoint-forms/) showed that Underworld3 obtains it from the Jacobian blocks that Newton already uses: one transposed linear solve, $K^{T}\mu = -(\partial J/\partial u)^{T}$, and an integral $\mu^{T}\partial R/\partial m_k$ for each parameter. Here we look at how the library assembles it, and at two of its uses.

The first is a solver that contains a tuneable, regularising parameter, a viscosity floor, and we ask how far it can be lowered before it stops perturbing the answer, so that it costs the solver nothing it does not have to. In the second example, we invert for model parameters by matching a subset of model outputs.

## The adjoint of one solve

In the library the adjoint problem, $K^{T}\mu = -(\partial J/\partial u)^{T}$, is one call, `solver.gradient(J, parameters=..., fields=...)`,
made of three steps. `misfit_duals` assembles $\partial J/\partial u$ as a
force, $\int g_0\,\phi_j + \mathbf g_1\cdot\nabla\phi_j$, where $g_0$ and
$\mathbf g_1$ are the symbolic derivatives of the misfit integrand with
respect to $u$ and $\nabla u$ — the same decomposition as the residual, which
is why a misfit on a stress needs no integration by parts and produces no
boundary term: it reads the velocity through its gradient, and
$\mathbf g_1$ carries it. `adjoint_solve` registers the forward kernels with
$G_1$ and $G_2$ exchanged where they carry the operator, lets the SNES assemble, and
solves with its own Krylov solver and preconditioner; where they do not it
transposes the assembled operator and solves that forwards with the same
solver. `sensitivity` forms $\mu^{T}\partial R/\partial m$
from the derivatives of $F_0$ and $\mathbf F_1$ with respect to $m$.

Two cases keep the matrix. A boundary Jacobian — a natural or Nitsche condition
carrying a tangent — has no swapped kernel. A rotated constraint has a
different operator to begin with: the forward solve inverts $Q K Q^{T}$ with
the wall-normal rows eliminated, so the adjoint is the transpose of that, built
from the assembled forward Jacobian and rotated in the same frame. Both then
transpose the matrix explicitly and solve the transposed system *forwards* with
the same Krylov solver, rather than asking PETSc for a transpose solve. PETSc
will not apply the transpose of a one-sided SOR smoother, which is the velocity
block of every Stokes solve with a mesh hierarchy; transposing the operator
instead of the preconditioner leaves every preconditioner the forward solve can
use available to the adjoint.

The one trap in `sensitivity` is early substitution. If the parameter's value has been folded
into the expression before differentiation the derivative is zero, correctly
and uselessly, so the sensitivity expands every *other* named expression first
and leaves $m$ standing.

### A number or a field

What the call is asked to differentiate with respect to comes in two kinds,
and they enter the calculation in different places.

A **scalar parameter** is a named expression the residual holds as a symbol —
a friction coefficient, a reference viscosity, a viscosity floor. Its
derivative is the pseudo-force $\partial R/\partial m$ contracted against $\mu$: one integral, one
number.

A **field** is a mesh variable the residual reads — a viscosity painted cell
by cell, a density, an initial temperature. Differentiating the residual with
respect to it gives not a number but a force on that field's own space, one
entry per degree of freedom: $(\partial R/\partial f)^{T}\mu$. Read as a
field, it is a sensitivity map: where in the domain a change in $f$ would move
the measure, and which way.

Both come out of the same adjoint solve:

```python
import underworld3 as uw

# a field and a scalar, both written into the rheology
eta0 = uw.discretisation.MeshVariable("eta0", mesh, 1, degree=0)

model = stokes.constitutive_model
model.Parameters.shear_viscosity_0 = eta0.sym[0]    # the field
model.Parameters.shear_viscosity_min = 1.0e-3       # the scalar: a viscosity floor
eta_min = model.Parameters.shear_viscosity_min      # its symbol in the residual

stokes.solve()                          # the forward state

# J: the measure, an integrand over the mesh — here the misfit of the
# vertical surface velocity against an observed profile
J = {"Top": (v.sym[1] - v_obs.sym[1]) ** 2 / 2}

result = stokes.gradient(J, parameters=[eta_min], fields=[eta0])
dJdm = result["parameters"]
dJdf = result["fields"]

result["J"]                # the measure itself
dJdm[eta_min]              # dJ/d(eta_min): a float
dJdf[eta0]                 # dJ/d(eta0): an array on eta0's nodes, the map
```

A scalar costs an integral after the adjoint solve and a field costs a force
assembly after it; neither costs another solve, so asking for ten parameters
and three fields is the same single transposed solve as asking for one.

So the cost of an exact derivative is one linear solve against an operator
the forward problem had already assembled, plus one integral per parameter.
The derivation was paid for by Newton.

Whether the forward solve reached its state by Newton or by Picard does not
enter. The converged state is the same, $\partial R/\partial u$ is a function
of that state, and the residual is symbolic, so the consistent tangent is
assembled for the transpose whichever tangent the iteration used — the
forgiveness that let Picard find the state does not extend to differentiating
at it.

## How close to the singularity: the viscosity floor

A viscoplastic solve carries a parameter that is there for the solver, not the
physics: the viscosity floor $\eta_{\min}$, the least viscosity yielded
material is allowed to reach. Without it the effective viscosity of material
at yield, $\tau_y/2\dot\varepsilon$, has no lower bound, the contrast the
solution can develop is unbounded, and the problem approaches the rigid-plastic
limit where the solution is no longer unique. The floor keeps the solve away
from that singularity. The cost is that it also changes the answer: a floor
set too high stiffens exactly the shear bands the model exists to find.

So we want to go no closer to the singularity than we have to, and the
derivative says how close that is. With a prediction $J$ — the dissipation in
the shear band, the surface velocity, whatever the model is for —
$\mathrm dJ/\mathrm d\eta_{\min}$ at the floor in use measures how much the
prediction still depends on it. While it is large, lowering the floor changes
the answer; once it is small against the precision the prediction needs, the
floor has stopped mattering and there is nothing to gain by lowering it
further and making the solve harder. It is one adjoint solve at each floor
tried, and no solve at the floor one would rather not attempt.

The floor enters the residual where it binds and nowhere else. It is a lower
bound, $\eta = \max(\eta_{\mathrm{eff}}, \eta_{\min})$, so $\partial R/\partial
\eta_{\min}$ vanishes wherever the material is stiffer than the floor, and
the sensitivity is an integral over the cells the floor is holding up (rounded
over a narrow band when the bound is smoothed). The same field that gives the
number shows where the floor is doing its work.

The example is a viscoplastic layer four times as wide as it is thick,
shortened at unit rate from both walls over a free-slip base, with a free
top. It has unit viscosity and yields at a von Mises stress of one half,
half the viscous stress of the bulk shortening, so it must yield to shorten
at all, and a Gaussian seed at the middle of the base lowers the yield
stress there by ninety per cent. Two bands rise from the seed to the surface
at $45^\circ$, and the wedge between them is pushed up
([](#fig-floor)a). We follow two predictions: the rate of work the walls do,
$\int\tau:\dot\varepsilon$, which is the layer's strength at this rate of
shortening, and the uplift, through $\int v_y^2/2$ along the top, which
grows as the uplift concentrates in the wedge. The floor starts at $0.5$ and
is lowered in steps to $10^{-4}$, each solve starting from the solution at
the floor above, and at each floor one adjoint solve per prediction gives
its derivative. At a floor of $0.01$ the adjoint derivative of the rate of
work agrees with central differences to three parts in $10^{7}$.

```{figure} figures/viscosity_floor.png
:label: fig-floor
:alt: Four panels. (a) The layer, four units wide and one deep, coloured by the logarithm of the effective viscosity at the lowest floor: yellow, a viscosity of one, everywhere except two narrow bands that rise from the middle of the base at 45 degrees to the surface at x = 1 and x = 3, where the viscosity falls to about a thousandth; white arrows show the walls moving inward and the wedge between the bands moving up. (b) The same layer coloured by the derivative of the rate of work with respect to the floor, per unit area, at a floor of 0.01: black almost everywhere, faint along the two bands, and bright at the seed where they meet. (c) The magnitude of the logarithmic sensitivity of the rate of work, solid, and the uplift, dashed, against the floor from 0.5 down to 0.0001, on logarithmic axes, one colour per mesh: both rise to a maximum between floors of 0.1 and 0.03, the uplift's eight times higher, fall by a factor of ten by a floor of 0.003, then fall steeply, by a further two orders of magnitude by 0.001 on the coarser mesh, the finer mesh falling at a slightly lower floor. (d) Newton iterations against the floor: lowered from the floor above, a peak of twelve to fifteen at floors of 0.03, falling to one or none below 0.001; solved from rest, eight to thirty-three at the floors that matter and thirty-five to forty below 0.001.

The viscosity floor of a viscoplastic layer. (a) The effective viscosity and
the velocity at the lowest floor. (b) Where the floor does its work at a
floor of $0.01$: the derivative of the rate of work with respect to a floor
set cell by cell, per unit area. (c) The logarithmic sensitivity of the rate
of work (solid) and the uplift (dashed) as the floor is lowered, for two
mesh sizes $h$. (d) The Newton iterations at each floor, lowered from the
floor above (filled) and solved from rest (open).
```

The logarithmic sensitivity, $\mathrm d\ln J/\mathrm d\ln\eta_{\min}$, is
the fractional change in a prediction for a fractional change in the floor
([](#fig-floor)c). At a floor of $0.5$ the floor holds up most of the layer,
and the rate of work changes by half as much as the floor does. Lower down it
holds up the bands, and the two predictions part: at $0.1$, while the wedge
is still forming, the uplift is twenty times as sensitive as the rate of
work. From their maxima both sensitivities fall by a factor of ten by a
floor of $0.003$, and then steeply, by a further factor of a hundred and fifty
by $0.001$ on the coarser mesh, where the floor passes below the viscosity the
bands reach on their own. Lowering the floor from $0.5$ to
$10^{-4}$ changes the rate of work by nine per cent and the uplift by twenty;
below $0.002$ it changes neither by more than four parts in $10^{4}$. On the
mesh with half the cell size the fall comes at a floor about a third lower:
the bands are narrower, their strain rate is higher, and the viscosity they
reach is lower, so how low the floor needs to go depends on the mesh as well
as on the material, and the derivative finds it on each mesh without a solve
below it.

The Newton iterations follow the same course ([](#fig-floor)d). Lowered from
the floor above, each solve takes most iterations where the sensitivity is
largest, and one or none once the floor has stopped mattering. Solved from
rest, the same floors take eight to thirty-three iterations where the floor
matters and thirty-five to forty below $0.001$, where it does not.

The floor's work is also local. With the floor set cell by cell, all cells
equal, the adjoint returns $\mathrm dJ/\mathrm d\eta_{\min}$ for each cell,
and the cells' values add up to the derivative with respect to the single
floor to eleven figures. At a floor of $0.01$, ninety-nine per cent of the
derivative of the rate of work comes from two per cent of the layer, and
ninety-seven per cent from within $0.15$ of the seed, where the two bands
meet ([](#fig-floor)b). That is where the floor is still holding the
solution up, and where a lower floor would first change it.

## A listric fault of unknown friction

@Ratnaswamy_2015 used an adjoint to estimate the coupling at plate
boundaries in a non-linear mantle flow model. This example is a smaller
problem of the same kind: the friction on one fault.

The fault is listric: a flat décollement at depth that steepens on a
circular ramp to a dip of $60^\circ$ where it reaches the surface, in a box
20 km wide and 10 km deep meshed at 24 cells across the depth, under
horizontal shortening from both sides and a gravity load, with a no-slip base and a free top, so the surface velocity
is the uplift rate. The notebook states the problem in kilometres, pascal
seconds and millimetres per year, and the solver works in units of the
depth, the bulk viscosity of $10^{21}$ Pa s and the convergence rate of
8.4 mm/yr, so a unit of stress is 26 MPa and the lithostatic pressure at
the base is ten. The numbers in this note are in those units. The fault is
not cut into the mesh. It is a weak plane in a
transversely isotropic viscosity: the bulk viscosity is $\eta_0 = 1$, the
director is the normal at the nearest point of the fault, vertical on the
flat and radial on the ramp, and the plane yields at the Coulomb stress

```{math}
:label: eq-coulomb
\tau_y = C + \tan\phi\, p, \qquad
\eta_1 = \frac{\eta_0\,\tau_y}{\tau_y + 2\eta_0\,\dot\varepsilon_s},
```

with $p$ the pressure, $\dot\varepsilon_s$ the shear strain rate resolved on
the plane, and $\eta_1$ the plane's viscosity, which tends to
$\tau_y / 2\dot\varepsilon_s$ where the plane slips and to $\eta_0$ where it
does not. Outside a band around the fault $\eta_1 = \eta_0$. The friction
coefficient $\tan\phi$, with $\phi$ the friction angle, takes a separate value on each of four segments, each a
named expression in the residual: the flat, the lower and upper thirds of the
ramp, and the third nearest the surface. The residual is nonlinear in the
velocity through $\dot\varepsilon_s$ and in the pressure through $\tau_y$, so
the forward solve is Newton and the transposed operator is the
consistent tangent, which carries both dependences.

The observations are the uplift rate $v_y$ along the top surface and the
shear stress $2\eta_0\dot\varepsilon_{xy}$ near five points in the bulk, taken
from a run at the true coefficients $(0.05, 0.15, 0.25, 0.4)$: a weak
décollement and a ramp whose friction rises towards the surface. The misfit
is the squared difference of the uplift rate integrated along the surface,
plus the squared difference of the stress under a Gaussian weight around
each point; its dual on the velocity is a facet force and a volume force. We invert for the logarithm of
each coefficient, starting from $0.2$ on every segment, with L-BFGS from
SciPy taking the misfit and its gradient from the three calls above.

```{figure} figures/fault_friction.png
:label: fig-fault
:alt: Three panels. Left, the plane's viscosity on the box at the true friction, a band running flat at y = 3 km from the left wall and curving up to reach the surface at x = 19 km; the band is weakest along the upper ramp near the surface and in patches on the flat, and close to the bulk value on the middle of the ramp; five crosses mark the stress points. Middle, the uplift rate along the surface, a trough of 3.4 mm/yr at x = 9 km and a peak of 5.3 mm/yr at x = 18.5 km for the true and recovered coefficients, which coincide, with the initial guess peaking at 5.9 mm/yr. Right, the four coefficients against misfit evaluation on a log axis, each reaching its true value, dashed, within twenty-six evaluations; the flat moves last, from 0.2 to 0.05 between evaluations ten and seventeen.

The plane's viscosity at the true friction, with the stress points; the
uplift rate at the true, initial and recovered coefficients; and the path
each coefficient took. The true and recovered profiles coincide.
```

Before the inversion, the adjoint gradient at the starting guess is checked
against central differences in each log-coefficient:

| segment | adjoint | finite difference | ratio |
|---|---|---|---|
| flat | $-1.00333 \times 10^{-6}$ | $-1.00333 \times 10^{-6}$ | $1.00000$ |
| lower ramp | $-4.38768 \times 10^{-4}$ | $-4.38768 \times 10^{-4}$ | $1.00000$ |
| upper ramp | $-3.23950 \times 10^{-3}$ | $-3.23950 \times 10^{-3}$ | $1.00000$ |
| near surface | $-3.98863 \times 10^{-3}$ | $-3.98863 \times 10^{-3}$ | $1.00000$ |

The inversion recovers $(0.05, 0.15, 0.25, 0.4)$ to machine precision in
twenty-six misfit evaluations, each one Newton solve of six iterations from a cold
start, one transposed solve, and four sensitivities. The
flat's sensitivity at the start is three orders of magnitude below the
ramp's: at a friction of $0.2$ under seven units of pressure the décollement
barely slips and the surface hardly sees it, and it is the last coefficient
to move, between the eleventh and fifteenth evaluations. The notebook in
`examples/`, also there as a script, runs the check in three minutes and
the inversion in about ten on a laptop.

## What the example does not show

The fault's position and shape are fixed. The observations are noise-free
and the misfit carries no regularisation, so the twin experiment says the
gradient is right and the four coefficients are identifiable from these
observations, and nothing about how well they would be resolved from real
ones. The same script with other observations recovers the same four
coefficients to five figures: the orientation of the principal stress at
the five interior points alone, in twenty-three evaluations, and the surface
strain rate $\partial v_x/\partial x$ along the top alone, in thirty-eight. The
flat's sensitivity is a thousandth of the near-surface segment's under
every set, and it is always the last to arrive. Two observables were tried
and dropped. The stress orientation on the free surface is a sign, since
the shear strain rate vanishes where the traction does; what an inversion
on it fitted was the discrete strain rate's departure from that. And a
Gaussian band beneath the surface, standing in for a surface integral,
sees the volume it covers rather than the surface, and recovered
coefficients that the true boundary integral does not resolve. With Gaussian noise on the observed velocity at a
fraction of its rms, and PETSc TAO's bounded quasi-Newton method as the
driver with friction confined to $[0.005, 1]$, the coefficients fail in the
reverse of the sensitivity order: at one percent the flat is ten percent
low and the rest within two, at three percent the flat is a third low, and
at ten percent the flat goes to the upper bound, a locked décollement, with
the lower ramp halved to compensate. A bound hands an unresolved parameter
the edge of its box. Written as a negative log posterior instead, the
misfit as $\chi^2/2$ against its floor under the noise and a Gaussian prior
of width one log unit about the start, the unresolved segments return to
the prior and the resolved ones move: at three percent noise the
near-surface segment is found to five percent and the flat is not moved,
and at ten percent only the near-surface segment moves, halfway. The
fitted $\chi^2$ per observation is 1.0001 in each case, so those are the answers the data
hold. A run in time is a chain of solves like this one, differentiated in
reverse order.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=model-derivatives-and-their-uses">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=model-derivatives-and-their-uses">Start one</a></div></div>
