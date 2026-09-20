#import "lapreprint.typ": *
#show: template.with(
  title: "[-doc.title-]",
[# if parts.abstract or parts.summary #]
  abstract: (
[# if parts.abstract #]
    (
      title: "Abstract",
      content: [
[-parts.abstract-]
      ]
    ),
[# endif #]
[# if parts.summary #]
    (
      title: "Plain Language Summary",
      content: [
[-parts.summary-]
      ]
    ),
[# endif #]
  ),
[# endif #]
[# if doc.subtitle #]
  subtitle: "[-doc.subtitle-]",
[# endif #]
[# if doc.short_title #]
  short-title: "[-doc.short_title-]",
[# endif #]
[# if options.short_citation #]
  short-citation: "[-options.short_citation-]",
[# endif #]
[# if options.heading_numbering #]
  heading-numbering: "[-options.heading_numbering-]",
[# endif #]
[# if options.theme #]
  theme: [-options.theme-],
[# endif #]
[# if doc.open_access !== undefined #]
  open-access: [-doc.open_access-],
[# endif #]
[# if doc.doi #]
  doi: "[-doc.doi-]",
[# endif #]
[# if doc.date #]
  date: datetime(
    year: [-doc.date.year-],
    month: [-doc.date.month-],
    day: [-doc.date.day-],
  ),
[# endif #]
[# if doc.keywords #]
  keywords: (
    [#- for keyword in doc.keywords -#]"[-keyword-]",[#- endfor -#]
  ),
[# endif #]
[# if doc.bibtex #]
  bibliography-file: "[-doc.bibtex-]",
[# endif #]
  authors: (
[# for author in doc.authors #]
    (
      name: "[-author.name-]",
[# if author.orcid #]
      orcid: "[-author.orcid-]",
[# endif #]
[# if author.affiliations #]
      affiliations: "[#- for aff in author.affiliations -#][-aff.index-][#- if not loop.last -#],[#- endif -#][#- endfor -#]",
[# endif #]
    ),
[# endfor #]
  ),
  affiliations: (
[# for aff in doc.affiliations #]
    (
      id: "[-aff.index-]",
      name: "[-aff.name-]",
    ),
[# endfor #]
  ),
[# if doc.venue.title #]
  venue: "[-doc.venue.title-]",
[# endif #]
[# if options.article_id #]
  article-id: "[-options.article_id-]",
[# endif #]
[# if options.article_version #]
  article-version: "[-options.article_version-]",
[# endif #]
[# if doc.license.content.id #]
  license: "[-doc.license.content.id-]",
[# endif #]
[# if options.archived #]
  archived: "[-options.archived-]",
[# endif #]
[# if options.series #]
  series: "[-options.series-]",
[# endif #]
[# if options.origin_url #]
  source-url: "[-options.origin_url-]",
[# endif #]
[# if options.software_version #]
  software-version: "[-options.software_version-]",
[# endif #]
[# if options.wide_body !== undefined #]
  wide-body: [-options.wide_body-],
[# endif #]
[# if options.logo #]
  logo: "[-options.logo-]",
[# endif #]
[# if options.kind #]
  kind: "[-options.kind-]",
[# endif #]
  margin: (
[# if parts.acknowledgements #]
    (
      title: "Acknowledgements",
      content: [
[-parts.acknowledgements-]
      ],
    ),
[# endif #]
[# if parts.availability #]
    (
      title: "Data Availability",
      content: [
[-parts.availability-]
      ],
    ),
[# endif #]
  ),
)

[-IMPORTS-]

// The house table style. MyST renders every markdown table as
// `tablex(columns: n, header-rows: 1, ..tableStyle, ..columnStyle, ...)`
// with both dictionaries EMPTY in its generated myst-imports.typ, so the
// template sets the style by shadowing them here, after that import and
// before the content. Horizontal hairlines only, no verticals; the header
// row filled in the theme blue with light text; the table centred. The
// site's CSS (static/uwtn.css, "tables") carries the same design to HTML.
#import "@preview/tablex:0.0.9": tablex as tablex-base
#let uwtn-theme = blue.darken(30%)
#let uwtn-table-sans = ("Helvetica Neue", "Helvetica", "Arial")
#let tableStyle = (
  auto-vlines: false,
  auto-hlines: true,
  map-hlines: h => (..h, stroke: 0.3pt + luma(165)),
  fill: (col, row) => if row == 0 { uwtn-theme } else { none },
  map-cells: c => if c.y == 0 {
    (..c, content: text(font: uwtn-table-sans, size: 8pt, weight: "semibold",
                        fill: blue.lighten(88%), c.content))
  } else {
    (..c, content: text(size: 9pt, c.content))
  },
  inset: (x: 8pt, y: 4.5pt),
)
#let tablex(..args) = align(center, block(above: 10pt, below: 12pt, tablex-base(..args)))

[-CONTENT-]
