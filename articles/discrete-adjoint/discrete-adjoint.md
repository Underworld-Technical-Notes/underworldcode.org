---
title: Symbolic FEM and Adjoint Forms
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
bibliography:
  - references.bib
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
In this article, we will see how the underworld3 sympy formulation combined with the PETSc finite element, strong-form framework builds model derivatives which can solve non-linear problems using a Newton method. This requires us to calculate the local derivative of the model with respect to the unknowns so that we know the direction to move towards a better solution.

If we differentiate the prediction a model makes with respect to one of its parameters, then we can determine how sensitive the prediction is to changes in that parameter and therefore whether the model can be used to constrain the value of that parameter. Similarly, model derivatives are used in data assimilation to determine how to adjust a model's parameters so it better fits the observations we have.

We provide two examples. The first is a solver that contains a tuneable, regularising parameter where we ask the question - is there an optimal value for this parameter that minimises the perturbation of the true problem while providing the maximum benefit to the solver efficiency. In the second example, we invert for model parameters by matching a subset of model outputs.

## Theoretical background

Underworld3 starts from the strong form of the equations which is usually how they are written in a textbook or a paper. These are symbolic, sympy objects that pass directly to compiled objects in PETSc  [@Moresi_2025; @Knepley_2013]: everything
inside a divergence term goes into the flux $\mathbf F_1$, everything else into the
force $F_0$. The weak form is then an integral of those two against the test
function and its gradient,

```{math}
:label: eq-residual
R(u;\, m) \;=\;
\int_\Omega F_0(u, \nabla u;\, m)\,\phi
\;+\; \mathbf F_1(u, \nabla u;\, m) \cdot \nabla\phi \;=\; 0 ,
```
$R$, the residual {eq}`eq-residual`, is the **out-of-balance force**: what the
assembled system has left over when the current $u$ is put into the governing
equation. A solution is a $u$ that makes it vanish. Here $m$ is a set of parameters of the model (for example a Rayleigh number, or a constitutive modulus) that the user typically would adjust to run an example. 

A Newton non-linear solver needs the derivative of $R$ with respect to the unknowns
[@Moresi_2026_sympy]:

```{math}
:label: eq-blocks
G_0 = \frac{\partial F_0}{\partial u}, \quad
G_1 = \frac{\partial F_0}{\partial (\nabla u)}, \quad
G_2 = \frac{\partial \mathbf F_1}{\partial u}, \quad
G_3 = \frac{\partial \mathbf F_1}{\partial (\nabla u)} ,
```

which underworld computes directly from sympy, compiles and registers with PETSc, and from which the Jacobian $K = \partial R/\partial u$ is assembled element by element,

```{math}
:label: eq-jacobian
K_{ij} = \int_\Omega
\phi_i \, G_0 \, \phi_j
\;+\; \phi_i \, G_1 \cdot \nabla\phi_j
\;+\; \nabla\phi_i \cdot G_2 \, \phi_j
\;+\; \nabla\phi_i \cdot G_3 \cdot \nabla\phi_j .
```

$K = \partial R/\partial u$, assembled by {eq}`eq-jacobian`, is the **tangent
stiffness matrix**. For a linear problem it is just the stiffness matrix,
and $R = Ku - f$. For a nonlinear problem, $K(u)$ is the stiffness of the material at
the current solution state. [NEWTON STEP HERE]

## The derivative we want

Write $m$ for a parameter — any quantity the constitutive model carries that
was chosen rather than solved for — and $J(u)$ for the prediction: a scalar
measure of the solution field, since a field itself is not something one can
be sensitive to. The quantity we want is

```{math}
:label: eq-question
\frac{\mathrm d J}{\mathrm d m} ,
```

and it has an obvious answer that is usually the wrong one: change $m$, solve
again, difference the two. That is a full nonlinear solve per parameter, twice
over if the difference is to be centred, and its accuracy is bounded by a step
size chosen between truncation and round-off. For four parameters it is a
nuisance. For the number a real study has, it is the study.

