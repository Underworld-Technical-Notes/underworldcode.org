# Underworld Technical Note — archival PDF template

Forked from [lapreprint-typst](https://github.com/myst-templates/lapreprint-typst)
(MIT, see `LICENSE`) by Rowan Cockett and Franklin Koch.

Changes from upstream:

- **Margin slimmed to 11%/9%** — upstream reserves 25% of the page for stacked
  margin notes. Rotating the identity block changed what it costs: a strip needs
  only its own thickness, about 14mm, not a quarter of the page. So the margin
  shrinks on *every* page and the code fits. 90% of code lines in this corpus
  need ~72 characters and 95% need ~84; none of them wrap now.
- **Controlled code treatment** — block code at 8pt on a tinted panel with a
  rule, inline code boxed at 8.5pt. The brief calls for controlled code wrapping
  and syntax treatment; at 8pt the 95th-percentile line fits without wrapping
  mid-token.
- **Rotated multi-column identity strip** in the first-page margin, running
  bottom-to-top: published date, article ID, version, licence, Underworld
  version and the URL of the living article. The brief requires the PDF to stay
  intelligible if both the website and the repository record later disappear,
  so these are printed rather than left to the record's metadata. Rotating the
  strip also buys space — label/value pairs sit along the page's long axis
  instead of stacking down a narrow column.

  The strip carries the **DOI, not the article's URL**: the DOI is the published
  identifier, and slugs are an implementation detail of the website that does
  not belong on an archival record.

  Two constraints are load-bearing, and both were found by rendering rather than
  by reasoning: the strip grows outward from its placement origin, so `dx` must
  sit far enough inside the margin to fit the strip's own thickness or the
  labels clip silently off the page edge (-12% clips, -8% does not). And
  aligning the grid `top` instead of `bottom` clips every label — don't.

- **No title page.** Typst 0.13 *does* honour a `set page` after the first page,
  so a narrow-margin title page followed by a wide-measure body is available.
  Measured across these eleven articles it cost **7 extra pages** — the page it
  adds per article is never paid back by the wider measure. One modest margin
  throughout gives the same 58 pages as the original layout while fitting the
  code.

- **Figure captions** in sans-serif at 8pt, `luma(90)`, so they read as
  apparatus rather than body text.
- **Abstract no longer required** — migrated Ghost posts have an excerpt rather
  than a formal abstract, and a missing one must not fail the build.
