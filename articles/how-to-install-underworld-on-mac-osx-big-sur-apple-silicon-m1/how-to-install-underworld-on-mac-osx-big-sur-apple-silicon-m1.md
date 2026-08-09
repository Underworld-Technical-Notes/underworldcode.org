---
title: How to install Underworld on Mac OSX (Apple Silicon M1)
description: The new generation of Apple Mac comes with the new Apple Silicon (M1) chip which has an Arm architecture (as opposed to the older generation that had i386 Intel processor). This brings all manner of troubles and requirements for the development of codes.
date: 2021-09-07
authors:
  - name: Romain Beucher
    orcid: 0000-0003-3891-5444
    affiliations:
      - Australian National University
doi: 10.59350/8nsyv-btx30
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Documentation
  - Tricks of the Trade
  - Underworld Code
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    origin_url: https://www.underworldcode.org/how-to-install-underworld-on-mac-osx-big-sur-apple-silicon-m1/
    template: ../../templates/pdf
    output: how-to-install-underworld-on-mac-osx-big-sur-apple-silicon-m1.pdf
    article_id: UWTN 2021-003
    article_version: 1.0.0
parts:
  abstract: The new generation of Apple Mac comes with the new Apple Silicon (M1) chip which has an Arm architecture (as opposed to the older generation that had i386 Intel processor). This brings all manner of troubles and requirements for the development of codes.
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

The new generation of Apple Mac comes with the new Apple Silicon (M1) chip which has an Arm architecture (as opposed to the older generation that had i386 Intel processor). This brings all manner of troubles and requirements for the development of codes. Here I detail how to install Underworld on Mac OSX Big Sur 11.5.2 (Apple Silicon) using Python 3.9

Important Note: The following guide uses the CMake branch of Underworld.

### Install Python

I installed Python 3 (3.9.7) using Homebrew:

```brew
brew install python3
```

### Install PETSc

I also installed PETSc (3.15.4) using Homebrew. The default comes with **hdf5**, **open-mpi.**

```
brew install petsc
```

### Create a python virtual environment

```python3
python3 -m venv uw2_virtualenv
```

### Activate the environment

```
source uw2_virtualenv/bin/activate
```

### Install H5py

**H5py** is notoriously difficult to get right... Here is how I do it.

```
# Install dependencies
pip3 install numpy cython pkgconfig mpi4py
HDF5_DIR=/opt/homebrew/Cellar/hdf/1.12.1 pip3 install h5py --no-build-isolation --no-binary :all:
```

At the time I am writing this post, the version of HDF5 that comes with PETSc is 1.12.1. This will change in the future so you will have to update that line.   
The **no-build-isolation** option forces pip to skip creating a build environment and to rely on the dependencies being already available (Numpy, pkgconfig, cython, mpi4py).

### Install Underworld 2

First you will probably need to have  **CMake** and **Swig** if you don't have them already.

```brew
brew install cmake swig
```

Now get **Underworld** from **GitHub** and switch to the *cmake* branch

```git
git clone https://github.com/underworldcode/underworld2.git
cd underworld2
git checkout cmake
cd ..
```

Finally install **Underworld**

```
pip3 install underworld2/
```

Note the `/` is important.

### Test your installation

```
python3 -c "import underworld as uw"
```

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=how-to-install-underworld-on-mac-osx-big-sur-apple-silicon-m1">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=how-to-install-underworld-on-mac-osx-big-sur-apple-silicon-m1">Start one</a></div></div>
