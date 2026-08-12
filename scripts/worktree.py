#!/usr/bin/env python3
"""Give a note being written its own working tree.

Writing a note and building the site are the same repository doing two things
at once, and they collide over generated files. ``myst.yml`` holds the toc and
both builds rewrite it: a production build run in another terminal takes notes
at draft and review out of the toc that ``myst start`` is watching, and the dev
server begins reporting "File is not in project" for the file its owner has
open. Nothing is lost and nothing is broken -- it simply stops updating, which
is worse, because it looks like the editor's fault.

The two cannot share one toc. The theme bakes the toc into every page, so a
production toc that listed drafts would put links to unbuilt pages on all of
them.

So separate the trees instead. A worktree is a second checkout of the same
repository on its own branch, with its own generated files, its own ``_build``
and its own pixi environment. Write in one, build in the other, and there is
nothing to collide over.

The branch is created for you, because the branch is what the preview site
keys on: push it and it publishes to its own hashed directory, and the pull
request gets the link.

    python3 scripts/worktree.py create particle-level-sets
    python3 scripts/worktree.py list
    python3 scripts/worktree.py remove particle-level-sets

Worktrees are made as siblings of the repository, never inside it: a checkout
nested in its own working tree is a good way to commit a copy of everything.
"""

import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TREES = ROOT.parent / ("%s-worktrees" % ROOT.name)


def run(*command, **kwargs):
    return subprocess.run(list(command), cwd=kwargs.pop("cwd", ROOT),
                          check=kwargs.pop("check", True), **kwargs)


def slugify(name):
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    if not slug:
        sys.exit("%r leaves nothing usable as a name" % name)
    return slug


def create(name, base):
    slug = slugify(name)
    branch = "note/%s" % slug
    target = TREES / slug

    if target.exists():
        sys.exit("%s already exists. `worktree.py remove %s` first, or pick "
                 "another name." % (target, slug))

    existing = subprocess.run(["git", "rev-parse", "--verify", branch],
                              cwd=ROOT, capture_output=True).returncode == 0
    TREES.mkdir(parents=True, exist_ok=True)

    # From the remote's base rather than whatever is checked out here: a
    # worktree cut from a local branch that is behind carries that lag into the
    # note, and the first sign is a merge conflict a fortnight later.
    run("git", "fetch", "--quiet", "origin", base)
    if existing:
        run("git", "worktree", "add", str(target), branch)
        print("worktree %s on existing branch %s" % (target, branch))
    else:
        run("git", "worktree", "add", "-b", branch, str(target),
            "origin/%s" % base)
        print("worktree %s on new branch %s (from origin/%s)"
              % (target, branch, base))

    # What to do next depends on whether the branch already has a note on it.
    # Telling somebody to `pixi run new` on a branch that already carries the
    # article they came to edit is worse than saying nothing: it reads as the
    # required next step, and it is not.
    existing_notes = subprocess.run(
        ["git", "diff", "--name-only", "origin/%s...%s" % (base, branch),
         "--", "articles/*/metadata.yml"],
        cwd=ROOT, capture_output=True, text=True).stdout.split()
    slugs = sorted({p.split("/")[1] for p in existing_notes if "/" in p})

    print("\nIt has its own environment -- that is the point, and installing it")
    print("takes a few minutes the first time:\n")
    print("    cd %s" % target)
    print("    pixi install")
    if slugs:
        print("    pixi run start          # then edit:")
        for found in slugs:
            print("        articles/%s/%s.md" % (found, found))
    else:
        print("    pixi run new --slug %s --title \"...\" --author louis" % slug)
        print("    pixi run start")
    print("\n`pixi run start` serves http://localhost:3000 with hot reload, and")
    print("shows notes at draft and review the way the preview site does.")
    print("Push the branch when it is worth someone else reading: the preview")
    print("link appears on the pull request.")


def listing():
    out = subprocess.run(["git", "worktree", "list", "--porcelain"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    trees = []
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if current:
                trees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line.startswith("detached"):
            current["branch"] = "(detached)"
    if current:
        trees.append(current)
    for tree in trees:
        path = pathlib.Path(tree["path"])
        marker = "  (this repository)" if path == ROOT else ""
        env = "" if (path / ".pixi").exists() else "   [no pixi env yet]"
        print("  %-42s %-28s%s%s"
              % (path.name, tree.get("branch", "?"), env, marker))
    print("%d worktree(s)" % len(trees))


def remove(name):
    slug = slugify(name)
    target = TREES / slug
    if not target.exists():
        sys.exit("no worktree at %s" % target)
    # The branch is left alone: it may be pushed, it may be under review, and
    # deleting it here would take the preview with it. Removing a working copy
    # and deleting a branch are different decisions.
    run("git", "worktree", "remove", str(target))
    print("removed %s. The branch note/%s is untouched." % (target, slug))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    made = sub.add_parser("create", help="a worktree and branch for a new note")
    made.add_argument("name")
    made.add_argument("--from", dest="base", default="main",
                      help="branch to start from (default: main)")
    sub.add_parser("list", help="every worktree, with its branch")
    gone = sub.add_parser("remove", help="a worktree, leaving its branch")
    gone.add_argument("name")
    args = parser.parse_args()

    if args.command == "create":
        create(args.name, args.base)
    elif args.command == "list":
        listing()
    else:
        remove(args.name)


if __name__ == "__main__":
    main()
