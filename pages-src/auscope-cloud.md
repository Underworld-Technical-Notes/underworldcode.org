**The AuScope / Underworld Cloud has been retired.** It was a computing platform
we ran ourselves — Kubernetes for large classes, DigitalOcean droplets for small
ones — to launch containers that pulled notebooks from a public git repository.
It did its job, and it is no longer the best way to do that job. Running our own
servers is a cost the project no longer needs to carry.

**[mybinder.org](https://mybinder.org) does this now**, and it does something the
old cloud could not: it will launch **any released version** of Underworld, so a
notebook that was written against a particular version can still be run against
that version years later.

## Launch Underworld

| Version | Launch |
|---------|--------|
| Stable (`main`) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/underworldcode/uw3-binder-launcher/main) |
| Latest (`development`) | [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/underworldcode/uw3-binder-launcher/development) |
| A specific release | `https://mybinder.org/v2/gh/underworldcode/uw3-binder-launcher/<version>` |

Released versions currently available as launchers: `v0.99`, `v3.0.0`, `v3.0.1`,
`v3.1.0`. Each is frozen against the container image built for that release, so
what you get is what that release actually was.

Either badge opens JupyterLab with the Underworld tutorials, with nothing to
install.

## Launch your own notebooks

This is the part worth knowing about. You can launch

**any public repository × any folder or notebook inside it × any released
version of Underworld**

and those three choices are independent. Your repository needs **nothing added
to it** — no `Dockerfile`, no `.binder/` directory, no configuration of any
kind. The environment comes from the launcher; the notebooks come from you.
[nbgitpuller](https://nbgitpuller.readthedocs.io/) clones your repository into
the running session, and pulls it fresh on every launch, so a correction you
push is live for the next person who clicks.

That is what the old cloud was built to do, and this does it without anybody
running a server.

The URL says which Underworld to use, which repository to fetch, and where to
open. In plain form:

```
https://mybinder.org/v2/gh/underworldcode/uw3-binder-launcher/VERSION
    ?urlpath=git-pull
     &repo=https://github.com/USER/REPO
     &branch=BRANCH
     &urlpath=lab/tree/REPO/WHERE
```

That is the shape to think in. The real URL is the same thing with the
characters escaped — it is a URL nested inside a URL, so every `?`, `&` and
`/` after `git-pull` has to be encoded, and the repository address, being one
level deeper again, is encoded twice. Nobody should do that by hand, and the
[wizard](#generating-the-link) below does it for you.

`WHERE` is what makes it land somewhere useful:

| To open | `<where>` |
|---------|-----------|
| The repository root | `<repo-name>` |
| A folder | `<repo-name>/tutorials` |
| One notebook | `<repo-name>/tutorials/intro.ipynb` |

So a course can hand out one link per practical, each opening its own folder,
all against the same pinned release.

### Generating the link

There is a script in the Underworld repository that writes the encoded URL for
you:

```bash
python scripts/binder_wizard.py                     # interactive
python scripts/binder_wizard.py myuser/my-course main tutorials/intro.ipynb
```

It emits a ready-to-paste launch badge in Markdown, HTML or reStructuredText —
which is how you put a **Launch** button on your own course or paper
repository.

Your repository needs only to be public, with notebooks using the `python3`
kernel, and to `import underworld3 as uw`.

## How the versions stay available

Nothing here is maintained by hand, which is why it can be relied on.

When Underworld is released, a GitHub Actions workflow builds a container image
for that release and pushes it to the GitHub Container Registry. It then tells
the launcher repository to create a branch pinned to that image. The launcher
branch and the release are made together, so the pairing cannot drift.

- Image build: [`.github/workflows/binder-image.yml`](https://github.com/underworldcode/underworld3/blob/development/.github/workflows/binder-image.yml)
- Launcher: [underworldcode/uw3-binder-launcher](https://github.com/underworldcode/uw3-binder-launcher)

## What mybinder.org will and will not do

Worth saying plainly, because it is the difference from the old cloud:

- **No home directory.** Sessions are ephemeral. Anything you want to keep, push
  to git or download before you close the tab. The old cloud kept a home
  directory; this does not, and that is the trade for not running servers.
- **A free, shared service.** Start-up can be slow when it is busy, and there
  are memory and CPU limits. It is for teaching, demonstrating and trying
  things, not for production runs.
- **Public repositories only**, since there is nowhere to put a credential.

For anything beyond that, install Underworld locally or run it on a cluster —
see [Introduction to Underworld](/intro-to-underworld/).

---

*The AuScope / Underworld Cloud was an AuScope project, supported by the
Australian Government through the National Collaborative Research
Infrastructure Strategy (NCRIS). It ran for several years and taught a lot of
people; the capability it pioneered is what this page now describes. The
Underworld project continues to be supported by AuScope and NCRIS. Source
code:* [*github.com/underworldcode/underworld3*](https://github.com/underworldcode/underworld3)
