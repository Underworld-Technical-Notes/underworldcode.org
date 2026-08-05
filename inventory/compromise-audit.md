# Stage 0 compromise audit

Corpus: **87 records** (54 posts, 33 pages) from the Ghost Content API.

87 record(s) carry at least one finding.

## Findings by check

| check | records |
|---|---:|
| codeinjection_foot | 73 |
| outbound domain not in expected set | 40 |
| written during compromise window | 14 |
| script-like tag | 12 |
| inline event handler | 2 |

## Record write dates

A tight cluster of `updated_at` values indicates a bulk write.

| updated_at | records |
|---|---:|
| 2026-07-31 | 4 |
| 2026-07-30 | 10 |
| 2026-07-07 | 73 |

## Per-record detail

### `2-11-scaling` (post)

Underworld 2.11 Scaling — published 2021-09-30, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: cloudstor.aarnet.edu.au

### `30-years-of-citcom-ellipsis-and-underworld` (post)

30 Years of Citcom, Ellipsis and Underworld — published 2024-01-16, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `account` (page)

Manage your account — published 2001-01-01, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `adding-zotero-references-to-a-webpage` (post)

An automated (zotero) bibliography in a webpage — published 2019-10-23, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.zotero.org

### `ai-and-scientific-software-what-we-learned-rebuilding-underworld3` (post)

AI and Scientific Software: What We Learned Rebuilding Underworld3 — published 2026-03-23, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `alaska-moho-model-reproducible-research-with-containers` (post)

Alaska Moho Model (Reproducible research with containers) — published 2018-10-12, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `auscope-cloud` (page)

About the AuScope Cloud — published 2019-08-29, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.mybinder.org

### `australian-cities-are-quiet-during-lockdown-earthquake-scientists-are-making-the-most-of-it` (post)

Australian cities are quiet during lockdown. Earthquake scientists are making the most of it — published 2020-07-17, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: ausis.edu.au, images.theconversation.com, theconversation.com

### `authors` (page)

Authors — published 2019-08-22, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `build-conda-packages` (post)

How to build Conda packages? — published 2020-11-23, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: docs.conda.io

### `compressible-convection-in-cartesian-coordinates-in-underworld3` (post)

Compressible convection in cartesian coordinates with Underworld3 — published 2023-10-04, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `congested-subduction-workshop` (page)

Congested Subduction Workshop — published 2020-02-07, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: anu.zoom.us, trendsideas.com, www.dropbox.com, www.eventbrite.com.au

### `constitutive-models-in-symbolic-form` (post)

Constitutive Models in Symbolic Form — published 2026-04-13, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `content` (page)

Index by date — published 2020-08-25, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `covid-quiet-time` (post)

COVID-19 lockdown leads to seismic noise “quiet period” — published 2020-07-24, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: au.finance.yahoo.com, rses.anu.edu.au, science.sciencemag.org, www.google.com

### `craton-formation-and-the-onset-of-plate-tectonics` (post)

Craton Formation and the Onset of Plate Tectonics — published 2018-04-01, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'

### `credits` (page)

Credits — published 2019-09-06, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.arc.gov.au, www.earthbyte.org

### `finding-particles-in-a-distributed-unstructured-mesh` (post)

Finding Particles in a Distributed, Unstructured Mesh — published 2026-06-04, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `free-surface-in-underworld` (post)

Free surface in Underworld — published 2021-12-03, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `getting-started-60-seconds-to-underworld` (post)

Getting started: 60 seconds to Underworld — published 2019-11-21, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: en.wiktionary.org, macpaw.com, medium.com, underworldcode.ghost.io, www.apple.com, www.computerhope.com, www.facebook.com, www.google.com, www.infoworld.com, www.mozilla.org, www.responsibletravel.com, www.techopedia.com ...

### `getting-started-with-pull-requests` (post)

Getting started with Pull requests — published 2020-11-17, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `group-publications` (page)

Our Publications — published 2019-08-27, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.zotero.org

### `here-comes-conda` (post)

Here comes Conda... — published 2020-11-16, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: docs.conda.io, www.anaconda.com

### `how-many-processors-should-we-use-to-solve-problem-x` (post)

