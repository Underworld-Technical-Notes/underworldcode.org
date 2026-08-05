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
- **Rotated multi-column identity strip** in the first-page margin, running
  bottom-to-top: published date, article ID, version, licence, Underworld
  version and the URL of the living article. The brief requires the PDF to stay
  intelligible if both the website and the repository record later disappear,
  so these are printed rather than left to the record's metadata. Rotating the
  strip also buys space — label/value pairs sit along the page's long axis
  instead of stacking down a narrow column.

  Two constraints are load-bearing here, and both were found by rendering:
  cells grow *upward* before rotation, which is *leftward* on the page, so a
  cell that wraps pushes its own label off the edge. The live URL is therefore
  set at 6pt to stay on one line, and `scripts/validate_metadata.py` warns when
  a slug is long enough to wrap it anyway. Aligning the grid `top` instead of
  `bottom` clips every label — don't.

- **Figure captions** in sans-serif at 8pt, `luma(90)`, so they read as
  apparatus rather than body text.
- **Abstract no longer required** — migrated Ghost posts have an excerpt rather
  than a formal abstract, and a missing one must not fail the build.
