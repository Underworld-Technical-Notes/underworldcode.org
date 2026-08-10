---
title: Underworld 2.10
description: "Underworld 2.10 has dropped... kidding this is a benchmark model proposed by Schmalholz, 2011, A simple analytical solution for slab detachment."
date: 2020-09-04
authors:
  - name: Julian Giordani
    orcid: 0000-0003-4515-9296
    affiliations:
      - University of Sydney
  - name: John Mansour
    orcid: 0000-0001-5865-1664
    affiliations:
      - Monash University
doi: 10.59350/dwxt3-tgj66
license: CC-BY-4.0
banner: figures/banner.png
keywords:
  - Underworld Code
parts:
  abstract: "Underworld 2.10 has dropped... kidding this is a benchmark model proposed by Schmalholz, 2011, A simple analytical solution for slab detachment."
---
<div class="uwtn-banner"><img src="figures/banner.png" alt=""></div>

Underworld 2.10 has been released!

Available via *docker* (recommended), *pip* and *source code*.  
See [here](https://github.com/underworldcode/underworld2/blob/v2.10.1b/Installation.rst) for more information on each install process.

For a *quick* taste of Underworld try our binder cloud resource, a temporary "virtual sandbox" to explore the release and example models. Click the button below.

:::{list-table}
:header-rows: 0

* - :::{image} figures/badge_logo.svg
    :alt: Binder
    :width: 109px
    :::
  - [mybinder.org/v2](https://mybinder.org/v2/gh/underworldcode/underworld2/v2.10.1b)
:::

---

This new release includes the following:

#### Enhancements

- Using UWGeodynamics-2.10.1, see [here](https://github.com/underworldcode/UWGeodynamics/tree/v2.10.1).

- All provided example model files are now parallel "safe". Reasonable number of processors must still be used.

- Improved regression testing: now testing parallel execution and "long_tests.sh".

- Add Dockerfile for Deepnote.

- Upgrade dependecy packages:

- petsc-3.12.3

- Ubuntu-20.04

- Numpy-1.19

- Swig4

#### User changes

- Update to the `underworld.visualisation` package. See [here](https://github.com/underworldcode/underworld2/commit/61b1db7239b12c853c3338b18cc24d03e86e9f95).

As always the Underworld team welcomes contact via our GitHub [Issue tracker](https://github.com/underworldcode/underworld2/issues), where questions and issues can be posted to the Underworld community.  
  
Good luck, wash those hands and have fun modelling!

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=underworld-2-10">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=underworld-2-10">Start one</a></div></div>
