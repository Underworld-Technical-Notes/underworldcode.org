---
title: "How to build Conda packages?"
date: 2020-11-23
authors:
  - name: Romain Beucher
    orcid: 0000-0003-3891-5444
    affiliations:
      - Australian National University
doi: 10.59350/7x9h6-y1x53
license: CC-BY-4.0
banner: figures/banner.jpg
keywords:
  - Tricks of the Trade
  - Documentation
  - "#editors-pick"
exports:
  - format: typst
    series: "Underworld Technical Notes"
    logo: ../../static/uwtn-logo.png
    origin_url: https://www.underworldcode.org/build-conda-packages/
    template: ../../templates/pdf
    output: build-conda-packages.pdf
    article_id: UWTN 2020-012
    article_version: 1.0.0
parts:
  abstract: "As mentioned, packages can be installed directly from our conda channel. You may however want to build your own package at some point in the future or you may want to fix some of ours by submitting a Pull Request on github (You are more welcome to do so...) The following goes through the steps of building a conda package for Badlands which contains Python and Fortran code. This is relatively advanced but not really difficult. Installing and Updating conda-build To install conda-build, in you"
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""></div>

```{figure} figures/landing-page.jpg
```

As mentioned, packages can be installed directly from our conda channel. You may however want to build your own package at some point in the future or you may want to fix some of ours by submitting a Pull Request on github (You are more welcome to do so...)

The following goes through the steps of building a conda package for Badlands which contains Python and Fortran code. This is relatively advanced but not really difficult.

### Installing and Updating `conda-build`

To install conda-build, in your terminal window or an Anaconda Prompt, run:

```bash
conda install conda-build
```

## A Conda recipe for Badlands

conda build requires a conda recipe which is usually a combination of files such as:

- A meta.yaml file

- A build script called `build.sh` for Linux and MacOS and `build.bat` for Windows.

- Sometimes a `yum_requirements.txt` file for some additional libraries that are not available on conda-forge.

- A LICENSE file.

The Badlands conda recipe is relatively simple and contains only a `meta.yaml` file and the License file.

### The meta.yaml file

