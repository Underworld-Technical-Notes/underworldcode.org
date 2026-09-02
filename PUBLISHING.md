# Minting a DOI

How a note gets a DOI and an archival record. Written against Figshare's actual
API — endpoints and field names below are from `docs.figshare.com/swagger.json`,
not from memory.

The reassuring part first: **everything except the last step is reversible.**

## The sequence

```
POST /account/articles                     create a DRAFT (private)
POST /account/articles/{id}/reserve_doi    → {"doi": "10.xxxx/..."}
        write that DOI into metadata.yml
        rebuild the PDF, so the DOI is on the title page
POST /account/articles/{id}/files          upload the archive package
POST /account/articles/{id}/publish        ← the only irreversible step
```

The order matters and it is the whole reason Figshare works for us: the DOI
exists *before* the PDF is built, so it can be printed on the paper. A provider
that only mints on publication cannot do this — which is why the GitHub–Zenodo
webhook was ruled out, whatever the repository layout.

## What is reversible, and what is not

| step | reversible? |
|---|---|
| create a draft | yes — `DELETE /account/articles/{id}` |
| reserve a DOI | yes while the article is unpublished |
| upload files | yes — files can be replaced or deleted |
| **publish** | **no** — the DOI resolves publicly and permanently |

So the entire workflow can be rehearsed end to end against a real draft, on the
real account, and thrown away. Only `publish` needs care, and it is one call
behind an explicit confirmation flag.

`POST /account/articles/{id}/unpublish` exists, but treat it as unavailable: a
DOI that has resolved is a citation someone may already have used.

## Verified field values

| field | value |
|---|---|
| `license` | `1` (CC BY 4.0 — matches `license: CC-BY-4.0` in our metadata) |
| `defined_type` | `12` preprint, or `11` online resource — **decision needed** |
| `title` | the only field Figshare requires at creation |
| `is_metadata_record` | must stay false; we always deposit a PDF |

`reserve_doi` returns `{"doi": "..."}`. Figshare's own example shows
`10.5072/FK2...`, which is DataCite's *test* prefix — a real account returns a
real one, and that difference is worth checking on the first run.

## Versioning

Publishing an already-published article creates a **new public version**;
updates to a published article affect only the private copy until an explicit
publish. That matches the brief: cosmetic web corrections need no deposit, and
a substantive change is a new version.

**A superseded guide becomes a new version, not a new article.** This is the
editorial rule, and it is why the how-tos are deposited at all. The container
instructions are the case in point: useful to know about, and going out of date.
When they are rewritten, the deposit gets a new version related to its
predecessor. The identifier keeps pointing at the thing it named, the reader
gets the current text, and the superseded text stays retrievable rather than
being quietly replaced.

Publishing it as a *new article* instead would give the same guide two
identifiers with nothing connecting them, and leave whoever cited the first one
holding a reference to advice the project no longer gives.

### Acknowledging the funding

A note about Underworld3 must carry the funding acknowledgement:

> The Underworld project is supported by AuScope and the Australian Government
> through the National Collaborative Research Infrastructure Strategy (NCRIS).
> Source code: github.com/underworldcode/underworld3

Add the slug to `acknowledgements.yml` and the build writes it in, before the
discussion block and into the archival PDF as well as the page. The wording
lives in one place, so it can be corrected once for every note.

It is a list rather than a rule inferred from the text, deliberately: a note
that mentions Underworld3 is not necessarily work the project funded, and
claiming funding that did not happen is worse than omitting one that did.

Three of the eleven Underworld3 notes carried this and eight did not, which is
what an acknowledgement looks like when it depends on an author remembering
rather than on the build.

### Runnable examples, and why they make versioning the normal case

A technical note or a how-to should come with the notebook that runs it.
Anything in `articles/<slug>/examples/` is deposited with the note, so the
archive holds the code and data as well as the prose -- a how-to whose notebook
lives only on the website is a how-to that stops working when the website does.

Examples age faster than the prose around them. An Underworld release changes an
API, a notebook stops running, and the note is still correct about the method
while being wrong about the call. **That is a new version of the same deposit,
not a new article.** Concretely:

