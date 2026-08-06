# Merge report — `mesh-variables-and-petsc-vectors-keeping-arrays-in-sync`

Prose from the published article, structure from the drafted original.

- **took-published**: 7
- **kept-original**: 3
- **added-in-ghost**: 4
- **dropped-from-draft**: 3

## Blocks dropped from the draft

These were in the drafted original but are not prose in the merged article. Each is checked against the whole published corpus, because a block can survive in another form — a caption that became a `<figcaption>` — or be published in a different article when a draft was split. Only **NOT PUBLISHED** is a real editorial decision.

- *(rule, too short to locate)* ---
- *(prose, published in particles-in-underworld3, physical-units-in-computational-geodynamics, how-underworld3-turns-sympy-into-c)* *The Underworld project is supported by AuScope and the Australian Government through the National Collaborative Research Infrastructure Strategy (NCR

### Never published — decide whether to restore

- *(prose)* In Underworld2, the answer was context managers. You wrapped every data access in a `with` block, and the framework synchronised the arrays on exit. It was safe, but verbose — and forgetting the context manager was a silent bug.

## Prose taken from the published article

The draft wording is shown first, the published wording second.

- draft: One of the less glamorous but most important problems in a finite element framework is this: how does the user assign values to a field variable, and how does the framework ensure 
  <br>published: In Underworld2, the answer was context managers. You would wrap every data access in a `with` block, and the framework synchronised the arrays on exit. It was safe, but verbose.
- draft: This post explains how that works.
  <br>published: This post explains how we make that work.
- draft: 1. Values are written into the PETSc local vector 2. A local-to-global scatter copies owned values to the global vector 3. A global-to-local scatter fills ghost regions from neighb
  <br>published: 1. Values are written into the PETSc local vector
- draft: - A new MeshVariable is added to the mesh (triggers a DM rebuild) - The mesh adapts (new topology, new vectors)
  <br>published: - A new MeshVariable is added to the mesh (triggers a DM rebuild)
- draft: UW3 solves this with a single line of defence: on every `.data` access, it checks whether `id(self._lvec)` matches the cached value. Python's `id()` returns the memory address of a
  <br>published: UW3 solves this with a single line of defence: on every `.data` or `.array` access, it checks whether `id(self._lvec)` matches the cached value. Python's `id()` returns the memory 
- draft: For most user code, `.data` is sufficient. `.array` is there when you want the structured shape or unit handling.
  <br>published: For most user code, `.array` is a good choice. `.data` is there when you want to avoid the overhead of unit converstions or resizing (for example, copying from one array to another
- draft: The division is clean: users work through `.data` (safe, synchronised, cached). Solvers work through `.vec` (direct, fast, PETSc-native). The two paths share the same underlying me
  <br>published: The division is clean: users work through `.array` (safe, synchronised, cached). Solvers work through `.vec` (direct, fast, PETSc-native). The two paths share the same underlying m

## Structure kept from the draft

2 block(s): code