### The terms, and what each one is

The exact route runs through objects a mechanical modeller already has names
for, and it is worth pinning those names down before combining them.





$\partial R/\partial m$ is a **pseudo-load**: the out-of-balance force that
appears if the parameter is nudged and the solution is held still. It is a
force, in the same units and the same space as $R$, and it is where the
parameter enters the problem at all.

$\partial J/\partial u$ is the **measure written as a load**. A scalar measure
of a field has a dual, a vector against which the field is contracted to give
the number; for an integral measure that dual is an ordinary finite-element
load vector, assembled the same way as any other.

### Putting them together

$u$ and $m$ are not independent: they are tied by the residual, which vanishes
at the solution whatever $m$ is. Differentiating $R\big(u(m);\, m\big) = 0$
with respect to $m$,

```{math}
:label: eq-implicit
K\,\frac{\mathrm d u}{\mathrm d m} = -\frac{\partial R}{\partial m},
\qquad \text{so} \qquad
\frac{\mathrm d u}{\mathrm d m} = -K^{-1}\frac{\partial R}{\partial m},
```

which reads as mechanics rather than as calculus: **the sensitivity of the
solution to a parameter is the response of the structure to that parameter's
pseudo-load.** One stiffness, one load, one solve — the same statement as any
other linear analysis, and the reason the derivative is exact rather than
differenced. The measure's derivative then follows by the chain rule:

```{math}
:label: eq-chain
\frac{\mathrm d J}{\mathrm d m}
= \frac{\partial J}{\partial m}
+ \frac{\partial J}{\partial u}\frac{\mathrm d u}{\mathrm d m}
= \frac{\partial J}{\partial m}
- \frac{\partial J}{\partial u}\,K^{-1}\frac{\partial R}{\partial m} .
```

The triple product in the second term can be bracketed from either end, and
that choice is the whole difference between a forward sensitivity and an
adjoint one. Group it as $K^{-1}\big(\partial R/\partial m\big)$ and it is
{eq}`eq-implicit`: solve once per parameter, and get a field each time. Group
it the other way, $\big(\partial J/\partial u\big)K^{-1}$, and one solve
serves every parameter:

```{math}
:label: eq-adjoint
K^{T}\mu = -\frac{\partial J}{\partial u}, \qquad
\frac{\mathrm d J}{\mathrm d m} = \frac{\partial J}{\partial m} + \mu^{T}\frac{\partial R}{\partial m}.
```

$\mu$, the **adjoint state**, is the response of the same structure to the
measure's load: an influence field, in the sense of an influence line. It says
how strongly an out-of-balance force applied anywhere in the domain would tell
on the measure. With it in hand, the derivative for a parameter is
$\mu^{T}\partial R/\partial m$ — the virtual work that parameter's pseudo-load
does against the influence field — and that is an integral, not a solve.

Why the two groupings give the same number is Maxwell–Betti reciprocity: the
work done by one load through the displacements of another equals the work
done by the second through the displacements of the first. The transpose is
what makes it true for a problem whose stiffness is not symmetric.

So the adjoint is cheap in parameters and dear in measures. One solve for ten
parameters or a thousand; another solve for every additional measure. That
suits a model with many dials and one thing you care about, which is the usual
shape of the problem.

### One stiffness, three loads

Newton's own step belongs to the same family as the two sensitivities, and
setting the three side by side is the clearest statement of why the adjoint
costs so little:

```{math}
:label: eq-family
K\,\delta u = -R, \qquad\quad
K\,\frac{\mathrm d u}{\mathrm d m} = -\frac{\partial R}{\partial m},
\qquad\quad
K^{T}\mu = -\frac{\partial J}{\partial u} .
```

