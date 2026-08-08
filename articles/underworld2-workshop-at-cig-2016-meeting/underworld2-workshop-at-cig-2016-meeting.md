---
title: Underworld2 Workshop at CIG 2016 Meeting
date: 2016-02-29
authors:
  - name: John Mansour
    orcid: 0000-0001-5865-1664
    affiliations:
      - Monash University
doi: 10.59350/m1brb-ah254
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Underworld Code
  - Underworld Workshops
exports:
  - format: typst
    template: ../../templates/pdf
    output: underworld2-workshop-at-cig-2016-meeting.pdf
    article_id: UWTN 2016-001
    article_version: 1.0.0
parts:
  abstract: "Underworld2 is a python-friendly version of the Underworld geodynamics code which provides a programmable and flexible front end to all the functionality of the code running in a parallel HPC environment. This gives signficant advantages to the user, with access to the power of python libraries for setup of complex problems, analysis at runtime, problem steering, and coupling of multiple problems. Underworld2 is integrated with the literate programming environment of the jupyter notebook [https:"
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

*Underworld2 is a python-friendly version of the Underworld geodynamics code which provides a programmable and flexible front end to all the functionality of the code running in a parallel HPC environment. This gives signficant advantages to the user, with access to the power of python libraries for setup of complex problems, analysis at runtime, problem steering, and coupling of multiple problems. Underworld2 is integrated with the literate programming environment of the [jupyter notebook](https://jupyter.org/) system for tutorials and as a teaching tool for solid Earth geoscience.*

## INSTRUCTORS

- Louis Moresi (University of Melbourne)

- John Mansour (Monash University )

## AGENDA

We will give a from-scratch overview of the python-based [Underworld2 code](/) using examples of interest to the mantle and lithospheric dynamics communities.

- Getting started with Underworld / iPython notebooks

- Introduction to the algorithms (PIC / FEM) and python constructs

- Setting up a problem / examples

- Solvers and equation systems

- Parallel code

- Moving to a supercomputer / batch environment

Our goal is to have people leave the workshop with a functioning version of Underworld and enough knowledge to tinker with the simple examples.

## SOFTWARE REQUIREMENTS

Docker Underworld images are the preferred avenue for Underworld usage.

**Mac / Windows**:  [Kitematic Docker GUI](https://kitematic.com/). Details on installing Underworld2 via Kitematic are available [here](/posts/Underworld-and-Dockers2).

**Linux**: Docker toolbox (see [https://docs.docker.com/linux/](https://docs.docker.com/linux/) for linux specific information). An overview of dockers, as well as details on installing Underworld2 via the docker command line interface is available [here](/posts/Underworld-and-Dockers).

Those wishing to compile natively are directed to the [Underworld2 github](https://github.com/underworldcode/underworld2/) page for details.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=underworld2-workshop-at-cig-2016-meeting">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=underworld2-workshop-at-cig-2016-meeting">Start one</a></div></div>