How many processors should we use to solve Problem X? — published 2025-07-27, updated 2026-07-07

- **high** — inline event handler: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'

### `how-to-cite-underworld` (page)

How to cite underworld codes — published 2019-10-14, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `how-to-install-underworld-on-mac-osx-big-sur-apple-silicon-m1` (post)

How to install Underworld on Mac OSX (Apple Silicon M1) — published 2021-09-07, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `how-underworld3-turns-sympy-into-c` (post)

How Underworld3 Turns SymPy into C — published 2026-04-01, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `intro-to-underworld` (page)

Underworld — published 2019-08-13, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: disqus.com, www.arc.gov.au, www.moresi.info, www.nectar.org.au, www.unimelb.edu.au, www.vpac.org

### `ismip-hom-benchmark-experiments-using-underworld` (post)

ISMIP-HOM benchmark experiments using Underworld — published 2023-02-20, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: frank.pattyn.web.ulb.be

### `joss-publication-underworld-2` (post)

JOSS publication - Underworld 2 — published 2020-03-11, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `lavavu` (page)

Lavavu — published 2019-09-11, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: lavavu.github.io, monash.edu.au, www.anaconda.com, www.dannyruijters.nl, www.sqlite.org, www.swig.org

### `lm-publications` (page)

Publications by Louis Moresi — published 2019-10-11, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.zotero.org

### `mesh-variables-and-petsc-vectors-keeping-arrays-in-sync` (post)

Mesh Variables and PETSc Vectors: Keeping Arrays in Sync — published 2026-04-03, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `new-features-of-the-surface-coupling-framework-in-underworld-2` (post)

New features of the surface-coupling framework in Underworld 2 — published 2025-08-25, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `our-journey-from-underworld2-to-underworld3` (post)

Our Journey from Underworld2 to Underworld3 — published 2026-03-23, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `particles-in-underworld3` (post)

Particles in Underworld3 — published 2026-06-03, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `perth-youre-invited-to-the-underworld-geodynamic-modelling-workshop` (post)

Underworld Geodynamic Modelling Workshop. Perth, 7 May 2025 — published 2025-04-29, updated 2026-07-07

- **high** — inline event handler: 2 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: anu-rses-education.github.io, campusmap.curtin.edu.au, forms.gle

### `physical-units-in-computational-geodynamics` (post)

Physical Units in Computational Geodynamics — published 2026-04-08, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `publication-news` (post)

Underworld publication news: Crustal thickness anomalies in stable continents. — published 2020-07-09, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: uwgeodynamics.readthedocs.io

### `publications-using-uw` (page)

Who's Using Underworld — published 2019-10-14, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: mailto:underworld_publications@agora.geophysics-down-under.geoscience.education, www.zotero.org

### `scaling-in-underworld` (post)

Scaling in Underworld — published 2021-03-09, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `self-updating-repositories` (post)

Australian Seismometers in Schools - Noise monitoring dashboard — published 2020-07-17, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: auspass.edu.au, images.theconversation.com, theconversation.com

### `setting-up-underworld-dependencies` (post)

Configuring and Installing PETSc for Underworld — published 2022-01-20, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `shear-bands-with-dilatancy-modelled-with-underworld` (post)

Shear Bands with Dilatancy modelled with Underworld — published 2017-05-05, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: link.springer.com

### `stress-recovery-in-underworld` (post)

Stress recovery in Underworld — published 2021-01-11, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.sciencedirect.com

### `stripy` (page)

Stripy — published 2019-08-27, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: links.underworldcode.org, underworldcode.github.io

### `stripy-2-0-released` (post)

Stripy 2.0 released — published 2020-08-26, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `symbolic-time-derivatives-in-underworld3` (post)

Symbolic Time Derivatives in Underworld3 — published 2026-04-16, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `tags` (page)

Collections of articles by subject — published 2019-08-21, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `the-dynamics-of-continental-accretion` (post)

The Dynamics of Continental Accretion — published 2014-04-01, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.nature.com

### `ugcomm` (page)

About us — published 2019-08-27, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: bgh.org.au

### `underworld-2` (post)

Underworld 2 — published 2015-08-11, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.facebook.com

