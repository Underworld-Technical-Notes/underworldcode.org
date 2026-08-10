**Underworld is a mathematically self-describing, parallel finite-element code
for geodynamics.** You write the physics as symbolic mathematics in Python;
Underworld turns it into compiled C and solves it on anything from a laptop to
a supercomputer, without you rewriting it in between.

It is particle-in-cell: a mesh carries the finite-element solution while a swarm
of Lagrangian particles carries history — stress, composition, damage — through
the large deformations that geological materials undergo. The mesh does not have
to follow the material, which is what makes long-timescale problems tractable.

## The documentation

> **[underworld3.readthedocs.io](https://underworld3.readthedocs.io/en/latest/)**
> — installation, tutorials, worked examples and the full API reference.

That is the source of everything about using the code, and it is generated from
the repository, so it is current by construction. This page deliberately does
not repeat it.

- **Source code:** [github.com/underworldcode/underworld3](https://github.com/underworldcode/underworld3)
  (LGPL-3; notebooks and documentation CC-BY-4.0)
- **Questions and bugs:** [open an issue](https://github.com/underworldcode/underworld3/issues)
- **Try it now, nothing to install:** [run it in the cloud](/auscope-cloud/)
- **How to cite it:** [see the citation page](/how-to-cite-underworld/)

## Underworld 2 and Underworld3

**Underworld3** is the current code. It is a rewrite rather than a revision: the
symbolic layer, the coordinate systems, curved boundaries, composable
constitutive models and swappable time derivatives are new, and PETSc's
nonlinear solvers are used directly rather than through a framework of our own.

**Underworld 2** is still available and still works
([github.com/underworldcode/underworld2](https://github.com/underworldcode/underworld2)).
**UWGeodynamics has been rolled into Underworld 2**, so its functionality lives
there and its own repository is archived.

If you are starting now, start with Underworld3. Why the rewrite happened, and
what it bought, is the subject of a note:
[Our Journey from Underworld2 to Underworld3](/our-journey-from-underworld2-to-underworld3/).

## Where the ideas are written up

The [Technical Notes](/notes/) explain how the code works and why —
each one citable, with an archival PDF. The methods behind it are published;
the [citation page](/how-to-cite-underworld/) lists the papers for the code and
for the underlying algorithms.
