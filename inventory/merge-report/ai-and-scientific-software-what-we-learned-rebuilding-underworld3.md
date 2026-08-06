# Merge report — `ai-and-scientific-software-what-we-learned-rebuilding-underworld3`

Prose from the published article, structure from the drafted original.

- **took-published**: 5
- **kept-original**: 22
- **added-in-ghost**: 5
- **dropped-from-draft**: 2

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.

- *(heading, too short to locate)* ### Example Interaction

### Never published — decide whether to restore

- *(prose)* Underworld3 has about 50,000 lines of Python/Cython wrapping PETSc, SymPy, and a just-in-time compiler. I began a trial of AI coding tools in 2025 and they have gradually become central to the way our team works. This is a story of co-evolution as much as it is about adoption of a new set of tools.

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: ``` > stokes.constitutive_model.flux σ = 2 · 1 · ε̇(u) ```
  <br>published: > stokes.constitutive_model.flux
- draft: The viscosity is 1 — the default value. Your depth-dependent expression isn't reaching the solver. You defined:
  <br>published: \boldsymbol{\sigma} = 2 \cdot 1 \cdot \dot{\boldsymbol{\epsilon}}(\mathbf{u})
- draft: ``` > viscosity_fn η₀ · exp(-γ · y) ```
  <br>published: The viscosity is 1 — the default value. Your depth-dependent
- draft: ``` > stokes.constitutive_model.Parameters.viscosity = viscosity_fn ```
  <br>published: > stokes.constitutive_model.Parameters.viscosity = viscosity_fn
- draft: ``` σ = 2 η₀ exp(-γ y) ε̇(u) ```
  <br>published: \boldsymbol{\sigma} = 2 \eta_0 \exp(-\gamma y) \dot{\boldsymbol{\epsilon}}(\mathbf{u})

## Structure kept from the draft

0 block(s): none