conda recipes use a `meta.yaml` file. The YAML (a [recursive acronym](https://en.wikipedia.org/wiki/Recursive_acronym) for "YAML Ain't Markup Language") format is a text format that is meant to be easily readable. A cheat sheet and full specification are available at the [official site](https://en.wikipedia.org/wiki/YAML#cite_note-13). The format is organised around to main structures:

- Dictionaries:

```yaml
package: 
  name: name
  version: version
```

- Lists:

```yaml
host:
  - python
  - pytriangle
  - numpy >=1.15.0
  - pip
```

The YAML structures can be completed with some Jinja2 code which allows to declare variables and access them:

```yaml
{% set name = "badlands" %}
{% set version = "2.0.25" %}

package:
  name: {{ name|lower }}
  version: {{ version }}
```

Jinja2 is a very powerful templating language for Python. It is definitely worth checking out if you want to automated / simplify your config files.

### Basic structure of the recipe

The `meta.yaml` recipe is organised into a list of structures that must be provided to `conda build`. They are:

- The **package** dictionary which must contain the **name** and the **version** number of the package.

- The **source** dictionary which contains the **url** (which can be a local path or an http address). Note that providing a  checksum such as sha256 is considered good practice. It can easily be generated on a MacOs or Linux system using the following command: `openssl sha256 my_tarball.tar.gz`

- The **build** dictionary that contains the build **number** that you as a maintener are responsible to increment and the **build** instructions on how to build the package. In the case of *Badlands*, the instructions are fairly simple and rely on a `pip install` method. You could provide a `build.sh` file with more complex instructions. I recommend you check the *Lavavu* recipe for an example of a more complex set of build instructions. Note that in its current form the *Badlands* conda recipe skips Windows system as we chose to rely on the Windows Subsystem for Linux (WSL) available on Windows 10.

- The requirement dictionary that contains 3 lists of dependencies for the **build**, **host** and **run** systems.   
The **build** section should only contains the tools that are required to build the package. This generally include the compilers and some configuration tools such as *make* or *cmake* etc.  
The **host** section contains a list of packages that need to be specific to the target platform, when the target platform is not necessarily the same as the build platform. Shared libraries should be listed here. The Python interpreter must also be listed here.  
The **run** section contains the dependencies that are needed when running a program. Typically all the packages that are imported by the package we are building will need to be listed here.

Note: Version constrains can be easily set within the lists of dependencies. Conda will use those constrain to resolve the dependencies when creating a new environment.

- The **test** section which contains the test that conda build should run once the package has been built. This section is optional but highly recommended. For a Python package, it includes a list of imports. It can also run unit tests etc.

- The **about** section contains a list of metadata that describe the package. It usually includes a link to the **home**page** **of the project, the **license**, a link to the full **license_file**, a **summary** and a link to the documentation, **doc_url**.

- The **extra** section contains some extra metadata that might be useful such as a list of the maintainers names.

### The complete recipe

*Badlands* requires a Fortran and a C compiler. Anaconda provides a list of default compilers that can be accessed using the {{compiler()}}  
expression. It is the recommended way to do things but you could also specify a specific compilers. You could also provide a list of variants compilers but this is beyond the scope of this blog post.

```yaml
{% set name = "badlands" %}
{% set version = "2.0.25" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: "https://pypi.io/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz"
  sha256: 339175849a62412e6e445be40b1c392ad1194b7c97746492010e7d3e26045814

build:
  skip: true # [win]
  number: 0
  script: {{ PYTHON }} -m pip install badlands/ -vv

requirements:
  build:
    - {{ compiler('fortran') }}
    - {{ compiler('c') }}
  host:
    - python
    - pytriangle
    - numpy
    - pip
  run:
    - gflex
    - h5py
    - matplotlib
    - meshplex
    - numpy
    - pandas
    - python
    - scikit-image
    - scipy
    - six
    - pytriangle

test:
  imports:
    - badlands
    - badlands.flow
    - badlands.forcing
    - badlands.hillslope
    - badlands.simulation
    - badlands.surface
    - badlands.underland

about:
  home: "https://github.com/badlands-model"
  license: GPL-3.0+
  license_family: GPL
  license_file: LICENSE 
  summary: "Basin and Landscape Dynamics (Badlands) is a TIN-based landscape evolution model"
  doc_url: https://badlands.readthedocs.io/

extra:
  recipe-maintainers:
    - rbeucher
    - tristan-salles
```

## The conda build process

Once ready you can test that the package builds using:

`conda build -c conda-forge -c geo-down-under recipe/`

where `recipe` is the folder that contains the full set of files of the conda recipe.

Here I copy the steps performed by conda-build as described in the official [documentation](https://docs.conda.io/projects/conda-build/en/latest/concepts/recipe.html#conda-build-process):

Conda-build performs the following steps:

1. Reads the metadata.

2. Downloads the source into a cache.

3. Extracts the source into the source directory.

4. Applies any patches.

5. Re-evaluates the metadata, if source is necessary to fill any metadata values.

6. Creates a build environment and then installs the build dependencies there.

7. Runs the build script. The current working directory is the source directory with environment variables set. The build script installs into the build environment.

8. Performs some necessary post-processing steps, such as shebang and rpath.

9. Creates a conda package containing all the files in the build environment that are new from step 5, along with the necessary conda package metadata.

10. Tests the new conda package if the recipe includes tests:

1. Deletes the build environment and source directory to ensure that the new conda package does not inadvertantly depend on artifacts not included in the package.

2. Creates a test environment with the package and its dependencies.

3. Runs the test scripts.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=build-conda-packages">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=build-conda-packages">Start one</a></div></div>
