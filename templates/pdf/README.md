# Underworld Technical Note — archival PDF template

Forked from [lapreprint-typst](https://github.com/myst-templates/lapreprint-typst)
(MIT, see `LICENSE`) by Rowan Cockett and Franklin Koch.

Changes from upstream:

- **Text column widened** — upstream reserves 25% of the page for margin notes.
  These are code-heavy notes: 90% of code lines need ~72 characters and 95% need
  ~84, which did not fit. The margin is 19%.
- **Controlled code treatment** — block code at 8pt on a tinted panel with a
  rule, inline code boxed at 8.5pt. The brief calls for controlled code wrapping
  and syntax treatment; at 8pt the 95th-percentile line fits without wrapping
  mid-token.
- **Archival identity block** in the first-page margin: article ID, version,
  licence, Underworld version, and the URL of the living article. The brief
  requires the PDF to stay intelligible if both the website and the repository
  record later disappear, so these are printed rather than left to the
  record's metadata.
- **Abstract no longer required** — migrated Ghost posts have an excerpt rather
  than a formal abstract, and a missing one must not fail the build.
