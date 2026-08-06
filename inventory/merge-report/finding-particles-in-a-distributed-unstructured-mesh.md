# Merge report — `finding-particles-in-a-distributed-unstructured-mesh`

Prose from the published article, structure from the drafted original.

- **took-published**: 16
- **kept-original**: 6
- **added-in-ghost**: 1
- **dropped-from-draft**: 23

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.

- *(heading, too short to locate)* ## What Is Not Automatic
- *(heading, too short to locate)* ## The Full Timestep
- *(rule, too short to locate)* ---
- *(prose, published in particles-in-underworld3, physical-units-in-computational-geodynamics, how-underworld3-turns-sympy-into-c)* *The Underworld project is supported by AuScope and the Australian Government through the National Collaborative Research Infrastructure Strategy (NCR

### Never published — decide whether to restore

- *(prose)* *An unstructured triangulation with a highlighted element. Each face carries a pair of control points: one just inside the cell (black) and one just outside (rust). A test point is connected to the marker on the same side of each face as the centroid: $x_q$ — interior — lands on three black markers;
- *(prose)* This approach is exact for linear meshes where faces are planar. For higher-order elements with curved faces, it is approximate but sufficient for particle location.
- *(prose)* *A mesh decomposed into four processor domains. The particle $x _ p$ is inside domain B but closer to domain A's centroid $c _ A$ than to $c _ B$. A nearest-centroid assignment would send the particle to the wrong processor. Dashed lines show distances to all four domain centroids. The domain shapes
- *(prose)* *Each panel shows one domain's view. Dark shading marks the region that is clearly inside (far from any boundary control point). Light shading marks the boundary zone where the sign of the nearest control point is not reliable. White is clearly outside. Black dots are inside control points; grey dot
- *(prose)* Particles are created by populating a swarm on the mesh:
- *(code)* ```python swarm = uw.swarm.Swarm(mesh) swarm.populate(fill_param=3) ```
- *(prose)* The `fill_param` controls density. It places particles at the locations of discontinuous basis functions of degree `fill_param` within each cell. At `fill_param=3`, this gives roughly 10 particles per cell in 2D and 20 in 3D. The distribution is designed to be well-suited for numerical integration a
- *(prose)* Particles can also be added manually:
- *(code)* ```python swarm.add_particles_with_coordinates(local_coords) ```
- *(prose)* This is a local operation. Each rank adds particles in its own domain. For placing particles across all ranks from a single coordinate array, `add_particles_with_global_coordinates()` handles the distribution and migration collectively.
- *(heading)* ## Swarm Variables and Solvers
- *(prose)* Particles carry data through swarm variables. Each variable is stored as a PETSc field on the DMSwarm, so when particles migrate, their data travels with them automatically. How that data participates in the finite element solver — projection onto the mesh, lazy evaluation, symbolic integration — is
- *(prose)* UW3 does not currently perform active population control. If particles cluster in a convergence zone or deplete in a divergence zone, the user is responsible for adding or removing particles. The `add_particles_with_coordinates()` method handles insertion, but deciding when and where to add particle
- *(prose)* This is a known limitation and an area where contributions are welcome. Population control strategies exist in the literature, but implementing them well in parallel, without introducing artefacts, is non-trivial.
- *(prose)* From this post's perspective, the particle-relevant part of a timestep is:
- *(prose)* 1. **Advect**: Particle coordinates are updated using the velocity solution.
- *(prose)* 2. **Locate**: Each particle is tested against its current cell using the face control point test. Particles that have left their cell are relocated using the KDTree lookup.
- *(prose)* 3. **Migrate**: Particles that crossed processor boundaries are sent to their new owners via the centroid hinting and ownership verification described above. PETSc exchanges particle coordinates and all swarm variable data between ranks.
- *(prose)* How the solver uses particle data, and how swarm variables participate in the weak form, is the subject of a companion post.

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: Given a point $x$ and an unstructured mesh of convex cells, which cell contains $x$? On a structured grid you compute an index. On an unstructured mesh, you have to test cells unti
  <br>published: Given a point $\mathbf{x}$ and an unstructured mesh of convex cells, which cell contains $\mathbf{x}$?
- draft: Testing whether a point is inside a convex cell is straightforward in principle. Each face of the cell defines a half-space. If the point is on the interior side of every face, it 
  <br>published: On a structured grid you compute an index. On an unstructured mesh, you have to test cells until you find one that contains the point. Testing whether a point is inside a convex ce
- draft: A naive approach would be to find the cell whose centroid is nearest to the particle. This fails for unstructured meshes. In a Delaunay triangulation, cells can be far from equilat
  <br>published: A first-pass approach might be to find the cell whose centroid is nearest to the particle. This is likely to be very close to the actual cell containing the particle, but it is not
- draft: ![Inside/outside test for a triangular cell](figures/finding-particles/mesh-demo.png)
  <br>published: ```{figure} figures/mesh-demo.svg :alt: Inside/outside test for a triangular cell An unstructured triangulation with a highlighted element. Each face carries a pair of control poin
- draft: No normals, no dot products, no plane equations at query time. The geometry was baked into the control point positions during mesh setup. The computation is vectorised over all par
  <br>published: This approach is exact for linear meshes (where faces are planar).
- draft: ![Domain centroid ambiguity in a parallel mesh](figures/finding-particles/domain-demo.png)
  <br>published: ```{figure} figures/domain-demo.svg :alt: Domain centroid ambiguity in a parallel mesh A mesh decomposed into four processor domains. The particle $x _ p$ is inside domain B but cl
- draft: ![Boundary ownership test from each domain's perspective](figures/finding-particles/boundary-demo.png)
  <br>published: ```{figure} figures/boundary-demo.svg :alt: Boundary ownership test from each domain's perspective Each panel shows one domain's view. Dark shading marks the region that is clearly
- draft: ### Putting Migration Together
  <br>published: ### Example: making `dm.migrate()` fast
- draft: The full migration sequence is iterative:
  <br>published: Migration is the parallel-only cost of working with particles. As particles move through the physical domain, they will often change their owning process. They, and their data cont
- draft: 1. Check which particles are still inside the local domain using the ownership test.
  <br>published: The global centroid KDTree is the key piece. Each rank computes its own domain centroid and shares it once — a small array, replicated on every rank, refreshed only when the decomp
- draft: 2. For particles that are outside, query the domain centroid KDTree to find the closest rank. Assign the particle to that rank.
  <br>published: What follows is a short negotiation scoped to the candidate peers — each rank tells its candidates how many particles are coming, and learns the same from any candidate sending to 
- draft: 3. Call PETSc's `dm.migrate()` to exchange particles between ranks. PETSc handles the MPI communication: packing particle coordinates and all swarm variable data, sending to the ta
  <br>published: Some particles still arrive at the wrong rank — the centroid prediction is a heuristic and can be imprecise near irregular boundary zones (see the figure above). The receiving rank
- draft: 4. The receiving rank runs the ownership test. Some particles may have been sent to the wrong rank (nearest centroid, but not the owning domain). For these, query the next-closest 
  <br>published: The centroid KDTree is a cheap ingredient that buys the whole architecture. Cost is local; communication is point-to-point; no rank ever needs to know what any other rank is holdin
- draft: 5. After a fixed number of iterations, any particles still unlocated are deleted. These are typically particles that have left the mesh entirely.
  <br>published: ### A Second Example: `global_evaluate()`
- draft: In practice, most particles arrive at the correct rank on the first attempt. The iteration catches the edge cases near irregular boundaries.
  <br>published: The same predict-then-send pattern underlies `uw.function.global_evaluate(expr, coords)`, which evaluates a symbolic expression at a set of points that may live on any rank. Interp
- draft: ## Creating Particles
  <br>published: UW3 implements this as a round-trip `migrate`. Each rank wraps its query points in a temporary evaluation swarm, with each point labelled by its origin rank and original index. The

## Structure kept from the draft

1 block(s): math
