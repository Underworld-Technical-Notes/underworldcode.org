---
title: Underworld 2.11 Scaling
date: 2021-09-30
authors:
  - name: Julian Giordani
    orcid: 0000-0003-4515-9296
    affiliations:
      - University of Sydney
  - name: John Mansour
    orcid: 0000-0001-5865-1664
    affiliations:
      - Monash University
doi: 10.59350/3wz3c-c8w65
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Underworld Code
  - Documentation
exports:
  - format: typst
    origin_url: https://www.underworldcode.org/2-11-scaling/
    template: ../../templates/pdf
    output: 2-11-scaling.pdf
    article_id: UWTN 2021-004
    article_version: 1.0.0
parts:
  abstract: "How does Underworld scale on a HPC? In this post we showcase how Underworld 2.11 scales across two of Australia's premiere HPC systems. * Gadi - https://nci.org.au/our-systems/hpc-systems * Magnus - https://pawsey.org.au/systems/magnus/ The reference model chosen for this scaling showcase is a extended 3D stokes flow: Analytic Solution SolDB3D [https://underworld2.readthedocs.io/en/latest/build/underworld.function.analytic.html?highlight=solDB#underworld.function.analytic.SolDB3d] . Q1P0 el"
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

How does Underworld scale on a HPC? In this post we showcase how Underworld 2.11 scales across two of Australia's premiere HPC systems.

- Gadi - [https://nci.org.au/our-systems/hpc-systems](https://nci.org.au/our-systems/hpc-systems)

- Magnus - [https://pawsey.org.au/systems/magnus/](https://pawsey.org.au/systems/magnus/)

The reference model chosen for this scaling showcase is a extended 3D stokes flow: Analytic Solution [SolDB3D](https://underworld2.readthedocs.io/en/latest/build/underworld.function.analytic.html?highlight=solDB#underworld.function.analytic.SolDB3d) . Q1P0 elements were used and a fixed solver iteration count for solving the saddle point problem. We extended this model adding extra routines (*swarm advection* and the *advection-diffusion* equation solver) to capture all the main algorithms used in a typical thermo-mechanical model by Underworld.

The results are split into **Strong** and **Weak** scaling results.

- **Strong scaling** varying the number of CPUs for a given model resolution.

- **Weak scaling** varying both the number of CPUs and model resolution to keep the amount of work per core constant - investigating the parallel efficiency of the algorithms.

---

## Strong scaling

The following graph shows various resolution runs performed over a range of CPU numbers (nproc). The y-axis is measured in service units to capture the cost of using the compute resources.   
For ideal scaling one would expect families of flat lines as doubling the amount of CPUs should result in halving the runtime; yielding a constant Service Unit cost.

```{figure} figures/Strong-Scaling-Gadi-solid--vs-Magnus-dashed--2.jpg

download
```

The following graph shows an function break down of a single sized model, 256^3 number of elements.

```{figure} figures/Strong-Scaling-Gadi-solid--vs-Magnus-dashed--256-3-Resolution-1-1.png

download
```

---

## Weak scaling

Weak scaling plots shows the effect of running the same amount of work (elements count in the legend) per CPU constant but increasing the number of processor CPUs used. This investigates the parallel efficiency of the code.

```{figure} figures/Weak-Scaling-Gadi-solid--vs-Magnus-dashed--1-1.png

download
```

The following is a function break down of the weak scaling results for a 32^3 element per CPU model.

```{figure} figures/Weak-Scaling-Gadi-solid--vs-Magnus-dashed--32-3-PerProc-1.png

download
```

Unfortunately, we were only able to run these scaling models once (sometimes twice) due to low time allocation of the 2 HPC facilities. Ideally, we would repeat each model configuration at least 3 times and take an average model time to generate more statistically sound results.  
  
We hope our Underworld user community find these results useful for understanding what one can expect when executing Underworld on a HPC facilities.

For anyone wanting to reproduce these results all scripts used to run and analyse the results are stored [here](https://github.com/underworldcode/scaling_scripts).

Finally we thank the following supporting project/support schemes:

- Project m18: Moresi, L. Instabilities in the convecting mantle and lithosphere.

- Project q97: Mueller, D. Geodynamics and evolution of sedimentary systems.

- Sydney Informatics Hub HPC Allocation Scheme, which is supported by the Deputy Vice-Chancellor (Research), University of Sydney and the ARC LIEF, 2019: Smith, Muller, Thornber et al., Sustaining and strengthening merit-based access to National Computational Infrastructure (LE190100021).

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=2-11-scaling">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=2-11-scaling">Start one</a></div></div>
