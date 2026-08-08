---
title: Scaling in Underworld
description: To test scalability we run weak scaling tests on various HPC machines to check the numerical framework remains robust when pushing for higher fidelity models.
date: 2021-03-09
authors:
  - name: Julian Giordani
    orcid: 0000-0003-4515-9296
    affiliations:
      - University of Sydney
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
  - name: John Mansour
    orcid: 0000-0001-5865-1664
    affiliations:
      - Monash University
doi: 10.59350/qvgm0-yz754
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Documentation
  - Underworld Code
exports:
  - format: typst
    template: ../../templates/pdf
    output: scaling-in-underworld.pdf
    article_id: UWTN 2021-002
    article_version: 1.0.0
parts:
  abstract: To test scalability we run weak scaling tests on various HPC machines to check the numerical framework remains robust when pushing for higher fidelity models.
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

To date *weak scaling *tests have been run on two of the largest computers in Australia: **Gadi** (NCI) and **Magnus **(Pawsey).  
Here we present the results of those tests and discuss:

**Gadi: Weak scaling - SolDB3D Q1**

```{figure} figures/Weak-Scaling-Timing-SolDB3d-Q1--base-16--MaxIts-100.png

Gadi - v2.11-prerelease: Weak scaling of SolDB3D (linear elements) to ~10k procs
```

**Gadi: Weak scaling - SolDB3D Q2**

```{figure} figures/image-1.png

Gadi - v2.11-prerelease: Weak scaling of SolDB3D (quadractic elements) to 10k procs
```

**Magnus: Weak scaling - SolDB3D Q2 - v2.10 vs v2.9**

```{figure} figures/f4efe6bc-57da-456a-97c3-cc4def294ae9.png

Magnus: Weak scaling of SolDB3D (quadractic elements) to ~14k procs
```

Underworld's **Gadi** installation is setup as a "bare metal" install, i.e. all code and dependencies are natively compiled onto Gadi's filesystem. However **Magnus** utilises Underworld's custom prebuilt docker via singularity containerisation.

Generally we see Underworld can scale to beyond 10k CPUs on both **Gadi** and **Magnus**. Wonderful!   
It is noticeable that the *Python_Import_Time* scales more erratically on all Gadi runs rather than Mangus runs. Indeed it has been observed that some Gadi jobs, 500+ CPUs, fail to even start.   
It is believed this issue is related to Underworld's (many) Python modules being read concurrently from Gadi's filesystem, overloading the filesystem with metadata operations and blocking IO. While on Magnus all Python modules are available to every CPU via the docker container and *Python_Import_Time* scales consistently.  
  
The Underworld development team are continuing to work with the Gadi system admin to overcome this  *Python_Import_Time* issue.

The analytic solution **SolDB3D** used as the reference model is based on the work by Dohrmann, C & Bochev, Pavel. 2004 [1], for the implementation details of of SolDB3D in Underworld see [here](https://underworld2.readthedocs.io/en/latest/build/underworld.function.analytic.html#underworld.function.analytic.SolDB3d)

[1]: Dohrmann, C & Bochev, Pavel. (2004). A stabilized finite element method for the Stokes problem based on polynomial pressure projections. International Journal for Numerical Methods in Fluids. 46. 183-201.