1. update the notebook in `examples/`, and the prose if it needs it;
2. merge to `main`;
3. run the deposit with `--new-version`.

Figshare publishes it as v2 and mints a version DOI beside the concept one. The
**concept DOI is what to circulate** -- `10.6084/m9.figshare.<id>` with no `.vN`
-- because it always resolves to the newest version, so a citation made in 2026
still lands on the working notebook in 2030. Anyone who needs the exact text
somebody read can cite `.v1`.

This is the case Figshare was chosen for, more than the first deposit was. A
provider that could only mint on first publication would force every revision to
become a separate record, and the series would accumulate near-duplicate
identifiers for one piece of work.

## One identifier to circulate, and what the record says about the original

**Every archival note is deposited**, excepting the types that get no archival
rendition. `archive_doi` is the identifier: it appears on the PDF, on the page
and in citations, and it resolves to a fixed record with checksums.

The older Rogue Scholar registrations under `10.59350` are **left alone**. They
exist, they keep resolving to the web pages, and that is a perfectly reasonable
thing for them to do. Nothing is built on them and nothing is said about them in
the deposit -- an earlier design declared each new record a variant form of its
legacy DOI, which made the archival record a statement about our migration
history rather than about the article.

What an archival record should say instead is what a reader of a fixed document
actually needs:

| field | says |
|---|---|
| the source URL | where the living article is, so they can see the current version |
| `archived_at` | when this copy was taken, so they can judge how much may have moved on |

Both go into the deposit's `related_materials` and description, onto the PDF's
margin strip, and into the package's README and `CITATION.cff`. A snapshot with
no date cannot be judged against the article it came from; a date with no link
cannot be followed up.

`archived_at` is stamped **once**, when the archival copy is first made, and
never changed. The package is byte-reproducible, and it only stays that way if
nothing inside it comes from the clock at build time.

### What the reader clicks

The DOI must land on something readable. **The PDF is deposited as its own file,
unwrapped and first**, because that is what Figshare previews -- a zip does not,
and a reader who follows a citation to a download button and a file browser has
been failed by the choice of provider.

The archive package sits beside it as the supplement: source, figures,
checksums, `CITATION.cff`. Re-depositing replaces the files rather than adding
to them, so a corrected package never sits beside the one it corrects.

### What must never happen

A note deposited **twice** — two archival records, two DOIs, for one PDF.
`repository_record_id` is the guard: the publish command refuses to create when
it is set, and offers a new version instead. Validation therefore treats an
`archive_doi` without a record id as an error, because the guard would have
nothing to check.

### The real fragility in the legacy DOIs

Those fifty resolve to `www.underworldcode.org/<slug>/`, and **we cannot change
where they point**. Today that is fine because we control the URL. It stops
being fine the moment the URL has to move.

This must be settled with Front Matter before Rogue Scholar is deactivated, and
it is a different question from the one already on the list:

1. Do the fifty registered DOIs keep resolving after deactivation? (asked)
2. **Can their target URLs still be updated afterwards, and by whom?** (not yet
   asked, and more important)

If the answer to (2) is no, then `/​<slug>/` on this domain is a permanent,
unbreakable commitment for fifty articles, and the DOI test in CI is the only
thing standing between a refactor and fifty dead citations. If the answer is
yes, the constraint is merely strict rather than absolute.

### Which notes get a DOI

`article_type` governs it, per the brief: technical notes, worked examples and
benchmarks by default; development notes, how-tos and commentary selectively;
news never.

Note that the legacy set does not follow this — Rogue Scholar minted for
everything it ingested, so a release note in the corpus already carries a DOI.
That is not retrospectively fixable and is not worth trying to fix: the policy
governs what we mint, not what was minted.

## The failure that must never happen

Minting a *second* DOI for a note that already has one. Two guards, both in
place already:

- `metadata.yml` carries `repository_record_id`. If it is set, the publish
  command must refuse to create and offer to make a new version instead.
