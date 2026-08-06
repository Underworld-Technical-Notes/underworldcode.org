# Merge report — `finding-particles-in-a-distributed-unstructured-mesh`

Prose from the published article, structure from the drafted original.

- **took-published**: 5
- **kept-original**: 3
- **dropped-from-draft**: 6

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.

- *(rule, too short to locate)* ---
- *(prose, published in particles-in-underworld3, physical-units-in-computational-geodynamics, how-underworld3-turns-sympy-into-c)* *The Underworld project is supported by AuScope and the Australian Government through the National Collaborative Research Infrastructure Strategy (NCR

### Never published — decide whether to restore

- *(prose)* *Control points used for cell location: the cell centroid $c$ plus one nudge point per vertex ($c _ 1$, $c _ 2$, $c _ 3$, each 1% from $v _ i$ toward $c$). **Left (normal cell):** a test point $x _ p$ near the acute vertex $v _ 1$ is closer to the neighbouring centroid $c'$ (rust line) than to the h
- *(prose)* *An unstructured triangulation with a highlighted element. Each face carries a pair of control points: one just inside the cell (black) and one just outside (rust). A test point is connected to the marker on the same side of each face as the centroid: $x _ q$ — interior — lands on three black marker
- *(prose)* *A mesh decomposed into four processor domains. The particle $x _ p$ is inside domain B but closer to domain A's centroid $c _ A$ than to $c _ B$. A nearest-centroid assignment would send the particle to the wrong processor. Dashed lines show distances to all four domain centroids. The domain shapes
- *(prose)* *Each panel shows one domain's view. Dark shading marks the region that is clearly inside (far from any boundary control point). Light shading marks the boundary zone where the sign of the nearest control point is not reliable. White is clearly outside. Black dots are inside control points; grey dot

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: Given a point $x$ and an unstructured mesh of convex cells, which cell contains $x$?
  <br>published: Given a point $\mathbf{x}$ and an unstructured mesh of convex cells, which cell contains $\mathbf{x}$?
- draft: ![Control points used for cell location: a normal cell and a sliver edge case](figures/finding-particles/element-location-demo.png)
  <br>published: ```{figure} figures/element-location-demo.svg :alt: Control points used for cell location: a normal cell and a sliver edge case **Control points used for cell location: the cell ce
- draft: ![Inside/outside test for a triangular cell](figures/finding-particles/mesh-demo.png)
  <br>published: ```{figure} figures/mesh-demo.svg :alt: Inside/outside test for a triangular cell An unstructured triangulation with a highlighted element. Each face carries a pair of control poin
- draft: ![Domain centroid ambiguity in a parallel mesh](figures/finding-particles/domain-demo.png)
  <br>published: ```{figure} figures/domain-demo.svg :alt: Domain centroid ambiguity in a parallel mesh A mesh decomposed into four processor domains. The particle $x _ p$ is inside domain B but cl
- draft: ![Boundary ownership test from each domain's perspective](figures/finding-particles/boundary-demo.png)
  <br>published: ```{figure} figures/boundary-demo.svg :alt: Boundary ownership test from each domain's perspective Each panel shows one domain's view. Dark shading marks the region that is clearly

## Maths repaired from the draft

Ghost's editor removed characters from LaTeX on the way in. Where the published prose was kept, its maths was restored from the draft.

*None.*

## Structure kept from the draft

1 block(s): math
