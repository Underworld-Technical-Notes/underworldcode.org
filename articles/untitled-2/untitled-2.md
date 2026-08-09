---
title: Using physical units in Underworld
date: 2017-05-24
authors:
  - name: Romain Beucher
    orcid: 0000-0003-3891-5444
    affiliations:
      - Australian National University
doi: 10.6084/m9.figshare.33193380
license: CC-BY-4.0
banner: figures/banner.png
keywords:
  - Underworld Code
  - "#editors-pick"
exports:
  - format: typst
    archived: "2026-08-09T14:04:08Z"
    series: "Underworld Technical Notes"
    logo: ../../static/uwtn-logo.png
    origin_url: https://www.underworldcode.org/untitled-2/
    template: ../../templates/pdf
    output: untitled-2.pdf
    article_id: UWTN 2017-002
    article_version: 1.0.0
parts:
  abstract: "Using physical units and how to appropriately scale a model is a top question users ask when beginning with Underworld. The equations Underworld solves are stated in a physically correct form, they remain valid as long as every material constant, geometry, time, etc., are expressed in the same system. There is no explicit concept of units no scaling in Underworld, the choice is entirely left to the user. One can thus decide to use the Meter Kilometer Second system or a dimensionless system, def"
---
<div class="uwtn-banner"><img src="figures/banner.png" alt=""></div>

Using physical units and how to appropriately scale a model is a top question users ask when beginning with Underworld. The equations Underworld solves are stated in a physically correct form, they remain valid as long as every material constant, geometry, time, etc., are expressed in the same system.  There is no explicit concept of units no scaling in Underworld, the choice is entirely left to the user. One can thus decide to use the Meter Kilometer Second system or a dimensionless system, defining the model such that length, density and viscosity of the material are one, etc. Both approaches are correct and allow for more flexibility, but with great power comes great responsibility. The user must ensure the units are consistent.

#### [null](https://imgs.xkcd.com/comics/dimensional_analysis.png)

null

The scaling of the problem, although related to the choice of system units, is a much broader subject. Computers generally have trouble accurately solving for a wide range of numbers. In numerical methods, this issue can result in a matrix with a large Condition number and is difficult to invert(solve) accurately. By using an appropriate scaling, the wide range of numbers can be reduced, thus minimising numerical errors.

From a mathematical point of view, non-dimensionalisation conserves the relationships between parameters. From a numerical point of view, it is often unclear whether the choice of reference value will ensure numerical stability. A rule of thumb is to keep values as close to one as possible. This can become challenging for Earth modeling problems when dealing with non-linear viscosities and values spanning several orders of magnitude.

Another problem arises from the fact that different communities in Earth Science have different backgrounds and usages. A simple example is the number of units we constantly switch between when dealing with space and time: as for when we describe the diffusion of temperature at the grain scale or the cooling of the entire planet.

Here I detail a workflow used to overcome these issues. It is by no mean the only way, but I have found it easy to use and it reduces the risk of error considerably. It is a simple way to solve the problem of unit consistency and scaling.

I have written a small python module which leverages [Pint](https://pint.readthedocs.io/), a python package used to define and manipulate physical units. Pint uses a system of unit registries to define a large set of units and most of their prefixes. A Pint Quantity object is a physical value which has a specific unit attached to itself. Quantity objects can be use in mathematical expressions which also return Quantities in appropriate units.

The example is available here:

[Units/Scaling Example](https://github.com/underworldcode/underworld2/blob/development/docs/examples/1_14_ScalingExample.ipynb)

And if you want to explore the convection simulation:

[M. Kronbichler, T. Heister, and W. Bangerth. High accuracy mantle convection simulationthrough modern numerical methods.Geophysics Journal International, 191:12–29, 2012.]

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=untitled-2">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=untitled-2">Start one</a></div></div>
