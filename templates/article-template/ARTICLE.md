---
title: A short, specific title
description: >-
  One or two sentences. This becomes the abstract in the PDF and the summary
  in listings, so write it for someone deciding whether to read on.
date: 2026-01-01
authors:
  - name: Your Name
    orcid: 0000-0000-0000-0000
    affiliations:
      - Your Institution
license: CC-BY-4.0
keywords:
  - Underworld Code
exports:
  - format: typst
    template: ../../templates/pdf
    output: SLUG.pdf
    article_id: UWTN 2026-000
    article_version: 1.0.0
    software_version: underworld3 0.0.0
---

Open with the question the note answers. Assume a reader who knows geodynamics
but not this corner of Underworld.

## A section

Maths is plain LaTeX, inline as $\nabla \cdot \boldsymbol{\sigma} = 0$. Display
maths goes in a `math` directive rather than a `$$` block: both build, but the
fence survives an editor that is not a MyST editor, and it takes a label
without the two traps `$$` has (see CONTRIBUTING.md).

```{math}
:label: eq-momentum
-\nabla \cdot \boldsymbol{\sigma}(u, \nabla u) - \mathbf{f}(u, \nabla u) = 0
```

Refer to it as {eq}`eq-momentum`. Drop the `:label:` line if nothing refers to
the equation.

Code blocks are fenced and language-tagged. Keep lines under ~84 characters:
that is the 95th percentile of this corpus and it is what fits the PDF measure
without wrapping.

```python
import underworld3 as uw

mesh = uw.meshing.UnstructuredSimplexBox(cellSize=0.05)
```

### Figures, badges and inline images — state the intent

This is the one place worth being explicit. The migration converter had to
*guess* these from rendered HTML; when you author a note, say which you mean.

A **numbered figure** with a caption — for anything you refer to in the text:

```{figure} figures/example.png
:alt: Short description for a reader who cannot see the image.

The caption. Keep it informative; it is set smaller and lighter than the body,
so it reads as apparatus rather than prose.
```

A **badge or small inline graphic** — not numbered, sized to itself:

```{image} figures/status.svg
:alt: DOI
:width: 168px
```

Two mystmd limitations to know before reaching for something else, both
verified by rendering (see `templates/pdf/README.md`):

- `:target:` on an `{image}` is silently ignored by both renderers, so badges
  are not clickable. Put the link in the text if it matters.
- A markdown linked image with a `doi.org` target is rewritten into a citation
  and the image is destroyed. Cite the DOI in text instead.

## Citing

**Do not write a References section.** MyST generates one from your citations,
and a hand-written list next to it produces two -- which is what happened to
every migrated note that had one.

The quickest way, with no bibliography file at all: cite the DOI, and MyST
fetches the reference from doi.org.

    Narrative:      @10.21105/joss.07831 showed that ...
    Parenthetical:  ... as others have found [@10.21105/joss.07831].

Both render as "Moresi et al. (2025)" and "(Moresi et al., 2025)", and the full
entry appears under an automatic **References** heading at the end.

For a note with many references, or one citing work without a DOI, put a
`references.bib` beside the article and name it in the front matter:

    bibliography:
      - references.bib

then cite by key -- `@farrington2014` or `[@farrington2014]` -- exactly as
above. The two can be mixed freely.

Verified by rendering: all four forms work in the web page and in the archival
PDF, and produce one references section.

## Examples

Notebooks and small data files go in `examples/` beside this file. They are
deposited with the note, so the archived record carries working code.

When a release breaks one, update it and publish a **new version** of the same
deposit rather than a new note — the DOI already in circulation then resolves to
the working notebook.