- `doi-register.csv` holds the fifty legacy Crossref DOIs. Any slug in it
  already has a DOI and must never be deposited as a new record. The validator
  already refuses a legacy DOI paired with a new registrant.

## Still to decide

**Which account — settled: a project account, not an institutional one and not
a personal one.**

ANU is ruled out deliberately. Leadership of Underworld will not always rest
with one person at one institution, and an institutional Figshare mints under
an institution-owned DOI prefix. Those DOIs cannot be re-minted, so they would
carry ANU's identity permanently, including after any move.

A personal figshare.com account mints under `10.6084` — Figshare's own prefix,
carrying no institutional identity at all. That is the desired property.

The account is held by the **project**, named as such (Underworld Geodynamics),
not by a person and not by an invented one. A fictitious identity is a
misrepresentation on a scholarly record, is visible as the depositor, and could
never hold an ORCID — so it could never be verified, which is the one thing an
archival record needs.

This costs nothing, because **custodianship and authorship are separate in
Figshare**: `authors` is set per record. The account owns the deposit; each
note credits its real authors with their real ORCIDs, exactly as `authors.yml`
already records them.

**Continuity comes from the email address**, and it is `help@underworldcode.org`
— the project's own domain, held to 2035, so the account follows the domain
rather than a person or an employer.

The domain has **no MX records**, so mail forwarding has to be added at
Netregistry *before* the account is created: Figshare sends a confirmation to
that address, and changing the email on an existing account afterwards is more
trouble than getting it right once. Send a test message to it first.

### The series as a community object

Figshare **collections** are first-class and answer this directly:
`POST /account/collections`, their own `reserve_doi`, their own author list,
categories and versions.

So the community shows up in two places, neither of which is the login:

- **each note** is an article carrying its real authors and their ORCIDs;
- **the series** is a collection with *its own DOI*, citable as a whole and
  identified independently of any person or institution.

A collection DOI is worth having on its own terms — it gives the series
something to cite, the way a journal has an ISSN — and it happens to be the
same property succession needs.

Zenodo's Communities were the reason to look again, and they turn out not to
be. Their advantage over a collection is that many people can deposit into one
community under curation. That does not apply here: the editorial model is
single-depositor by design — contributors open pull requests and CI deposits on
merge, which is what keeps the fifty registered DOIs safe from a stray
publish. Figshare being chosen for the reader's click-through therefore
stands.

**`defined_type`.** `preprint` reads as a paper awaiting formal publication;
`online resource` is vaguer but truer for a note that is not going anywhere
else. Affects how the record is described and indexed.

**Categories.** Figshare validates on publish, and in practice wants at least
one category plus keywords. Our subject/method facets are the natural source,
but Figshare's category list is its own controlled vocabulary and needs mapping
once.

## What Louis needs to provide

1. The account decision above.
2. A personal API token from that account
   (Figshare → Applications → Personal tokens).
3. The token stored as a GitHub Actions **repository** secret,
   `FIGSHARE_TOKEN`, so a publication can run from CI. Never in the repository
   itself. `gh secret set FIGSHARE_TOKEN --repo <org>/<repo>` prompts for the
   value, so it never reaches the shell history.

   A repository secret rather than an organisation or environment one: nothing
   else needs it, and a narrower scope is a smaller blast radius.

### The token grants everything

Figshare personal tokens have exactly one scope, `all`, and the documentation is
blunt about it: "a personal token which grants you full access to your account."
There is no read-only or deposit-only variant to fall back on.

So the token can publish, and it can delete. **None of the safety in this design
comes from the token** -- it comes from the tooling around it: dry-run by
default, publishing behind an explicit flag, and `repository_record_id` refusing
a second deposit for an article that already has one. Those guards are the whole
of the protection, which is a reason to build them before the first real run
rather than after.

Sent as `Authorization: token <TOKEN>`.

The token belongs to the **project account**, not to a person -- which is the
same succession property the account itself was chosen for.

### Not connecting the GitHub integration

Figshare offers to connect a GitHub account. It is the wrong tool here and
should be left alone.

