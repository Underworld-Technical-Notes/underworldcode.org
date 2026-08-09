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

[-CONTENT-]
