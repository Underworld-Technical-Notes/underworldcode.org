# Merge report — `particles-in-underworld3`

Prose from the published article, structure from the drafted original.

- **took-published**: 7
- **kept-original**: 9
- **added-in-ghost**: 2

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.

*None.*

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: In Underworld3, swarm variables are symbolic objects. A particle-carried quantity has a `.sym` property that returns a SymPy symbol, just like a mesh variable. That symbol particip
  <br>published: A swarm variable has a `.sym` property that returns a SymPy symbol, just like a mesh variable. That symbol participates in the solver's weak form, the constitutive model, the bound
- draft: In UW2, the user managed this explicitly. You would call a projection routine before each solve, mapping particle data onto the mesh. Forget the projection, and the solver uses sta
  <br>published: In Underworld2, the user managed this explicitly. You would call a projection routine before each solve, mapping particle data onto the mesh. Forget the projection, and the solver 
- draft: UW3 automates this through the proxy mesh variable pattern.
  <br>published: UW3 automates this through a ***"proxy mesh variable"*** pattern.
- draft: 1. Build a KDTree of all particle positions on the local rank. 2. For each mesh node at position $x _ n$, find the $k$ nearest particles ($k = \text{dim} + 1$ by default), giving n
  <br>published: 1. Build a KDTree of all particle positions on the local rank.
- draft: $$ w _ i = \frac{1}{\left(\epsilon + d _ i^2\right)^p}, \qquad \phi _ n = \frac{\sum _ {i=1}^{k} w _ i \, \phi _ p^{(i)}}{\sum _ {i=1}^{k} w _ i} $$
  <br>published: 2. For each mesh node at position $x _ n$, find the $k$ nearest particles ($k = \text{dim} + 1$ by default), giving neighbour positions $x _ p^{(i)}$ and values $\phi _ p^{(i)}$ fo
- draft: 4. Store the result $\phi _ n$ on the proxy mesh variable.
  <br>published: 1. Store the result $\phi _ n$ on the proxy mesh variable.
- draft: The same pattern works for stress history in viscoelastic models, where the DFDt infrastructure stores previous stress values on swarm variables with proxies. The constitutive mode
  <br>published: The same pattern works for stress history in viscoelastic models. The DFDt infrastructure stores previous stress values on a swarm variable like the `stress_history` declared above

## Structure kept from the draft

3 block(s): code
