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

**Commit your figure sources, not just the pictures.** If a figure is drawn from
data, the script and the data belong beside it. Seven figures in the older
material on this site no longer exist, because they were linked from a server
that went away — and nothing, not even the Internet Archive, kept a copy.

**Keep code lines under about 84 characters.** That is what fits the archival
PDF's measure without wrapping mid-token.

**Say what an image is.** A numbered figure, a badge and an inline graphic are
three different things, and the template treats them differently.

**A slug is permanent once a DOI points at it.** Choose the URL you want to
live with; it cannot be changed afterwards without breaking a citation.

**Maths is LaTeX**, inline as `$...$` and displayed as `$$...$$`.

Everything is published under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/),
so you keep the credit and anyone may build on the work.

## If a pull request is not for you

It should not be the barrier. Open a
[discussion](https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions)
with what you have — a draft, a notebook, a paper section — and we will help
turn it into a note.
