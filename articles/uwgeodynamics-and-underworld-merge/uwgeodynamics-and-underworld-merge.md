---
title: Folding UWGeodynamics into Underworld
date: 2022-05-24
authors:
  - name: Romain Beucher
    orcid: 0000-0003-3891-5444
    affiliations:
      - Australian National University
doi: 10.59350/ng0d5-23959
license: CC-BY-4.0
banner: figures/banner.jpg
exports:
  - format: typst
    template: ../../templates/pdf
    output: uwgeodynamics-and-underworld-merge.pdf
    article_id: UWTN 2022-003
    article_version: 1.0.0
parts:
  abstract: "Yeah, one repo, one vision! In an effort to simplify maintenance and compatibility between Underworld and UWGeodynamics, we have decided to merge the codes into a single repository. Starting with version 2.13, UWGeodynamics will now live under Underworld. All UWGeodynamics functionalities and workflows will remain available to the users. From version 2.13 users will be able to import UWGeodynamics after installing Underworld (see documentation for install options), using from underworld impor"
---
<div class="uwtn-banner"><img src="figures/banner.jpg" alt=""><div class="uwtn-credit">Photo by <a href="https://unsplash.com/@lisanto_?utm_source=underworld-technical-notes&utm_medium=referral&utm_campaign=api-credit">Lisanto 李奕良</a> / <a href="https://unsplash.com/?utm_source=underworld-technical-notes&utm_medium=referral&utm_campaign=api-credit">Unsplash</a></div></div>

Yeah, one repo, one vision!

In an effort to simplify maintenance and compatibility between Underworld and UWGeodynamics, we have decided to merge the codes into a single  repository.

Starting with version 2.13, UWGeodynamics will now live under [Underworld](https://github.com/underworldcode/underworld2).

All UWGeodynamics functionalities and workflows will remain available to the users. **From version 2.13** users will be able to import `UWGeodynamics` after installing `Underworld` (see documentation for install options), using `from underworld import UWGeodynamics`.

Issues, functionality requests and pull requests will have to be submitted to the Underworld repository.

The [UWGeodynamics](https://github.com/underworldcode/UWGeodynamics) repository has been archived and is now read-only. Older versions of `UWGeodynamics` will remain available but will NOT be made compatible with newer versions of its dependencies.

We encourage users to update their Underworld package as soon as possible.

We understand this can be an inconvenience to some users. This will allow us to focus on development by reducing maintenance work.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=uwgeodynamics-and-underworld-merge">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=uwgeodynamics-and-underworld-merge">Start one</a></div></div>
