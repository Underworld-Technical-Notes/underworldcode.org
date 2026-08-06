# Standing the organisation up

Everything below needs `admin:org`, which the local `gh` token does not have —
its scopes are `gist`, `read:org`, `repo`. These are the steps only Louis can
take; each is quick, and after step 4 the rest is automated.

## 1. Create the organisation

<https://github.com/organizations/plan> → **Free** → name `underworld-technical-notes`.

The name is available as of 2026-08-06. Use the free plan: Actions and Pages are
free for public repositories.

## 2. Add a second owner

Settings → People → Invite member → set role **Owner**.

A core UW3 developer (gthyagi or bknight1) is the natural choice — no new trust
relationship, since they are already core on `underworld3`. This is a
bus-factor backstop, not a change of editor: Louis still merges.

> Why a separate org rather than `underworldcode`: co-editors need owner rights
> over the publication without gaining them over Underworld source. Reusing an
> existing org couples the two permission sets permanently.

## 3. Create the repository

Name it `underworldcode.org` — matching the domain makes the Pages custom-domain
binding self-documenting. Public, and **do not** initialise with a README; the
local repository already has its history.

## 4. Push

```bash
cd ~/+Underworld/underworld-technical-notes
git remote add origin https://github.com/underworld-technical-notes/underworldcode.org.git
git branch -M main
git push -u origin main
```

## 5. Turn CI on

Nothing to configure — `.github/workflows/test.yml` runs on push. Confirm the
first run is green. It runs the unit tests, validates article metadata, builds
the site and the archival PDFs, and asserts that no registered DOI is broken.

## 6. Enable Pages — but not the custom domain yet

Settings → Pages → Source: **GitHub Actions**.

The site will publish at
`https://underworld-technical-notes.github.io/underworldcode.org/`.

**Leave the custom domain unset for now.** Two reasons:

- `www.underworldcode.org` still points at the Ghost droplet and is the live
  site. Repointing it is the cutover (plan Stage 3) and needs the full
  redirect check first.
- The apex `underworldcode.org` already points at GitHub Pages and currently
  404s, so it is free to claim — but claiming it publishes an eleven-article
  pilot at the project's real front door. Better to review on the
  `github.io` URL first.

When the pilot is approved, claiming the apex for staging is a one-line change
(add a `CNAME` file); the `www` switch stays until cutover.

---

## Then

- `pixi run test` must stay green — it is what protects the fifty registered
  DOIs.
- Fill in the ORCIDs in `authors.yml`. The validator warns about nine gaps
  across six people (Mansour, Giordani, Beucher, Knight, Lu). They are left
  null rather than guessed.
- Contact Front Matter to deactivate Rogue Scholar ingestion and confirm in
  writing that the fifty registered DOIs keep resolving. Not urgent until
  cutover, but it needs a reply on file.
