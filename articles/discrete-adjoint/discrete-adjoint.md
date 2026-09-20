---
title: A Discrete Adjoint from the Run Record
description: >-
  Every implicit solve in Underworld3 is a residual written in SymPy, so the
  derivative of a misfit with respect to a named parameter comes from
  transposing the Jacobian the solver assembled and differentiating its
  residual symbolically. We set out the adjoint of one solve and use it to
  recover the friction coefficient of a listric fault, segment by segment,
  from the uplift rate along the surface and the shear stress near five
  points.
date: 2026-09-15
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
license: CC-BY-4.0
keywords:
  - Underworld Code
  - adjoint
  - inversion
  - faults
  - data assimilation
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/discrete-adjoint/
    template: ../../templates/pdf
    output: discrete-adjoint.pdf
    article_id: UWTN 2026-020
    article_version: 1.0.0
    software_version: underworld3 0.0.0
---
We want the derivative of a measure of a model's result with respect to a
parameter the model depends on: here, the strength of a fault. A model in
Underworld3 is a Python program, and there is no model document to
differentiate. There is instead the residual of each implicit solve, which is
a SymPy expression the solver assembled from what the user wrote. This note
sets out how that residual gives an exact discrete adjoint for one solve, and
uses it on a listric fault whose friction varies down dip.

## An implicit solve is a residual

Every solver assembles its residual from two templates, $F_0$ and $F_1$, in
the unknown $u$ and whatever fields and named quantities the user wrote into
them:

```{math}
:label: eq-residual
R(u;\, m) \;=\;
\int_\Omega F_0(u, \nabla u, m)\,\phi
\;+\; F_1(u, \nabla u, m) \cdot \nabla\phi \;=\; 0 .
```

The SNES that solves it assembles the Jacobian $K = \partial R/\partial u$
from the symbolic derivative of {eq}`eq-residual`, and the same derivative can
be taken with respect to any named quantity $m$ in the residual. Nothing is
linearised by hand and nothing is differenced.

## The adjoint of one solve

For a misfit $J(u)$ of the solution, the derivative with respect to $m$ is

```{math}
:label: eq-adjoint
K^{T}\mu = -\frac{\partial J}{\partial u}, \qquad
\frac{\mathrm d J}{\mathrm d m} = \frac{\partial J}{\partial m} + \mu^{T}\frac{\partial R}{\partial m}.
```

In the library this is one call, `solver.gradient(misfit, parameters=...)`,
made of three steps. `misfit_duals` assembles
$\partial J/\partial u$ as a load, $\int g_0\,\phi_j + \mathbf g_1\cdot\nabla\phi_j$,
where $g_0$ and $\mathbf g_1$ are the symbolic derivatives of the misfit
integrand with respect to $u$ and $\nabla u$. A misfit on a stress reads the
velocity through its gradient, and the gradient part of the load is what
carries it; there is no integration by parts and no boundary term.
`adjoint_solve` assembles $K^{T}$ rather than transposing $K$. PETSc
assembles a Jacobian block from four pointwise kernels, the derivatives of
$F_0$ and $F_1$ with respect to $u$ and $\nabla u$, and the transposed
bilinear form has the same four with trial and test exchanged: the two
diagonal kernels transposed on their paired indices and the two mixed ones
swapped. The solver registers that kernel set, lets the SNES assemble, and
solves the result with its own Krylov solver and preconditioner; on the
composite velocity–pressure system of Stokes the $(u,p)$ and $(p,u)$ blocks
exchange places. Nothing is differentiated again, and the assembled operator
agrees with the explicit transpose to $10^{-16}$. `sensitivity` forms $\mu^{T}\partial R/\partial m$ by
differentiating the residual with respect to $m$, expanding every other named
expression first: the residual holds the constitutive model's own symbol for
the parameter, and the derivative of a value substituted too early is zero.

Whether the forward solve reached its state by Newton or by Picard does not
enter. The converged state is the same, $\partial R/\partial u$ is a function
of that state, and the residual is symbolic, so the consistent tangent is
assembled for the transpose whichever tangent the iteration used.

## A listric fault of unknown friction

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
\tau_y = C + \mu\, p, \qquad
\eta_1 = \frac{\eta_0\,\tau_y}{\tau_y + 2\eta_0\,\dot\varepsilon_s},
```

with $p$ the pressure, $\dot\varepsilon_s$ the shear strain rate resolved on
the plane, and $\eta_1$ the plane's viscosity, which tends to
$\tau_y / 2\dot\varepsilon_s$ where the plane slips and to $\eta_0$ where it
does not. Outside a band around the fault $\eta_1 = \eta_0$. The friction
coefficient $\mu$ takes a separate value on each of four segments, each a
named expression in the residual: the flat, the lower and upper thirds of the
ramp, and the third nearest the surface. The residual is nonlinear in the
velocity through $\dot\varepsilon_s$ and in the pressure through $\tau_y$, so
the forward solve is Newton and the transpose in {eq}`eq-adjoint` is of the
consistent tangent, which carries both dependences.

The observations are the uplift rate $v_y$ along the top surface and the
shear stress $2\eta_0\dot\varepsilon_{xy}$ near five points in the bulk, taken
from a run at the true coefficients $(0.05, 0.15, 0.25, 0.4)$: a weak
décollement and a ramp whose friction rises towards the surface. The misfit
is the squared difference of the uplift rate integrated along the surface,
plus the squared difference of the stress under a Gaussian weight around
each point; its dual on the velocity is a facet load and a volume load. We invert for the logarithm of
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
fitted $\chi^2/N$ is 1.0001 in each case, so those are the answers the data
hold. A run in time is a chain of solves like this one, differentiated in
reverse order.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=discrete-adjoint">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=discrete-adjoint">Start one</a></div></div>
