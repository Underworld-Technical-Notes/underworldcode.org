<!--
The front page's prose. Hand-written and meant to be edited: this is the first
thing a visitor reads, and it should sound like a person rather than a
generator.

`scripts/build_index.py` wraps this with the feeds. Three markers are replaced
at build time and must each appear exactly once:

    <!-- LATEST-POSTS -->   the news, releases and guides, newest first
    <!-- LATEST-NOTES -->   the three most recent technical notes, in brief
    <!-- COUNTS -->         how many notes, how many with a DOI

Everything else here is passed through as MyST markdown.
-->

<div class="uwtn-hero"><div class="uwtn-hero-text"><div class="uwtn-kicker">Geodynamics</div><div class="uwtn-hero-title">Underworld</div><div class="uwtn-standfirst">A parallel, particle-in-cell finite element code for modelling the solid Earth as a complex fluid — from a laptop to a supercomputer, driven from Python.</div><div class="uwtn-hero-actions"><a class="uwtn-cta" href="https://github.com/underworldcode/underworld3">Get the code</a><a href="/intro-to-underworld/">What is Underworld?</a><a href="/notes/">Technical Notes</a></div></div></div>

Underworld solves the equations of slow, viscous flow on a finite element mesh
while carrying material history on particles that move through it. That
combination is what lets a model track stress, damage and composition through
the very large deformations that geology produces — mountain building,
subduction, mantle convection over hundreds of millions of years.

The current version, **Underworld 3**, is a ground-up rewrite. Models are
written as symbolic expressions in [SymPy](https://www.sympy.org), which the
code compiles to C and hands to [PETSc](https://petsc.org) to solve. You write
the physics; the machinery for discretising, differentiating and solving it is
generated. There is [a note on how that works](/how-underworld3-turns-sympy-into-c/).

Underworld is open source, developed in the open, and supported by
[AuScope](https://www.auscope.org.au/) under the Australian Government's NCRIS
programme.

<div class="uwtn-section">Technical Notes</div>

<!-- COUNTS -->

<!-- LATEST-NOTES -->

<div class="uwtn-section">Latest</div>

<div class="uwtn-section-note">News, releases, and guides to getting Underworld running.</div>

<!-- LATEST-POSTS -->
