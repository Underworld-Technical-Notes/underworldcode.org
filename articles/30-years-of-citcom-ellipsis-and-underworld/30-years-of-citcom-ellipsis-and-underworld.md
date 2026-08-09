---
title: "30 Years of Citcom, Ellipsis and Underworld"
description: CITCOM is a geodynamics modelling code based on the finite element method that is designed for planetary evolution modelling where large spatial variations and strong non-linearities occur in the material properties.
date: 2024-01-16
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
doi: 10.59350/hsp06-ag431
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Underworld Code
  - Geophysics
  - Auscope
exports:
  - format: typst
    origin_url: https://www.underworldcode.org/30-years-of-citcom-ellipsis-and-underworld/
    template: ../../templates/pdf
    output: 30-years-of-citcom-ellipsis-and-underworld.pdf
    article_id: UWTN 2024-001
    article_version: 1.0.0
parts:
  abstract: CITCOM is a geodynamics modelling code based on the finite element method that is designed for planetary evolution modelling where large spatial variations and strong non-linearities occur in the material properties.
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""><div class="uwtn-credit">Photo by <a href="https://unsplash.com/@henleydesign?utm_source=underworld-technical-notes&utm_medium=referral&utm_campaign=api-credit">Henley Design Studio</a> / <a href="https://unsplash.com/?utm_source=underworld-technical-notes&utm_medium=referral&utm_campaign=api-credit">Unsplash</a></div></div>

CITCOM is a geodynamics modelling code based on the finite element method that is designed for planetary evolution modelling where large spatial variations and strong non-linearities occur in the material properties. CITCOM was originally conceived by Louis Moresi working at Caltech with Professor David Stevenson but quickly developed into an open-source community software effort with the work of Shijie Zhong, Slava Solomatov, Mike Gurnis and many others. CITCOM spun off many novel software tools including CITCOM-S, CITCOM-SVE, Ellipsis and Underworld. In this article, Louis Moresi reflects on a 30 year community-software development journey.

We mark January 17, 1994 (the day better known for the [Northridge Earthquake](https://en.wikipedia.org/wiki/1994_Northridge_earthquake)) as the birthday of the CITCOM family of codes. I was shaken awake early in the morning, and spent the rest of the day nervously waiting for the next aftershock while I checked that the code was really solving all the test problems quickly and accurately. CITCOM took more than a year to get right and many deadlines went by un-met as a result including the pre-Christmas deadline of the 1993 AGU Fall Meeting.

There were two notable papers that eventually came out of this early version of CITCOM: 1) Moresi and Solomatov (1995) where we were able to model fully-stagnant lid convection for the first time and demonstrate how all the theoretical scalings really worked; and 2) Moresi, Zhong & Gurnis (1996) where we proved that the method itself was accurate using analytical solutions. In the following two years we expanded on these topics in numerous other papers, Shijie Zhong developed a parallel version of the code, and we declared the code to be formally open source and encouraged the community to use it.

When Shijie Zhong and his team developed CITCOM-S (Zhong et al, 2000), the parallel, spherical code that inherited all the robust solvers from the Cartesian version, the community embraced the code and it became one of the most widely used software tools in the geodynamics community and continues to be used today.

The other branch of this family tree took a different path: the Ellipsis code was developed to study history-dependent fluid-dynamics problems (e.g. materials with damage, anisotropic flow, viscoelastic convection) using Lagrangian particles embedded in the finite element mesh (Moresi et al, 2003). Ellipsis became Underworld when we adopted the [PETSc](www.petsc.org) parallel computing framework and received funding from [AuScope](www.auscope.org.au) to develop a community of users and support their research needs.

As the CITCOM codes celebrate 30 years, and active development of Underworld passes the 20 year mark, we will be unveiling our next generation of software, **Underworld3**.

```{figure} figures/Screenshot-2024-01-16-at-9.27.44-pm.png

Underworld3 is integrated with Jupyter and with sympy. The development environment is easy to use, close to the original mathematical formulation and highly interactive. Once ready for deployment, parallel execution is efficient and scalable - no modification of the notebooks is needed.
```

**Underworld3** continues the long collaboration with the ***PETSc*** team. We have completely re-engineered the internal structure of the code to leverage the ***PETSc*** computational infrastructure while focusing on ease of use for geophysical fluid dynamics problems. We introduce a pure symbolic interface to the conservations equations that builds the python ***sympy*** system — this provides automatic differentiation of PDEs (required for non-linear problems and optimisation for example) but also simplification, code-compilation, and mathematical verification. This system puts Lagrangian and Eulerian formulations on a completely equal footing and makes the two representations inter-operable. Parallel scaling is robust and reliable thanks to ***PETSc*** and, at the same time, the code is very straightforward to follow because the built-in documentation is perfectly integrated with ***Jupyter***.

Stay tuned for a series of posts introducing **Underworld3** and, this time (fingers crossed) no natural disasters to accompany the release.

### References

Moresi, L., Dufour, F., & Mühlhaus, H.-B. (2003). A Lagrangian integration point finite element method for large deformation modeling of viscoelastic geomaterials. *Journal of Computational Physics*, *184*(2), 476–497. [https://doi.org/10.1016/S0021-9991(02)00031-1](https://doi.org/10.1016/S0021-9991(02)00031-1)

Moresi, L., Quenette, S., Lemiale, V., Mériaux, C., Appelbe, B., & Mühlhaus, H.-B. (2007). Computational approaches to studying non-linear dynamics of the crust and mantle. *Physics of the Earth and Planetary Interiors*, *163*(1), 69–82. [https://doi.org/10.1016/j.pepi.2007.06.009](https://doi.org/10.1016/j.pepi.2007.06.009)

Moresi, L.-N., & Solomatov, V. S. (1995). Numerical investigation of 2D convection with extremely large viscosity variations. *Physics of Fluids*, *7*(9), 2154–2162. [https://doi.org/10.1063/1.868465](https://doi.org/10.1063/1.868465)

Moresi, L., Zhong, S., & Gurnis, M. (1996). The accuracy of finite element solutions of Stokes’ flow with strongly varying viscosity. *Physics of the Earth and Planetary Interiors*, *97*(1–4), 83–94. [https://doi.org/10.1016/0031-9201(96)03163-9](https://doi.org/10.1016/0031-9201(96)03163-9)

Zhong, S., Zuber, M. T., Moresi, L., & Gurnis, M. (2000). Role of temperature-dependent viscosity and surface plates in spherical shell models of mantle convection. *Journal of Geophysical Research B: Solid Earth*, *105*(B5), 11063–11082. [https://doi.org/10.1029/2000JB900003](https://doi.org/10.1029/2000JB900003)

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=30-years-of-citcom-ellipsis-and-underworld">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=30-years-of-citcom-ellipsis-and-underworld">Start one</a></div></div>
