# Merge report — `particles-in-underworld3`

Prose from the published article, structure from the drafted original.

- **took-published**: 3
- **kept-original**: 1
- **added-in-ghost**: 3

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.

*None.*

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: 1. Build a KDTree of all particle positions on the local rank. 2. For each mesh node at position $x _ n$, find the $k$ nearest particles ($k = \text{dim} + 1$ by default), giving n
  <br>published: 1. Build a KDTree of all particle positions on the local rank.
- draft: $$ w _ i = \frac{1}{\left(\epsilon + d _ i^2\right)^p}, \qquad \phi _ n = \frac{\sum _ {i=1}^{k} w _ i \, \phi _ p^{(i)}}{\sum _ {i=1}^{k} w _ i} $$
  <br>published: 2. For each mesh node at position $x _ n$, find the $k$ nearest particles ($k = \text{dim} + 1$ by default), giving neighbour positions $x _ p^{(i)}$ and values $\phi _ p^{(i)}$ fo
- draft: 4. Store the result $\phi _ n$ on the proxy mesh variable.
  <br>published: 1. Store the result $\phi _ n$ on the proxy mesh variable.

## Maths repaired from the draft

Ghost's editor removed characters from LaTeX on the way in. Where the published prose was kept, its maths was restored from the draft.

- published `w _ i = \frac{1}{\left(\epsilon + d _ i^2\right)p}, \qquad  
\phi _ n = \frac{\sum _ {i=1}^{k} w _ i , \phi _ `
  <br>restored `w _ i = \frac{1}{\left(\epsilon + d _ i^2\right)^p}, \qquad
\phi _ n = \frac{\sum _ {i=1}^{k} w _ i \, \phi _ `
- published `d _ i^2 = | x _ n - x _ p^{(i)} |^2`
  <br>restored `d _ i^2 = \| x _ n - x _ p^{(i)} \|^2`

## Structure kept from the draft

0 block(s): none
