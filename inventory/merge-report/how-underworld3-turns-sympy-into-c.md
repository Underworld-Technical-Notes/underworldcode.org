# Merge report — `how-underworld3-turns-sympy-into-c`

Prose from the published article, structure from the drafted original.

- **took-published**: 3
- **kept-original**: 6
- **added-in-ghost**: 7
- **dropped-from-draft**: 1

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.


### Never published — decide whether to restore

- *(prose)* *[Screenshot: F0 and F1 as rendered in a Jupyter notebook — the full mathematical form of the body force and constitutive stress, with the Frank-Kamenetskii viscosity visible inside the flux.]*

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: <!-- NOTEBOOK SCREENSHOT: Insert screenshot from sympy-to-c-pipeline-notebook.ipynb showing stokes.F0, stokes.F1, and/or stokes.constitutive_model.flux rendered as LaTeX in a Jupyt
  <br>published: ```{figure} figures/Screenshot-2026-03-30-at-3.53.35-pm.png Screenshot: F0 and F1 as rendered in a Jupyter notebook — the full mathematical form of the body force and constitutive 
- draft: The solver takes F0 and F1 and differentiates them with respect to the unknown field and its gradient, producing four Jacobian blocks:
  <br>published: The solver takes $F_0$ and $F_1$ and differentiates them with respect to the unknown field and its gradient, producing four Jacobian blocks:
- draft: ``` G0 = ∂F0/∂u G1 = ∂F0/∂(∇u) G2 = ∂F1/∂u G3 = ∂F1/∂(∇u) ```
  <br>published: $G_0 = ∂F_0/∂u$ $G_1 = ∂F_0/∂(∇u)$ $G_2 = ∂F_1/∂u$ $G_3 = ∂F_1/∂(∇u)$

## Structure kept from the draft

2 block(s): code, math