### `underworld-2-10` (post)

Underworld 2.10 — published 2020-09-04, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `underworld-2-9` (post)

Underworld 2.9 — published 2020-04-03, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: singularity.lbl.gov, www.mpich.org, www.open-mpi.org

### `underworld-and-docker-part-1` (post)

Underworld and Docker (part 1) — published 2015-09-01, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: 192.168.99.100:8888, docs.docker.com, localhost:8888

### `underworld-and-docker-part-2` (post)

Underworld and Docker (part 2) — published 2015-09-15, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: kitematic.com

### `underworld-and-singularity` (post)

Underworld and Singularity — published 2025-04-09, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: opus.nci.org.au, pawsey.atlassian.net

### `underworld-geodynamics-community` (page)

Underworld Geodynamics Community — published 2023-10-18, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `underworld-low-fat-cloud` (post)

Underworld's  lightweight cloud for online classrooms. — published 2020-04-06, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: demon.underworldcloud.org, jupyterhub.github.io, tljh.jupyter.org, www.mybinder.org

### `underworld-model-exchange` (page)

Underworld Model Exchange — published 2020-08-28, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `underworld-on-zenodo` (post)

Cite Underworld from Zenodo — published 2018-10-03, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.zenodo.org

### `underworld-release-2-8` (post)

Underworld Release 2.8 — published 2019-09-03, updated 2026-07-07

- **high** — script-like tag: 4 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: portal.tacc.utexas.edu, pythonclock.org, sebastianraschka.com, singularity.lbl.gov

### `underworld-steering-committee` (page)

Underworld Steering Committee — published 2021-03-17, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `underworld2-workshop-at-cig-2016-meeting` (post)

Underworld2 Workshop at CIG 2016 Meeting — published 2016-02-29, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: docs.docker.com, kitematic.com

### `underworld3-come-and-get-it` (post)

Underworld3 — published 2024-12-08, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: underworldcode.github.io

### `underworld3-published-in-journal-of-open-source-software` (post)

Underworld3 published in Journal of Open Source Software — published 2025-08-25, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: arxiv.org

### `untitled` (post)

Modelling Drips and Delamination with Underworld — published 2017-06-29, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: academic.oup.com

### `untitled-2` (post)

Using physical units in Underworld — published 2017-05-24, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: imgs.xkcd.com, pint.readthedocs.io

### `using-python-virtual-environment-for-underworld-development` (post)

Developing Underworld using Python Virtual Environments — published 2022-01-20, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `uw-mailing-lists` (page)

Underworld Community Mailing list and Discussion Forum — published 2020-08-24, updated 2026-07-07

- **high** — script-like tag: 2 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: forums.geophysics-down-under.geoscience.education

### `uwgeodynamics-and-underworld-merge` (post)

Folding UWGeodynamics into Underworld — published 2022-05-24, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'

### `viscoelasticity` (post)

Viscoelasticity in Underworld2 — published 2019-08-12, updated 2026-07-07

- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: onlinelibrary.wiley.com

### `who-is-using-stripy` (page)

Who's using stripy — published 2020-09-03, updated 2026-07-07

- **high** — script-like tag: 1 occurrence(s)
- **high** — codeinjection_foot: 'ссс'
- **review** — outbound domain not in expected set: www.zotero.org

### `rce` (page)

S — published 2026-07-31, updated 2026-07-31

- **review** — written during compromise window: updated_at 2026-07-31

### `rce-10` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-11` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-12` (page)

S — published 2026-07-31, updated 2026-07-31

- **review** — written during compromise window: updated_at 2026-07-31

### `rce-13` (page)

S — published 2026-07-31, updated 2026-07-31

- **review** — written during compromise window: updated_at 2026-07-31

### `rce-2` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-3` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-4` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-5` (page)

V — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-6` (page)

V — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-7` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-8` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `rce-9` (page)

S — published 2026-07-30, updated 2026-07-30

- **review** — written during compromise window: updated_at 2026-07-30

### `sysinfo-3c8a5c38` (post)

SYSINFO-underworldcode.org — published 2026-07-31, updated 2026-07-31

- **review** — written during compromise window: updated_at 2026-07-31
