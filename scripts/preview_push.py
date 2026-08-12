#!/usr/bin/env python3
"""Push the site you already built straight to the preview host.

The workflow route is: push a branch, a runner starts, restores the
environment, builds the whole site and every PDF, publishes, and waits for
GitHub to deploy. Two and a half minutes, most of it repeating a build you have
already done locally while writing.

This does the other thing. You have `_build/html` on disk; it goes to the
preview repository directly.

    pixi run preview

    build the changed note's PDF and the site   ~40s, or 0 if it is current
    mark it: noindex, banner, no Giscus         instant
    push _build/html into <hash>/ on gh-pages   ~5s
    GitHub's own pages deployment               ~60s, and unavoidable

That last minute is the floor for GitHub Pages from a branch, and it is the
same whether a workflow pushed or you did. Everything above it is what this
removes.

The hashed directory is the same one the workflow uses, derived from the branch
name -- so a link works whether the preview was pushed from here or built in
CI, and pushing from here updates a link already sitting on a pull request.

Authentication is yours: you have write access to the preview repository, so
there is no token to configure. The workflow needs PREVIEW_TOKEN because a
runner is nobody.

Usage:
    python3 scripts/preview_push.py            # build if needed, then push
    python3 scripts/preview_push.py --no-build # push _build/html as it stands
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

PREVIEW_REPO = "Underworld-Technical-Notes/underworldcode.org-preview"
PREVIEW_HOST = "https://underworld-technical-notes.github.io/underworldcode.org-preview"


def run(*command, **kwargs):
    return subprocess.run(list(command), check=kwargs.pop("check", True),
                          cwd=kwargs.pop("cwd", ROOT), **kwargs)


def branch_name():
    out = run("git", "rev-parse", "--abbrev-ref", "HEAD",
              capture_output=True, text=True).stdout.strip()
    if out in ("main", "HEAD"):
        sys.exit("on %s. A preview is for a branch -- `pixi run worktree create "
                 "<name>` if you have not made one." % out)
    return out


def changed_notes(branch):
    """Notes this branch touches, so only their PDFs get built."""
    run("git", "fetch", "--quiet", "origin", "main", check=False)
    out = run("git", "diff", "--name-only", "origin/main...HEAD", "--",
              "articles", capture_output=True, text=True, check=False).stdout
    return sorted({line.split("/")[1] for line in out.split()
                   if line.startswith("articles/") and "/" in line[9:]})


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-build", action="store_true",
                        help="push _build/html as it stands")
    parser.add_argument("--whole-site", action="store_true",
                        help="build every page, not just the notes under review")
    args = parser.parse_args()

    import preview_mark
    branch = branch_name()
    digest = preview_mark.preview_path(branch)
    url = "%s/%s/" % (PREVIEW_HOST, digest)
    notes = changed_notes(branch)
    commit = run("git", "rev-parse", "HEAD",
                 capture_output=True, text=True).stdout.strip()

    if not args.no_build:
        print("building %s (%s)" % (branch, ", ".join(notes) if notes
                                    else "no article changed"))
        import preview_build
        if not preview_build.build(
                notes, "/underworldcode.org-preview/%s" % digest,
                whole_site=args.whole_site):
            sys.exit("the build failed; nothing pushed")

    build = ROOT / "_build" / "html"
    if not (build / "index.html").exists():
        sys.exit("no site at %s -- drop --no-build" % build)

    # Marked here rather than trusted from the build: a preview that reached the
    # host without noindex would be a draft a search engine could find.
    run(sys.executable, "scripts/preview_mark.py",
        "--branch", branch, "--commit", commit)

    with tempfile.TemporaryDirectory() as tmp:
        clone = pathlib.Path(tmp) / "preview"
        print("\npushing to %s" % PREVIEW_REPO)
        run("git", "clone", "--quiet", "--depth", "1", "--branch", "gh-pages",
            "https://github.com/%s.git" % PREVIEW_REPO, str(clone), cwd=ROOT)

        target = clone / digest
        # Replaced wholesale: a file deleted from the site should disappear from
        # the preview too, and only THIS branch's directory is touched, so every
        # other preview survives.
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(build, target)

        run("git", "add", "-A", cwd=clone)
        staged = run("git", "status", "--porcelain", cwd=clone,
                     capture_output=True, text=True).stdout.strip()
        if not staged:
            print("nothing changed; the preview is already current")
        else:
            run("git", "-c", "user.name=underworld-technical-notes",
                "-c", "user.email=help@underworldcode.org",
                "commit", "--quiet", "-m",
                "preview: %s at %s" % (branch, commit[:7]), cwd=clone)
            run("git", "push", "--quiet", "origin", "gh-pages", cwd=clone)
            print("pushed")

    print("\n  %s" % url)
    for slug in notes:
        print("  %s%s/" % (url, slug))
    print("\nGitHub takes about a minute to deploy a push to gh-pages. Until it")
    print("has, that link serves the previous build -- the banner names the")
    print("commit, so you can tell which one you are looking at.")


if __name__ == "__main__":
    main()
