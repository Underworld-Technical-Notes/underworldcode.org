# Writing a technical note

```bash
pixi run new --slug my-note-slug --title "My note" --author louis
```

That creates `articles/<slug>/` from `templates/article-template`, allocates an
article ID that cannot collide with an existing note or with one the legacy
backfill will later claim, and fills in your details from `authors.yml`. Add the
file to the `toc` in `myst.yml`, then:

```bash
pixi run build     # HTML site + archival PDF
pixi run test      # metadata validation + the DOI URL test
pixi run myst start
```

## Things that are load-bearing

- **The article file must be named `<slug>.md`.** MyST takes a page's URL from
  the filename, not the path, so this is what publishes the note at `/<slug>/`.
  Renaming it to `index.md` changes the URL. `pixi run validate` rejects that.
- **Never change the slug of a published note.** Fifty legacy notes carry
  Crossref DOIs that resolve to `/<slug>/` and cannot be re-pointed;
  `pixi run test-dois` fails the build if any would 404.
- **Article IDs are permanent.** Once an ID appears in a deposited PDF it must
  not move, which is why they are allocated across the whole corpus rather than
  per batch.
- **State the intent for images.** A numbered figure, a badge and an inline
  graphic are three different things; see the template and
  `templates/pdf/README.md` for the two mystmd limitations worth knowing.

## Adding an author

Add them to `authors.yml` with their ORCID. ORCIDs are left `null` rather than
guessed — attaching a wrong one attributes someone's work to a stranger — and
`pixi run validate` warns about any that are missing on a DOI-bearing article.
