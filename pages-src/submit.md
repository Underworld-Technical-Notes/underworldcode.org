Underworld Technical Notes publishes methods and implementation notes, worked
examples, benchmarks and design rationale from the Underworld community. If you
have built something with Underworld and written down how it works, it belongs
here.

Notes are submitted as pull requests. That is not ceremony: it is what lets the
review happen in the open, keeps the full history of an article, and means the
published version and its source are the same thing.

## What gets published

| type | what it is |
|---|---|
| Technical note | How a method, algorithm or piece of the implementation works |
| Worked example | A reproducible model, with the code to run it |
| Benchmark | A validation or comparison, with numbers |
| Development note | Why something was designed the way it was |
| How-to | Durable installation or workflow guidance |

A note should be readable by someone who knows geodynamics but not this corner
of the code. It does not need to be long. Several of the notes here are a
thousand words and one figure.

## Submitting

You will need a GitHub account, and an [ORCID](https://orcid.org) if you would
like to be properly credited — we do not guess at them.

```bash
git clone https://github.com/Underworld-Technical-Notes/underworldcode.org
cd underworldcode.org

pixi run new --slug my-note --title "My note" --author yourname
```

That creates `articles/my-note/` with the article, its metadata and a place for
figures. Write it, then:

```bash
pixi run build      # the web page and the archival PDF
pixi run test       # metadata, links and the checks below
pixi run myst start # read it as it will appear
```

Open a pull request. The build runs on it, so you will see any problem before a
reviewer does.

## What happens next

1. **Review** in the pull request — on the science and on the writing.
2. **Merge**, and the note appears on the site.
3. **A DOI**, if the note is one of the types that gets one, minted from
   Figshare with the identifier printed on the archival PDF.
4. **The PDF is deposited** with its source, figures and checksums, so the
   article survives this website.

The DOI identifies the fixed archival publication. The page here is the living
version and may pick up corrections, better links and discussion.

## Things worth knowing before you write

**If the work was funded, say so.** Notes about Underworld3 carry the AuScope
and NCRIS acknowledgement; add your slug to `acknowledgements.yml` and the build
puts it in, on the page and in the PDF.

**Attach the notebook.** A note that describes how to do something should come
with something that does it. Put notebooks and any small data files in
`articles/<slug>/examples/`; they are deposited with the note, so the archive
carries working code rather than a description of code.

Examples date faster than prose — an Underworld release changes an API and a
notebook stops running, while the note remains right about the method. When that
happens the fix is a **new version of the same deposit**, not a new note: update
the notebook, merge, and the DOI you have already circulated starts resolving to
the working version. That is deliberate, and it is why the series is on a
repository that versions.

**Commit your figure sources, not just the pictures.** If a figure is drawn from
data, the script and the data belong beside it. Sixteen figures in the older
material on this site went dark when the server they were linked from was
retired — and not one of them was recoverable from the Internet Archive. They
came back only because copies existed elsewhere, which was luck rather than
design.

**Keep code lines under about 84 characters.** That is what fits the archival
PDF's measure without wrapping mid-token.

**Say what an image is.** A numbered figure, a badge and an inline graphic are
three different things, and the template treats them differently.

**A slug is permanent once a DOI points at it.** Choose the URL you want to
live with; it cannot be changed afterwards without breaking a citation.

**Maths is LaTeX**, inline as `$...$` and displayed as `$$...$$`.

**Do not write a References section by hand.** Cite the DOI and MyST fetches the
reference and builds the list for you:

```markdown
@10.21105/joss.07831 showed that ...
... as others have found [@10.21105/joss.07831].
```

That needs no bibliography file, and it is fine while you are drafting. Before a
note is published, **pin its references**: add a `references.bib` beside the
article, name it in the front matter as `bibliography: [references.bib]`, and
cite by key in one form, `[@farrington2014]`.

Pinning is not tidiness. A citation given as a bare DOI is fetched from doi.org
at build time, so the build depends on doi.org answering — one note resolved
fine locally and failed on CI with *Citation data was not available or
malformed*, which would have published a broken reference. A DOI containing
parentheses fails a second way: the inline form stops at the first bracket.
Neither can be repaired in a PDF that has already been deposited.

This is worth insisting on because the alternative is not merely untidy. A
hand-written list whose entries are links gets read as citations, and the note
ends up with two reference sections: the older material on this site is being
repaired for exactly that.

Everything is published under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/),
so you keep the credit and anyone may build on the work.

## If a pull request is not for you

It should not be the barrier. Open a
[discussion](https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions)
with what you have — a draft, a notebook, a paper section — and we will help
turn it into a note.