The first is the Newton update. Read it the way we read {eq}`eq-implicit` and
it is not a formula from calculus but the same mechanical statement: the
correction to the solution is **the response of the tangent structure to its
own out-of-balance force**. Every Newton iteration hangs the residual on the
structure as a load and asks where it gives. The forward sensitivity hangs the
parameter's pseudo-load on the same structure. The adjoint hangs the measure's
load on it and reads the answer through the transpose. One stiffness, three
right-hand sides — and by the time Newton has converged, that stiffness is
assembled, preconditioned, and evaluated at exactly the state the sensitivities
must be taken at. The adjoint solve costs one more Newton iteration, pointed
backwards.

The family shares its operator but not its tolerance for error in it, and the
reason is what each solve's unknown is *defined by*. The state is defined by
$R(u) = 0$ — a statement of the physics that never mentions the tangent — so
any iterate can be held against it, and $K$ is only scaffolding: a
frozen-viscosity tangent bends the path, the residual check straightens it,
and the answer costs iterations, never correctness. That is why Picard works
at all, and why a converged state does not remember which tangent found it.

The adjoint state has no such definition to be checked against. Its *only*
defining equation is {eq}`eq-adjoint`, and the tangent is inside it. A residual
for that linear system can certainly be formed — the Krylov solver drives it to
zero — but it certifies the arithmetic of whatever operator it was handed, not
the physics: solve with an inconsistent tangent and the result is a different
$\mu$, satisfying its own equation to machine precision. Residual zero, answer
wrong. The one check that does not route through the tangent is a finite
difference of the forward problem — the Taylor test — and that is exactly the
cost the adjoint exists to avoid, so it is a validation run once, not a guard
the solve can carry.

There is a second way to say this, and it is the sharper one. The adjoint is a
constrained solve. Write the Lagrangian $L = J(u) + \mu^{T} R(u;\, m)$ and
{eq}`eq-adjoint` is its stationarity in $u$: $\mu$ is the multiplier attached
to the constraint that $u$ solves the forward problem *exactly*, the same
office the pressure holds for incompressibility, and the coupled system for
$(u, \mu)$ has the same saddle shape. A multiplier is defined only on the
constraint manifold. At a state that does not satisfy $R = 0$ — an unconverged
solve, a linearisation somewhere the iteration never reached — the multiplier
is not inaccurate but undefined, and where the constraint leaves the state
free it is non-unique as well, exactly as the pressure is on an enclosed
domain. That is the second reason no residual can bring an inexact adjoint
solve back: not only would the check route through the same tangent, but off
the manifold there is nothing for it to measure the distance to. It is also
why the library refuses to take the adjoint of a solve that did not converge,
rather than doing its best with the state it has.

The forgiveness lost here is restored one level up, and for the same reason
Newton had it. An inversion evaluates the misfit at each new parameter set by
solving the forward problem to convergence — on the manifold, exactly — so the
outer loop owns a computable check, as the Newton iteration owned its residual.
Against that check, an unstructured error in $\mu$ from a loose tolerance on
the adjoint solve costs optimisation iterations and nothing else: the direction
is slightly askew, it still descends, and the fresh misfit keeps score. The
inconsistent tangent gets no such rescue, because its error is systematic — it
is the exact gradient of a different problem, vanishing at a different point,
and the optimiser will follow it faithfully to the wrong minimum. How much
accuracy the gradient actually needs is set by what the optimiser does with
it: a descent method needs only the sign to be right in projection, while a
quasi-Newton method differences successive gradients to build its curvature
model, so gradient error pollutes the model and the superlinear rate is the
first casualty.

What {eq}`eq-adjoint` asks for is a transposed tangent stiffness and the
derivative of the residual with respect to a parameter. Neither is a new
object.

## The same blocks give the derivative

Both pieces are {eq}`eq-blocks` read differently.

**The transposed stiffness is a relabelling.** $K^{T}$ is the bilinear form of
{eq}`eq-jacobian` with trial and test exchanged. Exchanging $\phi_i$ and
$\phi_j$ leaves the two diagonal terms in place, transposed on their paired
indices, and swaps the two mixed ones — the $G_1$ term becomes a $G_2$ term
and the other way about:

