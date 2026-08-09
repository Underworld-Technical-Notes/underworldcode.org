#import "frontmatter.typ": orcidLogo, loadFrontmatter

#let template(
  // The paper's title.
  title: "Paper Title",
  subtitle: none,

  // An array of authors. For each author you can specify a name, orcid, and affiliations.
  // affiliations should be content, e.g. "1", which is shown in superscript and should match the affiliations list.
  // Everything but but the name is optional.
  authors: (),
  // This is the affiliations list. Include an id and `name` in each affiliation. These are shown below the authors.
  affiliations: (),
  // The paper's abstract. Can be omitted if you don't have one.
  abstract: none,
  // The short-title is shown in the running header
  short-title: none,
  // The short-citation is shown in the running header, if set to auto it will show the author(s) and the year in APA format.
  short-citation: auto,
  // The venue is show in the footer
  venue: none,
  // An image path that is shown in the top right of the page. Can also be content.
  logo: none,
  // A DOI link, shown in the header on the first page. Should be just the DOI, e.g. `10.10123/123456` ,not a URL
  doi: none,
  // When this archival PDF was made, and the web article it was made from.
  // Together these say what a reader of a fixed document most needs to know:
  // where the living version is, and how old this snapshot of it is.
  archived: none,
  source-url: none,
  heading-numbering: "1.a.i",
  // Show an Open Access badge on the first page, and support open science, default is true, because that is what the default should be.
  open-access: true,
  // A list of keywords to display after the abstract
  keywords: (),
  // The "kind" of the content, e.g. "Original Research", this is shown as the title of the margin content on the first page.
  kind: none,
  // Content to put on the margin of the first page
  // Should be a list of dicts with `title` and `content`
  margin: (),
  paper-size: "us-letter",
  // A color for the theme of the document
  theme: blue.darken(30%),
  // Date published, for example, when you publish your preprint to an archive server.
  // To hide the date, set this to `none`. You can also supply a list of dicts with `title` and `date`.
  date: datetime.today(),
  // Feel free to change this, the font applies to the whole document
  font-face: none,
  // -- Underworld Technical Notes additions ------------------------------
  // The archival publication's identity. The brief requires the PDF to remain
  // intelligible if both the website and the repository later disappear, so
  // these are printed on the page rather than left to the record's metadata.
  article-id: none,
  article-version: none,
  license: none,
  software-version: none,
  live-url: none,
  // Release the first page's wide left margin for the body.
  wide-body: true,
  // -----------------------------------------------------------------------
  // The path to a bibliography file if you want to cite some external works.
  bibliography-file: none,
  bibliography-style: "apa",
  // The paper's content.
  body
) = {
  let spacer = text(fill: gray)[#h(8pt) | #h(8pt)]

  let dates;
  if (type(date) == datetime) {
    dates = ((title: "Published", date: date),)
  } else if (type(date) == dictionary) {
    dates = (date,)
  } else {
    dates = date
  }
  date = dates.at(0).date

  // Create a short-citation, e.g. Cockett et al., 2023
  let year = if (date != none) { ", " + date.display("[year]") }
  if (short-citation == auto and authors.len() == 1) {
    short-citation = authors.at(0).name.split(" ").last() + year
  } else if (short-citation == auto and authors.len() == 2) {
    short-citation = authors.at(0).name.split(" ").last() + " & " + authors.at(1).name.split(" ").last() + year
  } else if (short-citation == auto and authors.len() > 2) {
    short-citation = authors.at(0).name.split(" ").last() + " " + emph("et al.") + year
  } else if (short-citation == auto) {
    short-citation = none
  }

  // Set document metadata.
  set document(title: title, author: authors.map(author => author.name))

  show link: it => [#text(fill: theme)[#it]]
  show ref: it => [#text(fill: theme)[#it]]

  set page(
    paper-size,
    margin: (left: 11%, right: 9%),
    header: context {
      let loc = here()
      if(loc.page() == 1) {
        let headers = (
          if (open-access) {smallcaps[Open Access]},
          if (doi != none) { link("https://doi.org/" + doi, "https://doi.org/" + doi)}
        )
        return align(left, text(size: 8pt, fill: gray, headers.filter(header => header != none).join(spacer)))
      } else {
        return align(right, text(size: 8pt, fill: gray.darken(50%),
          (short-title, short-citation).join(spacer)
        ))
      }
    },
    footer: block(
      width: 100%,
      stroke: (top: 1pt + gray),
      inset: (top: 8pt, right: 2pt),
      context [
        #grid(columns: (75%, 25%),
          align(left, text(size: 9pt, fill: gray.darken(50%),
              (
                if(venue != none) {emph(venue)},
                if(date != none) {date.display("[month repr:long] [day], [year]")}
              ).filter(t => t != none).join(spacer)
          )),
          align(right)[
            #text(
              size: 9pt, fill: gray.darken(50%)
            )[
              #counter(page).display() of #counter(page).final().first()
            ]
          ]
        )
      ]
    )
  )

  // Set the body font.
  if (font-face != none) {
    set text(font: font-face, size: 10pt)
  } else {
    set text(size: 10pt)
  }
  // Code: 8pt fits the 95th-percentile line (84 chars) without wrapping.
  show raw.where(block: true): it => block(
    width: 100%,
    fill: luma(248),
    stroke: (left: 2pt + luma(220)),
    inset: (x: 7pt, y: 6pt),
    radius: 2pt,
    text(size: 8pt, it),
  )
  show raw.where(block: false): it => box(
    fill: luma(245), inset: (x: 2pt), outset: (y: 2pt), radius: 1pt,
    text(size: 8.5pt, it),
  )

  // Figure captions read as apparatus, not body text: sans-serif for contrast
  // against the serif body, smaller and lighter.
  show figure.caption: it => text(
    font: ("Helvetica Neue", "Helvetica", "Arial"),
    size: 8pt,
    fill: luma(90),
    it,
  )

  // Configure equation numbering and spacing.
  set math.equation(numbering: "(1)")
  show math.equation: set block(spacing: 1em)

  // Configure lists.
  set enum(indent: 10pt, body-indent: 9pt)
  set list(indent: 10pt, body-indent: 9pt)

  // Configure headings.
  set heading(numbering: heading-numbering)
  show heading: it => context {
    let loc = here()
    // Find out the final number of the heading counter.
    let levels = counter(heading).at(loc)
    set text(10pt, weight: 400)
    if it.level == 1 [
      // First-level headings are centered smallcaps.
      // We don't want to number of the acknowledgment section.
      #let is-ack = it.body in ([Acknowledgment], [Acknowledgement])
      // #set align(center)
      #set text(if is-ack { 10pt } else { 12pt })
      #show: smallcaps
      #v(20pt, weak: true)
      #if it.numbering != none and not is-ack {
        numbering(heading-numbering, ..levels)
        [.]
        h(7pt, weak: true)
      }
      #it.body
      #v(13.75pt, weak: true)
    ] else if it.level == 2 [
      // Second-level headings are run-ins.
      #set par(first-line-indent: 0pt)
      #set text(style: "italic")
      #v(10pt, weak: true)
      #if it.numbering != none {
        numbering(heading-numbering, ..levels)
        [.]
        h(7pt, weak: true)
      }
      #it.body
      #v(10pt, weak: true)
    ] else [
      // Third level headings are run-ins too, but different.
      #if it.level == 3 {
        numbering(heading-numbering, ..levels)
        [. ]
      }
      _#(it.body):_
    ]
  }


  if (logo != none) {
    place(
      top,
      dx: -12%,
      float: false,
      box(
        width: 10%,
        {
          if (type(logo) == content) {
            logo
          } else {
            image(logo, width: 100%)
          }
        },
      ),
    )
  }


  // Title and subtitle
  box(inset: (bottom: 2pt), width: 100%, text(17pt, weight: "bold", fill: theme, title))
  if subtitle != none {
    parbreak()
    box(width: 100%, text(14pt, fill: gray.darken(30%), subtitle))
  }
  // Authors and affiliations
  if authors.len() > 0 {
    box(inset: (y: 10pt), {
      authors.map(author => {
        text(11pt, weight: "semibold", author.name)
        h(1pt)
        if "affiliations" in author {
          super(author.affiliations)
        }
        if "orcid" in author {
          orcidLogo(orcid: author.orcid)
        }
      }).join(", ", last: ", and ")
    })
  }
  if affiliations.len() > 0 {
    // On its own line. Both of these are inline boxes, so without the break
    // the affiliation ran straight into the author's ORCID mark --
    // "Louis Moresi(1)(orcid)(1)Australian National University".
    linebreak()
    box(inset: (bottom: 10pt), {
      affiliations.map(affiliation => {
        super(affiliation.id)
        h(1pt)
        affiliation.name
      }).join(", ")
    })
  }


  // First-page information block, rotated to run bottom-to-top up the left
  // margin as a single multi-column strip. Rotation is decorative but it also
  // buys space: label/value pairs that would stack down a narrow column sit
  // side by side along the page's long axis instead.
  let field(label, value, link-target: none, size: 7pt) = {
    box({
      text(size: 6.5pt, fill: theme, weight: "bold", upper(label))
      linebreak()
      if (link-target != none) {
        text(size: size, link(link-target, value))
      } else {
        text(size: size, value)
      }
    })
  }

  let cells = ()
  if (kind != none) {
    cells.push(text(11pt, fill: theme, weight: "semibold", smallcaps(kind)))
  }
  if (dates != none) {
    for d in dates {
      cells.push(field(d.title, d.date.display("[month repr:short] [day], [year]")))
    }
  }
  // Archival identity. Printed on the page so the PDF stays self-describing
  // even if the site and the repository record are both gone.
  if (article-id != none) { cells.push(field("Article", article-id)) }
  if (article-version != none) { cells.push(field("Version", article-version)) }
  if (license != none) { cells.push(field("Licence", license)) }
  if (software-version != none) { cells.push(field("Underworld", software-version)) }
  // The DOI is the published identifier; slugs are an implementation detail of
  // the website and do not belong on the archival record.
  if (doi != none) {
    cells.push(field("DOI", doi, link-target: "https://doi.org/" + doi))
  }
  // A fixed document should say when it was fixed, and against what. Without
  // the date a reader cannot tell whether the living article has moved on;
  // without the link they cannot go and see.
  if (archived != none) { cells.push(field("Archived", archived)) }
  if (source-url != none) {
    cells.push(field("Source", source-url, link-target: source-url))
  }
  for side in margin {
    if ("title" in side) {
      cells.push({
        text(size: 6.5pt, fill: theme, weight: "bold", upper(side.title))
        linebreak()
        text(size: 7pt, side.content)
      })
    }
  }

  if (cells.len() > 0) {
    place(
      left + bottom,
      // Offset found by rendering: at -12% the labels clip off the page
      // edge. The strip grows outward from this origin, so it must sit far
      // enough inside the margin to fit its own thickness.
      dx: -8%,
      dy: 0pt,
      rotate(-90deg, origin: left + bottom, box(
        width: 200mm,
        height: 14mm,
        grid(
          columns: cells.map(_ => auto),
          column-gutter: 1.6em,
          align: bottom + left,
          ..cells,
        ),
      )),
    )
  }


  let abstracts
  if (type(abstract) == content or type(abstract) == str) {
    abstracts = ((title: "Abstract", content: abstract),)
  } else {
    abstracts = abstract
  }

if (abstracts != none and abstracts.len() > 0) {
    box(inset: (top: 16pt, bottom: 16pt), width: 100%, stroke: (top: 1pt + gray, bottom: 1pt + gray), {
      abstracts.map(abs => {
        set par(justify: true)
        text(fill: theme, weight: "semibold", size: 9pt, abs.title)
        parbreak()
        abs.content
      }).join(parbreak())
    })
  }
  if (keywords.len() > 0) {
    text(size: 9pt, {
      text(fill: theme, weight: "semibold", "Keywords")
      h(8pt)
      keywords.join(", ")
    })
  }
  v(10pt)

  show par: set par(spacing: 1.5em)

  // Typst 0.13 does honour a `set page` after the first page, so a title page
  // with a wider body is available -- but it is not worth it here: measured
  // across these eleven articles it cost 7 extra pages, because the page it
  // adds is never paid back by the wider measure. The rotated strip is thin
  // enough that one modest margin serves every page.
  body

  if (bibliography-file != none) {
    show bibliography: set text(8pt)
    bibliography(bibliography-file, title: text(10pt, "References"), style: bibliography-style)
  }
}
