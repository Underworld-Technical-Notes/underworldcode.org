---
title: Alaska Moho Model (Reproducible research with containers)
date: 2018-10-12
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
doi: 10.6084/m9.figshare.33193410
license: CC-BY-4.0
banner: figures/banner.png
keywords:
  - Stripy
  - Geodynamics
exports:
  - format: typst
    archived: "2026-08-09T14:21:43Z"
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/alaska-moho-model-reproducible-research-with-containers/
    template: ../../templates/pdf
    output: alaska-moho-model-reproducible-research-with-containers.pdf
    article_id: UWTN 2018-003
    article_version: 1.0.0
---
<div class="uwtn-banner"><img src="figures/banner.png" alt=""></div>

```{figure} figures/MohoSurfaceGradient-ClusteredGrids.png
```

Making your research reproducible means that you provide the entire workflow from data, through software and post-processing freely available. Not only can somebody repeat your experiments and verify them, they can build upon them. In lab-based disciplines, there are many further challenges, but in research that is predominantly based on data processing, this ought to be an achievable goal.

We are releasing all of the background for our recent paper on the Alaska Moho (Miller & Moresi, 2018) to make it transparent and reproducible. Open source software is one thing but it is also important to make the software easily accessible: the software and raw moho picks are available through

```bash
pip install miller_alaskamoho_srl2018
```

but to manage versions and operating system changes, we have also packaged everything in a docker container that is published on docker hub.

But, since the software we release is also used to interpolate the surfaces, and not everyone wants to install docker, we also make all our notebooks available in the cloud with everything pre-configured. You can launch it [on mybinder.org](https://mybinder.org/v2/gh/lmoresi/miller-moho-binder/publication) to try it out.

```{image} figures/badge.svg
:alt: Binder
:target: https://mybinder.org/v2/gh/lmoresi/miller-moho-binder/publication
:width: 92px
```

See [pypi.org/project/miller_alaskamoho_srl2018](https://pypi.org/project/miller_alaskamoho_srl2018/) for a full list of installation / running options.

The software is also tracked on Zenodo

```{image} figures/zenodo.1459110.svg
:alt: DOI
:target: https://doi.org/10.5281/zenodo.1459110
:width: 183px
```

#### References

1.  Miller, M. S., and L. Moresi (2018), Mapping the Alaskan Moho, Seismological Research Letters, 1–7, doi:10.1785/0220180222.

2. Louis Moresi. (2018, October 12). lmoresi/miller-moho-binder: Miller and Moresi, Seismological Research Letters (Version v1.0). Zenodo. http://doi.org/10.5281/zenodo.1459110

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=alaska-moho-model-reproducible-research-with-containers">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=alaska-moho-model-reproducible-research-with-containers">Start one</a></div></div>
