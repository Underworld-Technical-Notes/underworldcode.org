---
title: Stripy 2.0 released
description: Generating Voronoi diagrams and interpolating / smoothing with spline tensions are among a list of new features in Stripy 2.0
date: 2020-08-26
authors:
  - name: Ben Mather
    orcid: 0000-0003-3566-1557
    affiliations:
      - University of Sydney
doi: 10.59350/bpy2d-6ww41
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Stripy
  - Python/Jupyter
exports:
  - format: typst
    template: ../../templates/pdf
    output: stripy-2-0-released.pdf
    article_id: UWTN 2020-008
    article_version: 1.0.0
parts:
  abstract: Generating Voronoi diagrams and interpolating / smoothing with spline tensions are among a list of new features in Stripy 2.0
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

```{figure} figures/seafloor-age-topo.png
```

We've been busy creating the next major release of [Stripy](https://github.com/underworldcode/stripy). To refresh your memory, Stripy is a Python tool for triangulating scattered points either in Cartesian coordinates or on the sphere. It wraps a bunch of Fortran codes in a neat, object-oriented Python interface that can be used for many geographical applications.

## What's new?

**Spline tension** - a lot of data transformations in Stripy are underpinned by cubic splines (e.g. interpolation, derivatives, smoothing). In v2.0 you can now add spline tension which avoids overshoot / undershoot artefacts. The most visible improvements are in accuracy of derivatives at points along the boundary and extrapolation of data beyond the boundary of a mesh.

```{figure} figures/spline_tension.png

Difference between derivatives evaluated at the poles with spline tension vs. without. Looks like a beautiful flower. (Graphic generated with LavaVu).
```

**Voronoi diagram** - the Voronoi diagram is the dual of a Delaunay triangulation. For every triangle in the mesh, there is a voronoi point which lies at an equal radius from each node. The diagram is constructed by connecting up the voronoi points from each neighbouring triangle.

```{figure} figures/voronoi.png

Voronoi diagram on the sphere. Graphic generated with Matplotlib and Cartopy.
```

Other** notable new features** include:

- a new equispaced elliptical mesh in Cartesian coordinates

- central area node weights for any mesh

- efficient evaluation of second derivatives in Cartesian coordinates

- better documentation, LGPLv3 license, and other small bug fixes

You can install the latest release of Stripy with `pip`

```sh
pip install stripy
```

or Conda:

```sh
conda install -c underworldcode stripy
```

## Make Stripy better!

We welcome contributions to the code. If you want to add something you think is missing in Stripy, submit a pull request and if it looks good we'll merge your changes. Check out our [contribution guidelines](https://github.com/underworldcode/stripy/blob/master/CONTRIBUTING.md) for more details.
