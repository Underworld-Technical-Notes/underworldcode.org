---
title: Australian Seismometers in Schools - Noise monitoring dashboard
description: How we built a simple dashboard using Github actions with open source software and openly available (FAIR) data.
date: 2020-07-17
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
doi: 10.6084/m9.figshare.33193428
license: CC-BY-4.0
banner: figures/banner.png
keywords:
  - AuScope UW Cloud
  - Tricks of the Trade
  - Geophysics
  - Python/Jupyter
exports:
  - format: typst
    archived: "2026-08-09T14:33:08Z"
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/self-updating-repositories/
    template: ../../templates/pdf
    output: self-updating-repositories.pdf
    article_id: UWTN 2020-006
    article_version: 1.0.0
parts:
  abstract: How we built a simple dashboard using Github actions with open source software and openly available (FAIR) data.
---
<div class="uwtn-banner"><img src="figures/banner.png" alt=""></div>

[Meghan S. Miller](https://theconversation.com/profiles/meghan-s-miller-1105475), *[Australian National University](https://theconversation.com/institutions/australian-national-university-877)* and [Louis Moresi](https://theconversation.com/profiles/louis-moresi-1133314), *[Australian National University](https://theconversation.com/institutions/australian-national-university-877)*

***How we built a simple dashboard using Github actions with [open source software](https://github.com/ThomasLecocq/SeismoRMS) and [openly available (FAIR) data](https://auspass.edu.au/). ***

We recently wrote an [article in The Conversation](https://theconversation.com/australian-cities-are-quiet-during-lockdown-earthquake-scientists-are-making-the-most-of-it-142717) that shows how the Australian Seismometers in schools network registers the pulse of Australian life through changes in the seismic noise  spectrum measured in local schools.

The figures in the article show the signal from Christmas 2019 through to July 2020 and, like any publication of record, they are static. But the data continue to flow into the school seismometers, so every night we update those graphs automatically and you can see the version from last night here:

![AuDAR](figures/latest.png)  
[Canberra, ACT](https://github.com/ANU-RSES-Education/SeismicNoise_AuSIS_DAR)

![AuUHS](figures/latest.png)  
[Rockhampton, QLD](https://github.com/ANU-RSES-Education/SeismicNoise_AuSIS_NRC)

![AuUHS](figures/latest.png)  
[Ulladulla, NSW](https://github.com/ANU-RSES-Education/SeismicNoise_AuSIS_UHS)

![AuKSC](figures/latest.png)  
[Keysborough, VIC](https://github.com/ANU-RSES-Education/SeismicNoise_AuSIS_KSC)

![AuMAR](figures/latest.png)  
[Adelaide, SA](https://github.com/ANU-RSES-Education/SeismicNoise_AuSIS_MAR)

*These images are raw versions of the plots used to make [this figure](https://images.theconversation.com/files/347848/original/file-20200716-17-1xkxswe.png?ixlib=rb-1.1.0&q=45&auto=format&w=1000&fit=clip) from The Conversation article and the links point to the Github repositories that generate the images each day.Because we link to the image and not a copy of the image, it will always be the latest version.*

### How it works

We built a [template repository on GitHub](https://github.com/ANU-RSES-Education/SeismicNoise_AuSIS) where we keep a copy of the python notebooks and scripts that generate the plots we need. The next thing we did was to add some [Github actions](https://github.com/features/actions) to the repository which are small scripts that run if the code changes or, otherwise, every evening. These fetch new data, build the latest figures and send a warning email if anything goes wrong. Then the same scripts upload the day's processed signals (to save time the next day) and update the images in the original repository.

For any station that we want to monitor, we make a copy of the template repository and change a few settings that describe how to find the data on the [Auspass](https://auspass.edu.au/) servers. Then we just need to wait for the scripts to grab all the data and build the images. It takes a while the first time but just takes a few seconds next time around.

There is a "health check" image that shows gaps in the data that is handy when  warning messages roll in. This is the health check for the Ulladulla station which has a few gaps here and there but is healthy enough to produce a clear noise plot.

![HealthCheck_UHS](figures/latest-gridmap.png)

### What else ?

It is quite common to see code repositories with badges that show if the current code is working well. Sometimes, though, it is also useful to tabulate or graph the results of benchmarks over time or speed tests that are not automated. Actions running periodically can do this very easily and also keep the results synchronized and versioned alongside the code itself.

### Can I use this ?

Of course — all of these codes are open source including everything we built in the template to make the dashboards.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=self-updating-repositories">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=self-updating-repositories">Start one</a></div></div>
