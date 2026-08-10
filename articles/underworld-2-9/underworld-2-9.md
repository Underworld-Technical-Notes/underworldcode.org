---
title: Underworld 2.9
description: "The Underworld 2.9 release is available from Github, as a docker container and via zenodo (doi:10.5281/zenodo.3964957) it is also available through pip install for the first time"
date: 2020-04-03
authors:
  - name: John Mansour
    orcid: 0000-0001-5865-1664
    affiliations:
      - Monash University
  - name: Julian Giordani
    orcid: 0000-0003-4515-9296
    affiliations:
      - University of Sydney
  - name: Romain Beucher
    orcid: 0000-0003-3891-5444
    affiliations:
      - Australian National University
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
doi: 10.59350/p0vnx-b9498
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Underworld Code
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

The Underworld 2.9 release is available from [Github](https://github.com/underworldcode/underworld2/releases/tag/v2.9.5b), as a docker container and via [zenodo](https://zenodo.org/record/3964957#.X0xXG0lS9RU) (doi:10.5281/zenodo.3964957) it is also available through `pip install` for the first time (see below).

### Underworld paper in the Journal of Open Source Software

The paper of record for underworld 2 has been published. It does tie to the Underworld 2.9 release but is sufficiently broad to cite for all 2.x releases.

Mansour, John, Julian Giordani, Louis Moresi, Romain Beucher, Owen Kaluza, Mirko Velic, Rebecca Farrington, Steve Quenette, and Adam Beall. “Underworld2: Python Geodynamics Modelling for Desktop, HPC and Cloud.” Journal of Open Source Software 5, no. 47 (March 6, 2020): 1797. [https://doi.org/10.21105/joss.01797](https://doi.org/10.21105/joss.01797).

### Pip Install

While Underworld2 is a Python API, it relies on a complex stack of C libraries to provide much of its core functionality. Statically typed languages such as C are generally orders of magnitude faster than dynamically typed languages (such as Python) and therefore are usually the best choice for numerically heavy routines. Indeed, most computational Python libraries (such as `numpy` and `scipy` use Python for high level orchestration, but outsource all expensive computations to statically typed layers, and `underworld` is no different. While this design is critical to achieving high performance, it does come with the necessary complexity of generating  library binaries for each platform `underworld` needs to run on. ABI compatible third party libraries (such as `petsc`) also need to be created if not available.

The Underworld team’s solution to this problem is [container virtualisation,](https://en.wikipedia.org/wiki/OS-level%5Fvirtualisation) and in particular [Docker](https://en.wikipedia.org/wiki/Docker%5F%28software%29). Containers allow us to generate an image containing the entire runtime stack required to run `underworld`, along with all other peripheral tools our users usually wish to run (such as `Jupyter`). Containers also provide portability, with the single image being able to be utilised on any platform where a Linux kernel can be made available (which includes OS X and Windows).  Indeed there are many other advantages to using containers, such as reproducibility, the ability to switch versions trivially, and even HPC amenability is becoming realistic via tools such as [Shifter](https://github.com/NERSC/shifter) and [Singularity](https://singularity.lbl.gov/) (with potential benefits over bare metal for Python in particular).

However there are certainly shortcomings to container usage. Foremost, it presents a significant learning curve for new users, particularly those not familiar with virtualisation. While front-ends such as Kitematic go a long way to hide much of this difficulty, users will probably still require some understanding of the underlying paradigms for frictionless operation. Image size can also be of annoyance, with [our complete images weighing in at almost 1GB,](https://hub.docker.com/r/underworldcode/underworld2/tags) and over 2GB when uncompressed. Finally, running inside a virtualised environment isolates `underworld` from the host and its software, such as locally installed Python modules and tools such as IDEs.

It is therefore also nice to have the option of a natively installed `underworld` module. We have always provided minimal compilation instructions to allow users to generate local `underworld` builds, but the expertise required to successfully compile `underworld` and its dependencies generally restricted this to power users. However in recent times the installation of third party libraries has become easier, and [we’ve also made some changes to simplify our requirements](https://github.com/underworldcode/underworld2/commit/e01c14f9ca5ea204e10f6d97433a902a82ea0175). As such, we’re now in a position where we can provide `underworld` installation via the `pip` Python package manager:

```TERMINAL
pip3 install -v git+https://github.com/underworldcode/underworld2
```

Note that we unable to provide pre-compiled binaries at the moment, so `pip` will attempted to compiled `underworld` locally. You therefore will require various tools/libraries for the compilation process, as well as Python3, pip, and any required Python modules. We also recommend the use of `virtualenv` Python environments which allow you to run different Python environments concurrently and only install to user space.

Note that the installation of `underworld` via `pip` is still experimental, and while we encourage users to give it a shot (and welcome feedback), usage via Docker containers is still the recommendation.

#### Requirements

**PETSc:** PETSc can be installed via `pip` these days, or is usually available via platform package managers (such as `apt` on Ubuntu as `petsc-dev`). If you have PETSc installed in a non-standard location, please set the `PETSC_DIR` environment variable to specify the required location.

**MPI & mpi4py:** You will need an implementation of MPI installed on your system. Underworld is commonly used with [MPICH](https://www.mpich.org/) and [OpenMPI](https://www.open-mpi.org/). You will also need to install the `mpi4py` package (via `pip`) which provides Python bindings to the MPI library. If non-standard, you can specify the wrapped compilers by setting the `MPICC` and `MPICXX` environment variables.

**h5py:** The standard `h5py` (installed via `pip`) is the recommended version for desktop usage. However, note that it will be the non-parallel enabled version, and for large parallel simulations saving/reading data may become a bottleneck, and collective IO via MPI-enabled `h5py` is recommended. The following command may be useful for installed MPI-enabled `h5py` where necessary:

```SH
CC=mpicc HDF5_MPI="ON" HDF5_DIR=/path/to/your/hdf5/install/ pip install --no-binary=h5py h5py
```

Note that, for the above, you will also need to have a parallel enabled version of the  `HDF5` library available for `h5py` to link against.

**Lavavu:** For rendering of visualisations, you will also need to install `lavavu` (via `pip`). Please check the [lavavu page](https://github.com/lavavu/LavaVu) for further installation instructions.

**Other**: The following should also be installed via a system package manager (such as apt on Ubuntu):`swig`, `git` and  `libxml2-dev` (or equivalent). The following should be installed via pip:`scons` and `numpy`.

Please refer to the `Installation.rst` file located at the top level of the project repository for the latest installation information and guidelines.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=underworld-2-9">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=underworld-2-9">Start one</a></div></div>