It imports a **repository** and creates a new version of that item on every
GitHub *release*, with the title and description pulled from GitHub and an MIT
licence applied by default. That is a software-archiving workflow, and it
mismatches this one on every axis that matters:

| | the integration | what we need |
|---|---|---|
| what is deposited | a repository snapshot | one archival PDF per note |
| granularity | one item per repository | one item per article |
| metadata | GitHub's title and description | our authors, ORCIDs, abstract, licence |
| when the DOI exists | on release | **before the PDF is built**, so it can be printed on it |

The last row is decisive, and it is the same reason the Zenodo webhook was ruled
out: an identifier minted at publication cannot appear on the document it
identifies.

There is a worse problem than mismatch. A second deposit path would create
Figshare items that our tooling did not create and does not know about, so
`repository_record_id` -- the guard against minting a second DOI for a note that
already has one -- would have nothing to check. The one failure this design
exists to prevent is exactly the one the integration would enable.

Archiving the Underworld **source** is a real and separate need, and it is
already met: Underworld has been on Zenodo since 2018 under the master DOI
`10.5281/zenodo.1436039`, with a DOI per release. Connecting Figshare to GitHub
would duplicate an arrangement that already works.

### Where the deposit can run, and where it cannot

GitHub does not expose secrets to workflows triggered by a pull request **from a
fork**. That is correct behaviour, and it decides the design: contributors
submit notes by pull request, so the deposit cannot run on the PR. It runs **on
merge to `main`**, or from an explicit `workflow_dispatch`.

That suits the editorial model rather than fighting it — a deposit should follow
acceptance, not submission — and it is what keeps a stray pull request from
minting a DOI.

## What is still to build

Nothing here is written yet — this documents the target, so the design is
settled before code exists.

- an archive-package builder: PDF, source, figures, bibliography, metadata
  JSON, `CITATION.cff`, README, SHA-256 checksums;
- a provider interface — create, reserve, upload, update, publish, new version
  — with a Figshare adapter behind it, so the Zenodo comparison stays possible;
- a publication command that is **dry-run by default**, prints exactly what it
  would deposit, and requires an explicit flag to publish;
- resumability: a run that dies after reserving a DOI must continue, not start
  again and reserve a second one.

## The deposit is offered, not taken

A note reaching `main` without a record gets a pull request titled
**Deposit: <slug>**. The workflow creates a figshare draft and reserves a DOI
for it — both private, both reversible — and commits the identifiers into that
note's own `metadata.yml`. So the request you are reading already contains the
DOI it is asking about, and `deposit-pdf` attaches the archival PDF to it.

**Merging is the decision, and it is the only one.** The push runs the deposit,
which rebuilds the PDF with the DOI on its title page, uploads it with the
archive package, and publishes. Nothing has to be recorded afterwards: the
identifiers arrived with the approval.

Closing the request deposits nothing. The draft is then unused, and it appears
in the weekly *outstanding* issue until it is either merged or cleared with
`--delete-draft`. A reserved DOI never resolves publicly, so an abandoned
request costs nothing but a line in that report.

The reminder is automatic and the decision is not. Nothing is deposited because
a note was published — only because somebody merged the request. That matters
because a published DOI cannot be withdrawn, only superseded.

### Why the approval lives in the note's metadata

It used to live in one shared `deposit-queue.txt`, appended to by every note at
the same line. Two notes in flight therefore conflicted, and merging one broke
the other — so the approvals raced each other, and duplicate requests piled up
for the same note. Per-note files cannot collide.

The trigger watches `articles/**/metadata.yml` and acts on `--approved`, which
is "holds a reserved record, not yet published". A reserved record can only
reach `main` through a merged request, so an ordinary metadata edit — a
keyword, a corrected credit — mints nothing. `--all`, which would deposit
anything undeposited, stays behind an explicit manual mode.

### What still comes back afterwards

One thing: `archive_published_at`, the moment figshare published. It arrives as
a small pull request, and it is bookkeeping — the record id and DOI are already
on `main`, so the guard against a second mint is satisfied whether or not it
lands. It only decides which notes a batch re-version offers. The *outstanding*
report lists it until it is merged.
