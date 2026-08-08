---
title: Here comes Conda...
description: Sharing a workflow environment is also paramount if we want to make sure that reproducibility can be effectively tested. An environment management system such as conda allows us to do so.
date: 2020-11-16
authors:
  - name: Romain Beucher
    orcid: 0000-0003-3891-5444
    affiliations:
      - Australian National University
doi: 10.59350/4c21r-t7c68
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Underworld Code
  - Documentation
  - AuScope UW Cloud
exports:
  - format: typst
    template: ../../templates/pdf
    output: here-comes-conda.pdf
    article_id: UWTN 2020-010
    article_version: 1.0.0
parts:
  abstract: Sharing a workflow environment is also paramount if we want to make sure that reproducibility can be effectively tested. An environment management system such as conda allows us to do so.
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

*Conda packages are now available for most of the underworldcode suite of software* *([Underworld](https://github.com/underworldcode/underworld2.git), [UWGeodynamics](https://github.com/underworldcode/UWGeodynamics.git), [Lavavu](https://github.com/lavavu/LavaVu.git), [Stripy](https://github.com/underworldcode/stripy.git)) from the [geo-down-under](https://anaconda.org/geo-down-under) conda channel.*

```{figure} figures/conda_logo.svg
```

Let’s face it. Users don’t want to spend time compiling code on their machine. It is time consuming, requires some specific skills and creates unnecessary hurdles in a workflow. More often than not, users give up and potentially miss out on some very interesting tools.   
  
The Underworld team has been using [Docker](https://www.docker.com/) Containers for a while. Containers are convenient: users can pull a new Docker image after each release of the software, start a new container and use the code on any machine that can run Docker. We love docker containers, they are great for deploying services with dedicated functions on large systems such as Amazon cloud, Azure or Google cloud etc. Containers provide a complete environment with all the dependencies needed to run your software. They also provide some degree of isolation: you can discard a container and restart from a fresh and clean system whenever you like.

***But they are not for everyone. ***

Docker images/containers are often quite big and pulling a new image often means transferring gigabytes of data. This can quickly become a waste of resources. A normal user should be able to install and run code in a few minutes. The very nature of scientific work is to explore and test things. We may do so by testing different libraries or even different version of a code. This requires multiple environment that need to be managed efficiently. Sharing a workflow environment is also paramount if we want to make sure that reproducibility can be effectively tested. An environment management system such as [conda](https://docs.conda.io/en/latest/) allows us to do so.

## Conda Packages

conda is a package, dependency and virtual environment manager that is included in the [Anaconda Python distribution](https://www.anaconda.com/). Anaconda is a high performance open source data science platforms powered by Python and R. It is very popular in the Science / Data Science communities as it includes the most popular Python, R and Scala packages for data processing and analysis. Anaconda is a fairly large download, for people who are conservative about disk space, there is also [Miniconda](https://docs.conda.io/en/latest/miniconda.html), a smaller distribution that includes only conda and Python.

You may already be aware of pip, easy_install, and virtualenv. They are all very good environment management systems. The main problem is that they are focused around Python while scientific codes and libraries are often a mix of Python, Fortran, C or C++, built against some platform dependent libraries. There are workarounds to create binary packages with some of these tools but the resulting product is strongly platform dependent and is thus not easy shareable. Conda was created specifically to handle this case scenario and can build packages in any language.

Before using pip, a Python interpreter must be installed. Conda, on the other hand, can install Python packages as well as the Python interpreter. The key advantage of conda over pip is the way it handles dependency. All the user needs to do is provide a list of packages needed for their workflow. Conda will resolve the compatibility of the required dependencies and will return a working environment. Occasionally a package is needed which is not available as a conda package but is available on PyPI and can be installed with pip. In these cases, it makes sense to try to use both conda and pip.

## A short introduction to conda

### Installing Miniconda

### Linux

[Miniconda installer for Linux](https://docs.conda.io/en/latest/miniconda.html#linux-installers)

In a terminal window, run:

```bash
bash Miniconda3-latest-Linux-x86_64.sh
```

### macOS

[Miniconda installer for macOS](https://docs.conda.io/en/latest/miniconda.html#macosx-installers)

In a terminal window, run:

```bash
bash Miniconda3-latest-MacOSX-x86_64.sh
```

### Create a new environment

In a terminal window, run:

```bash
conda create --name env_name
```

Then activate it:

```bash
conda activate env_name
```

### Installing packages

All our packages are built against dependencies available from the conda-forge and/or the geo-down-under conda channel.  
They need to be added to your list of channels:

```bash
conda config --add channels conda-forge
conda config --append channels geo-down-under
```

The first command adds the channel `conda-forge` to the top of the channel list, making it the highest priority.  
The second command appends the channel `geo-down-under` to the channel list making it the lowest priority.

In a terminal window:

```bash
conda install underworld2 uwgeodynamics badlands lavavu stripy
```

which is equivalent to:

```bash
conda install -c conda-forge -c geo-down-under underworld2 uwgeodynamics lavavu stripy
```

## Good practice tips

When you add, remove or update a package you should save the environment to a text file:

```bash
conda list --explicit > conda-env.txt
```

It is good practice to keep that environment file in a version control system such as `git`. You can then share the file with your colleagues who will then be able to recreate the environment as follows:

```bash
conda env create --file conda-env.txt 
```

##