```{math}
:label: eq-transpose
G_0^{T} \;\rightarrow\; G_0, \qquad
G_3^{T} \;\rightarrow\; G_3, \qquad
G_1 \;\leftrightarrow\; G_2 .
```

So the adjoint operator is assembled from the *same four compiled kernels*,
registered in a different arrangement. We do that wherever the kernels carry
the whole operator, rather than transposing an assembled matrix, which matters
for Stokes, where the $(u,p)$ and $(p,u)$ blocks exchange places by the same
rule and the composite operator stays a composite operator the Krylov solver
can be preconditioned against. Nothing is differentiated a second time, and the
assembled operator agrees with the explicit transpose to $10^{-16}$.

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

**The parameter derivative is the same `diff`, on a different symbol.**
A named quantity $m$ — a friction coefficient, a reference viscosity, a
continuation parameter — survives into $F_0$ and $\mathbf F_1$ as a symbol,
because the solver carries the constitutive model's own expression rather than
the number it currently holds. Differentiating {eq}`eq-residual` with respect
to $m$ instead of $u$ is the same operation that produced {eq}`eq-blocks`:

```{math}
:label: eq-drdm
\frac{\partial R}{\partial m} \;=\;
\int_\Omega \frac{\partial F_0}{\partial m}\,\phi
\;+\; \frac{\partial \mathbf F_1}{\partial m}\cdot\nabla\phi .
```

The one trap is early substitution. If the parameter's value has been folded
into the expression before differentiation the derivative is zero, correctly
and uselessly, so the sensitivity expands every *other* named expression first
and leaves $m$ standing.

## The adjoint of one solve

In the library {eq}`eq-adjoint` is one call, `solver.gradient(misfit, parameters=..., fields=...)`,
made of three steps. `misfit_duals` assembles $\partial J/\partial u$ as a
load, $\int g_0\,\phi_j + \mathbf g_1\cdot\nabla\phi_j$, where $g_0$ and
$\mathbf g_1$ are the symbolic derivatives of the misfit integrand with
respect to $u$ and $\nabla u$ — the same decomposition as the residual, which
is why a misfit on a stress needs no integration by parts and produces no
boundary term: it reads the velocity through its gradient, and
$\mathbf g_1$ carries it. `adjoint_solve` registers the kernels of
{eq}`eq-transpose` where they carry the operator, lets the SNES assemble, and
solves with its own Krylov solver and preconditioner; where they do not it
transposes the assembled operator and solves that forwards with the same
solver. `sensitivity` forms $\mu^{T}\partial R/\partial m$
from {eq}`eq-drdm`.

### A number or a field

What the call is asked to differentiate with respect to comes in two kinds,
and they enter the calculation in different places.

A **scalar parameter** is a named expression the residual holds as a symbol —
a friction coefficient, a reference viscosity, a viscosity floor. Its
derivative is {eq}`eq-drdm` contracted against $\mu$: one integral, one
number.

A **field** is a mesh variable the residual reads — a viscosity painted cell
by cell, a density, an initial temperature. Differentiating the residual with
respect to it gives not a number but a load on that field's own space, one
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

out = stokes.gradient(J, parameters=[eta_min], fields=[eta0])

out["J"]                   # the measure itself
out["parameters"][eta_min] # dJ/d(eta_min): a float
out["fields"][eta0]        # dJ/d(eta0): an array on eta0's nodes, the map
```

A scalar costs an integral after the adjoint solve and a field costs a load
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
bound, $\eta = \max(\eta_{\rm eff}, \eta_{\min})$, so $\partial R/\partial
\eta_{\min}$ vanishes wherever the material is stiffer than the floor, and
the sensitivity is an integral over the cells the floor is holding up (rounded
over a narrow band when the bound is smoothed). The same field that gives the
number shows where the floor is doing its work.

TODO: the notch — $\mathrm dJ/\mathrm d\eta_{\min}$ against $\eta_{\min}$ and
the iteration count at each floor.

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
