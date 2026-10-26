#!/usr/bin/env python3
"""Write every note in one checkout, and make each branch from its own files.

A branch is a line of commits; a checkout is a directory with one branch in
it. Keeping a note per branch therefore meant a checkout per note -- a
worktree each, sixteen of them by October 2026, each wanting its own editor
window. Several sessions in one checkout was worse: one of them switching
branch moved the files out from under the others.

The notes do not actually collide. Each lives in its own ``articles/<slug>/``,
and the only files they share are registers of one entry per note,
classification.yml and acknowledgements.yml. So this keeps them all in one
checkout -- the workbench, a local branch that is never pushed -- and builds
each note's branch from that note's directory without checking it out:

    pixi run note init                       # once: this checkout becomes the workbench
    pixi run note save particle-level-sets -m "First draft" --push
    pixi run note save docs/pdf-template templates/pdf -m "..."   # anything else: name the paths
    pixi run note pull 58                    # a pull request, someone else's or yours
    pixi run note sync                       # main, into the workbench
    pixi run note list                       # what is on the bench, and what it needs

``save`` commits one snapshot twice: onto the note's branch, on top of whatever
the branch already had, and into the workbench as a merge of that commit, so
the workbench's history records that the branch is in it. That is what keeps
``sync`` clean once the pull request is merged -- main brings back commits the
workbench already has -- and it is how ``save`` knows when someone else has
pushed to the branch since: their commit is not in the workbench, and the save
stops rather than overwrite it.

Nothing here checks out, stashes or resets the working tree. A save builds its
commits in a private index and then refreshes only its own paths in the shared
one, so a session saving one note cannot sweep another session's files into
its commit. The rule that goes with it, for people and sessions alike: in the
workbench, never ``git checkout``, ``switch``, ``stash``, ``reset --hard`` or
``commit -a``.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BENCH = "refs/heads/workbench"
MAIN = "refs/remotes/origin/main"
ZERO = "0" * 40

# Rewritten by `pixi run start` and by every build, so it belongs to no note.
# Put back without asking when only its generated blocks differ.
GENERATED = "myst.yml"

KEY = re.compile(r"^([a-z0-9][a-z0-9-]*):\s*$")
ITEM = re.compile(r"^- ([a-z0-9][a-z0-9-]*)\s*$")


def run(*args, env=None, stdin=None):
    for attempt in range(20):
        done = subprocess.run(["git", *args], cwd=ROOT, env=env, input=stdin,
                              capture_output=True, text=True)
        # Another session holds the shared index for a moment. The lock lasts
        # milliseconds; waiting it out is better than failing the save.
        if "index.lock" not in done.stderr:
            break
        time.sleep(0.25)
    return done


def git(*args, env=None, stdin=None):
    done = run(*args, env=env, stdin=stdin)
    if done.returncode:
        sys.exit("git %s failed:\n%s" % (" ".join(args), done.stderr.strip()))
    return done.stdout


def line(*args, **kwargs):
    return git(*args, **kwargs).strip()


def commit_of(ref):
    return run("rev-parse", "-q", "--verify", ref + "^{commit}").stdout.strip() or None


def contains(ancestor, descendant):
    return run("merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


class Stop(Exception):
    """A merge that cannot go ahead. Fatal for one pull; one line of a sync."""


def show(rev, path):
    done = run("show", "%s:%s" % (rev, path))
    return done.stdout if done.returncode == 0 else ""


class PrivateIndex:
    """An index of our own, so building a commit never touches the shared one."""

    def __enter__(self):
        handle, self.path = tempfile.mkstemp(
            prefix="note-index-", dir=line("rev-parse", "--absolute-git-dir"))
        os.close(handle)
        os.unlink(self.path)
        return dict(os.environ, GIT_INDEX_FILE=self.path)

    def __exit__(self, *exc):
        for leftover in (self.path, self.path + ".lock"):
            try:
                os.unlink(leftover)
            except FileNotFoundError:
                pass


# -- what is tracked ---------------------------------------------------------
#
# Kept in the repository's own git config, under [note "<branch>"]: tracked,
# and for a pull request its number, plus the fork it came from if it did.

def setting(branch, key):
    return run("config", "--get", "note.%s.%s" % (branch, key)).stdout.strip() or None


def remember(branch, **values):
    for key, value in values.items():
        git("config", "note.%s.%s" % (branch, key), str(value))


def forget(branch):
    run("config", "--remove-section", "note.%s" % branch)


def tracked():
    found = run("config", "--get-regexp", r"^note\..*\.tracked$").stdout
    return sorted(entry.split()[0][len("note."):-len(".tracked")]
                  for entry in found.splitlines())


def require_bench():
    head = run("symbolic-ref", "-q", "HEAD").stdout.strip()
    if head != BENCH:
        sys.exit("This checkout is on %s, not the workbench. `pixi run note init` "
                 "makes it one." % (head.replace("refs/heads/", "") or "a detached HEAD"))


def elsewhere(branch):
    """The other worktree that has this branch checked out, if one does."""
    path = None
    for entry in git("worktree", "list", "--porcelain").splitlines():
        if entry.startswith("worktree "):
            path = pathlib.Path(entry[len("worktree "):])
        elif entry == "branch refs/heads/%s" % branch and path != ROOT:
            return path
    return None


# -- naming a branch ---------------------------------------------------------

def adopt(number):
    """Look a pull request up, and track its branch under the name we use for it."""
    view = subprocess.run(
        ["gh", "pr", "view", str(number), "--json",
         "headRefName,isCrossRepository,headRepository,headRepositoryOwner,title"],
        cwd=ROOT, capture_output=True, text=True)
    if view.returncode:
        sys.exit(view.stderr.strip())
    pr = json.loads(view.stdout)
    if pr["isCrossRepository"]:
        # A contributor's fork. Their branch name can be anything, including
        # one of ours, so it is held here under the pull request's number.
        branch = "pr/%d" % number
        remember(branch, pr=number, forkbranch=pr["headRefName"],
                 fork="https://github.com/%s/%s.git"
                 % (pr["headRepositoryOwner"]["login"], pr["headRepository"]["name"]))
    else:
        branch = pr["headRefName"]
        remember(branch, pr=number)
    print("#%d %s -> %s" % (number, pr["title"], branch))
    return branch


def resolve(target):
    """A slug, a branch or a pull request number -> (branch, slug or None)."""
    number = target.lstrip("#")
    if number.isdigit():
        for branch in tracked():
            if setting(branch, "pr") == number:
                return branch, None
        return adopt(int(number)), None
    if "/" in target:
        return target, None
    return "note/%s" % target, target


def published_ref(branch):
    if setting(branch, "fork"):
        return "refs/remotes/pull/%s" % setting(branch, "pr")
    return "refs/remotes/origin/%s" % branch


def fetch(branch):
    """Bring the published tip of a branch here; None if it was never pushed."""
    if setting(branch, "fork"):
        # GitHub mirrors the head of every pull request on our side, fork or not.
        source = "refs/pull/%s/head" % setting(branch, "pr")
    else:
        source = "refs/heads/%s" % branch
    probe = run("ls-remote", "--exit-code", "origin", source)
    if probe.returncode == 2:
        return None
    if probe.returncode:
        sys.exit("cannot reach origin:\n%s" % probe.stderr.strip())
    git("fetch", "--quiet", "origin", "+%s:%s" % (source, published_ref(branch)))
    return commit_of(published_ref(branch))


# -- what a branch owns ------------------------------------------------------

def owned(tip, named):
    """The paths a branch is responsible for: what it has changed, and what is named.

    A note owns its whole directory, so a file added to it is carried without
    being named. The registers and myst.yml come only by name: a branch that
    once committed them does not thereby own everyone's entries. Nor does a
    note's branch own a file outside articles/ that it once edited --
    WRITING-PLAN.md, say: saving the note would carry the workbench's copy, with
    every other branch's edits to it, and would carry as a contribution any
    branch that edits nothing else. A branch with no article in it owns all it
    changed, having nothing else to own.
    """
    named = {path.rstrip("/") for path in named}
    paths = set(named)
    if tip:
        base = line("merge-base", MAIN, tip)
        changed = set(git("diff", "--name-only", "--no-renames", base, tip).splitlines())
        if any(path.startswith("articles/") for path in changed | paths):
            changed = {path for path in changed if path.startswith("articles/")}
        paths |= changed
    collapsed = set()
    for path in paths:
        parts = path.split("/")
        collapsed.add("/".join(parts[:2]) if parts[0] == "articles" and len(parts) > 2 else path)
    return sorted(collapsed - ((set(REGISTERS) | {GENERATED}) - named))


def edited_elsewhere(branch, paths):
    """Those of these paths outside articles/ that another tracked branch edits too.

    The workbench's copy of such a file holds both branches' edits, so saving
    it whole would hand one branch's work to the other.
    """
    outside = {path for path in paths if not path.startswith("articles/")}
    found = {}
    for other in tracked():
        tip = commit_of(published_ref(other)) or commit_of("refs/heads/%s" % other)
        if other == branch or not tip or not outside:
            continue
        base = line("merge-base", MAIN, tip)
        for path in outside & set(git("diff", "--name-only", "--no-renames", base, tip).splitlines()):
            found.setdefault(path, []).append(other)
    return found


def slugs_in(paths):
    return sorted({path.split("/")[1] for path in paths
                   if path.startswith("articles/") and path.count("/") == 1})


def entries(lines):
    """Where each top-level entry of classification.yml starts and ends, by line."""
    spans, name, start, last = {}, None, 0, 0
    for number, text in enumerate(lines):
        if text.strip() and not text[0].isspace():
            # Column 0 is a new entry, or a comment between entries: either
            # way the entry before it has ended at its last non-blank line.
            if name:
                spans[name] = (start, last + 1)
            match = KEY.match(text)
            name, start = (match.group(1), number) if match else (None, 0)
        if text.strip():
            last = number
    if name:
        spans[name] = (start, last + 1)
    return spans


def items(lines):
    """Where each `- slug` line of acknowledgements.yml is, by line."""
    return {match.group(1): (number, number + 1)
            for number, match in enumerate(map(ITEM.match, lines)) if match}


# The files every note has an entry in, and how to find the entries. A note's
# save carries its own entries and nobody else's; a merge takes each entry from
# whichever side changed it.
REGISTERS = {"classification.yml": entries, "acknowledgements.yml": items}


def splice(path, theirs, ours, slugs):
    """theirs, with the entries for these slugs as they are in ours: added, replaced or removed."""
    where = REGISTERS[path]
    result = theirs.splitlines(keepends=True)
    mine = ours.splitlines(keepends=True)
    for slug in slugs:
        have, want = where(result), where(mine)
        block = [text if text.endswith("\n") else text + "\n"
                 for text in (mine[slice(*want[slug])] if slug in want else [])]
        if slug in have:
            start, end = have[slug]
            if not block and end < len(result) and not result[end].strip():
                end += 1
            result[start:end] = block
        elif block:
            if result and not result[-1].endswith("\n"):
                result[-1] += "\n"
            if where is items and have:
                # A list: the new line goes after the last one, with no gap.
                end = max(stop for _, stop in have.values())
                result[end:end] = block
            else:
                result += (["\n"] if result else []) + block
    return "".join(result)


def blocks(path, text):
    lines = text.splitlines(keepends=True)
    return {slug: "".join(lines[slice(*span)]).rstrip()
            for slug, span in REGISTERS[path](lines).items()}


def merge_entries(path, base, ours, theirs):
    """A register merged entry by entry, each entry from whichever side changed it.

    Two notes adding their entries at the end of the file conflict as lines,
    but not as entries. None if both sides changed one entry differently, or
    theirs changed the text between entries: those want a person.
    """
    was, mine, new = (blocks(path, text) for text in (base, ours, theirs))
    moved = sorted(slug for slug in set(was) | set(new) if was.get(slug) != new.get(slug))
    if any(mine.get(slug) not in (was.get(slug), new.get(slug)) for slug in moved):
        return None
    every = sorted(set(was) | set(mine) | set(new))
    if splice(path, base, "", every) != splice(path, theirs, "", every):
        return None
    return splice(path, ours, theirs, moved)


def present(paths, env):
    """The paths git can stage: on disk, or in the index so their removal can be."""
    known = [entry for entry in git("ls-files", "-z", "--", *paths, env=env).split("\0") if entry]
    return [path for path in paths if (ROOT / path).exists()
            or any(entry == path or entry.startswith(path + "/") for entry in known)]


def dirty():
    """Every path whose working copy differs from the workbench, untracked ones included."""
    out = git("status", "--porcelain", "-z", "-uall", "--no-renames")
    return {entry[3:] for entry in out.split("\0") if entry}


def under(path, paths):
    return any(path == owner or path.startswith(owner + "/") for owner in paths)


# -- save --------------------------------------------------------------------

def contributions(branch, paths, slugs, parents):
    """Pulled branches whose work lies wholly inside this branch's paths.

    A contribution to a note often arrives on a branch of its own: figures
    from the machine that has the runs, a section from a hub session. Once it
    is merged into the workbench, the note's next save carries its commits as
    further parents, so their authorship survives and GitHub marks that pull
    request merged when the note's is. Only a branch that changes nothing
    outside the note qualifies -- anything else would be recorded as merged
    while part of it was left behind.
    """
    found = []
    for other in tracked():
        if other == branch:
            continue
        tip = commit_of(published_ref(other)) or commit_of("refs/heads/%s" % other)
        if (not tip or not contains(tip, BENCH)
                or any(contains(tip, seen) for seen in parents + [t for _, t in found])):
            continue
        base = line("merge-base", MAIN, tip)
        changed = git("diff", "--name-only", "--no-renames", base, tip).splitlines()

        def inside(path):
            if under(path, paths):
                return True
            # Its own entries in a register are inside; anyone else's are not.
            return (path in REGISTERS and bool(slugs)
                    and splice(path, show(base, path), "", slugs) == splice(path, show(tip, path), "", slugs))

        if changed and all(inside(path) for path in changed):
            found.append((other, tip))
    return found


def fork_destination(branch):
    """Where `save --push` sends a commit on a contributor's pull request.

    Their pull request comes from their fork, setting(branch, "fork"), on the
    branch setting(branch, "forkbranch"). There are two places a commit of
    ours can go:

    - straight onto their branch. GitHub allows it when they ticked "allow
      edits from maintainers"; the pull request updates at once, and they must
      pull before they write again or their next push is rejected.
    - onto a branch of ours on origin, which they can merge or not. Pushing to
      origin also gets it a preview site, which a push to a fork does not.

    Returns (remote URL, branch name on that remote).
    """
    # TODO(louis): choose.
    sys.exit("pushing to a contributor's pull request is not decided yet: see "
             "fork_destination() in scripts/note.py. The commit is saved locally on %s."
             % branch)


def save(target, named, message, push):
    require_bench()
    branch, slug = resolve(target)
    if slug:
        if not (ROOT / "articles" / slug).is_dir() and not commit_of("refs/heads/%s" % branch):
            sys.exit("there is no articles/%s here. `pixi run new` makes one." % slug)
        named = list(named) + ["articles/%s" % slug]
    if elsewhere(branch):
        sys.exit("%s is checked out in %s. Remove that worktree first; the branch "
                 "is not touched by removing it." % (branch, elsewhere(branch)))

    git("fetch", "--quiet", "origin", "+refs/heads/main:%s" % MAIN)
    published = fetch(branch)
    local = commit_of("refs/heads/%s" % branch)
    # Anything on the branch that the workbench has not seen would be
    # overwritten by the save, which carries the workbench's copy of every path
    # the branch owns. Merge it in first; that is what pull is for.
    for tip, where in ((published, "on origin"), (local, "here")):
        if tip and not contains(tip, BENCH):
            sys.exit("%s has commits %s that the workbench has not seen. "
                     "`pixi run note pull %s` first, so they are merged rather than "
                     "overwritten." % (branch, where, target))

    for attempt in range(5):
        local = commit_of("refs/heads/%s" % branch)
        if published and local:
            if contains(published, local):
                parents = [local]
            elif contains(local, published):
                parents = [published]
            else:
                parents = [published, local]
        else:
            # A new branch starts from the newest main the workbench has, not
            # the newest there is: the workbench has to contain every parent
            # of what it merges, or a later sync would think main was in it.
            parents = [published or local or line("merge-base", BENCH, MAIN)]
        paths = owned(parents[0], named)
        # Named outright, a file goes whole: whoever names it has looked.
        shared = {path: others for path, others in edited_elsewhere(branch, paths).items()
                  if path not in {name.rstrip("/") for name in named}}
        paths = [path for path in paths if path not in shared]
        if not paths and shared:
            sys.exit("Nothing saved: every file %s changes is edited by another branch too:\n%s\n"
                     "Name the ones to save the workbench's copy of, whole: "
                     "`pixi run note save %s <path> ...`"
                     % (branch, "\n".join("  %s (%s)" % (path, ", ".join(others))
                                          for path, others in sorted(shared.items())), target))
        if not paths:
            sys.exit("%s owns nothing yet. Name what it is for: "
                     "`pixi run note save %s <path> ...`" % (branch, target))
        slugs = slugs_in(paths)
        # A register named outright goes whole; otherwise just these notes' entries.
        spliced = [path for path in REGISTERS if path not in paths] if slugs else []
        snapshot = paths + spliced
        carried = contributions(branch, paths, slugs, parents)
        parents += [tip for _, tip in carried]

        head = commit_of(BENCH)
        with PrivateIndex() as env:
            git("read-tree", head, env=env)
            staged = present(snapshot, env)
            if staged:
                git("add", "-A", "--", *staged, env=env)
            bench_tree = line("write-tree", env=env)

        with PrivateIndex() as env:
            git("read-tree", parents[0], env=env)
            stale = git("ls-files", "-z", "--", *paths, env=env)
            if stale:
                git("update-index", "--force-remove", "-z", "--stdin", env=env, stdin=stale)
            fresh = git("ls-tree", "-r", "-z", "--full-tree", bench_tree, *paths)
            if fresh:
                git("update-index", "-z", "--index-info", env=env, stdin=fresh)
            for path in spliced:
                theirs = show(parents[0], path)
                text = splice(path, theirs, show(bench_tree, path), slugs)
                if text != theirs:
                    blob = line("hash-object", "-w", "--stdin", stdin=text)
                    git("update-index", "--add", "--cacheinfo",
                        "100644,%s,%s" % (blob, path), env=env)
            branch_tree = line("write-tree", env=env)

        if len(parents) == 1 and branch_tree == line("rev-parse", parents[0] + "^{tree}"):
            tip = parents[0]
        else:
            tip = line("commit-tree", branch_tree,
                       *[flag for parent in parents for flag in ("-p", parent)], "-m", message)
        merge = [] if contains(tip, head) else ["-p", tip]
        if not merge and bench_tree == line("rev-parse", head + "^{tree}"):
            new_head = head
        else:
            new_head = line("commit-tree", bench_tree, "-p", head, *merge,
                            "-m", "%s: %s" % (branch, message))

        if tip != local:
            git("update-ref", "-m", "note save", "refs/heads/%s" % branch, tip, local or ZERO)
        if new_head == head or run("update-ref", "-m", "note save: %s" % branch,
                                   BENCH, new_head, head).returncode == 0:
            break
        # Another session saved in between. Build again on top of theirs; the
        # branch already has this commit, so only the workbench's half repeats.
    else:
        sys.exit("the workbench kept moving under this save; run it again")

    # The workbench now has these paths as they are on disk. Say so in the
    # shared index too, for these paths only, or they would show as staged
    # changes back to what they were.
    git("reset", "-q", "--pathspec-from-file=-", "--pathspec-file-nul",
        stdin="\0".join(snapshot) + "\0")

    remember(branch, tracked="true")
    for path, others in sorted(shared.items()):
        print("left %s as it was on %s: %s edit%s it too. Name it to save the "
              "workbench's copy whole." % (path, branch, " and ".join(others),
                                           "s" if len(others) == 1 else ""))
    for other, _ in carried:
        remember(other, carriedby=branch)
        print("carries %s: its pull request closes as merged when %s's does" % (other, branch))
    if tip == parents[0] and len(parents) == 1:
        print("%s already has this; nothing new to commit." % branch)
    else:
        print("%s  %s  %s" % (branch, tip[:8], message))
        print(git("diff", "--stat", parents[0], tip).rstrip())

    if push:
        if setting(branch, "fork"):
            url, ref = fork_destination(branch)
        else:
            url, ref = "origin", branch
        git("push", "--quiet", url, "%s:refs/heads/%s" % (tip, ref))
        if url == "origin":
            git("update-ref", published_ref(branch), tip)
        print("pushed to %s %s" % (url, ref))
        if not setting(branch, "pr") and url == "origin":
            print("No pull request yet: gh pr create --head %s" % ref)


# -- pull and sync -----------------------------------------------------------

def put_back_generated(paths):
    """Restore myst.yml if the only edits to it are its generated blocks."""
    if GENERATED not in paths:
        return
    def bare(text):
        return re.sub(r"# BEGIN GENERATED (\w+).*?# END GENERATED \1", "", text, flags=re.S)
    current = (ROOT / GENERATED).read_text(encoding="utf-8")
    committed = show(BENCH, GENERATED)
    if current != committed and bare(current) == bare(committed):
        (ROOT / GENERATED).write_text(committed, encoding="utf-8")
        print("myst.yml: put its committed contents list back so the merge can "
              "proceed. `pixi run start` regenerates it.")


def checkpoint(paths, message):
    """Commit these paths, as they are on disk, to the workbench alone."""
    for attempt in range(5):
        head = commit_of(BENCH)
        with PrivateIndex() as env:
            git("read-tree", head, env=env)
            staged = present(paths, env)
            if staged:
                # Never without paths: a bare `add -A` would take everyone's files.
                git("add", "-A", "--", *staged, env=env)
            tree = line("write-tree", env=env)
        if tree == line("rev-parse", head + "^{tree}"):
            return
        new_head = line("commit-tree", tree, "-p", head, "-m", "workbench: %s" % message)
        if run("update-ref", "-m", message, BENCH, new_head, head).returncode == 0:
            git("reset", "-q", "--pathspec-from-file=-", "--pathspec-file-nul",
                stdin="\0".join(paths) + "\0")
            return
    sys.exit("the workbench kept moving under this checkpoint; run it again")


def settle(tree, head, tip, conflicted):
    """The merged tree with each conflicted register merged entry by entry, or None."""
    base = line("merge-base", head, tip)
    with PrivateIndex() as env:
        git("read-tree", tree, env=env)
        for path in conflicted:
            text = merge_entries(path, show(base, path), show(head, path), show(tip, path))
            if text is None:
                return None
            blob = line("hash-object", "-w", "--stdin", stdin=text)
            git("update-index", "--cacheinfo", "100644,%s,%s" % (blob, path), env=env)
        return line("write-tree", env=env)


def trial_merge(tip, label):
    """(workbench, merged tree, paths the merge changes), without touching a file."""
    head = commit_of(BENCH)
    trial = run("merge-tree", "--write-tree", "--name-only", "--no-messages", head, tip)
    if trial.returncode > 1:
        sys.exit(trial.stderr.strip())
    merged, *conflicted = [path for path in trial.stdout.splitlines() if path]
    if conflicted:
        merged = all(path in REGISTERS for path in conflicted) and settle(merged, head, tip, conflicted)
    if not merged:
        raise Stop("%s conflicts with the workbench in:\n  %s\nNothing in the working "
                   "tree was changed. To resolve it by hand, as an ordinary merge:\n"
                   "  git merge %s     # fix the files, then git commit\n"
                   "and nobody else may save while it is half done."
                   % (label, "\n  ".join(conflicted), tip[:12]))
    touched = set(git("diff", "--name-only", "--no-renames", "-z", head, merged).split("\0")) - {""}
    return head, merged, touched


def absorb(tip, label):
    """Merge a commit into the workbench, or stop before touching anything.

    Unsaved edits in files the merge changes are committed to the workbench
    first -- not to any branch -- so that git merges them three ways rather
    than refusing. Without that, a branch somebody else pushed to while you
    were editing it could be neither saved (it has commits you have not seen)
    nor pulled (you have edits it would overwrite).
    """
    if contains(tip, BENCH):
        return False
    head, merged, touched = trial_merge(tip, label)
    put_back_generated(touched)
    blocked = sorted(touched & dirty())
    if blocked:
        checkpoint(blocked, "before %s" % label)
        head, merged, touched = trial_merge(tip, label)
        put_back_generated(touched)
        still = sorted(touched & dirty())
        if still:
            raise Stop("%s would overwrite edits made while it ran:\n  %s"
                       % (label, "\n  ".join(still)))
    # The commit is built from the trial's tree, since `git merge` would stop at
    # the register conflicts settle() has already resolved. read-tree then
    # writes just the files the merge changes, and refuses, writing none, if
    # one of them has edits or an untracked file is in the way.
    commit = line("commit-tree", merged, "-p", head, "-p", tip, "-m", "workbench: %s" % label)
    written = run("read-tree", "-m", "-u", head, commit)
    if written.returncode:
        raise Stop("%s: %s" % (label, written.stderr.strip()))
    if run("update-ref", "-m", "workbench: %s" % label, BENCH, commit, head).returncode:
        # Another session saved in between. Put the files back; the next run merges onto theirs.
        run("read-tree", "-m", "-u", commit, head)
        raise Stop("%s: the workbench moved while it ran; run it again" % label)
    return True


def pull(target):
    require_bench()
    branch, _ = resolve(target)
    published = fetch(branch)
    local = commit_of("refs/heads/%s" % branch)
    if not (published or local):
        sys.exit("no branch %s here or on origin" % branch)
    took = False
    # A branch from the worktree days can have local commits it never pushed.
    # Those are the note too, so they come in alongside the published ones.
    for tip in [published] + ([local] if local and local != published else []):
        if tip:
            try:
                took = absorb(tip, "pull %s" % branch) or took
            except Stop as stop:
                sys.exit(str(stop))
    # Keep the local branch at the published tip, so the next save builds on it.
    if published and not elsewhere(branch) and (not local or contains(local, published)):
        git("update-ref", "refs/heads/%s" % branch, published, local or ZERO)
    remember(branch, tracked="true")
    print("%s: %s" % (branch, "merged into the workbench" if took else "the workbench already has it"))


def pull_requests():
    view = subprocess.run(
        ["gh", "pr", "list", "--state", "all", "--limit", "200", "--json",
         "number,state,headRefName,isCrossRepository,title,author"],
        cwd=ROOT, capture_output=True, text=True)
    if view.returncode:
        return {}
    found = {}
    for pr in json.loads(view.stdout):
        branch = "pr/%d" % pr["number"] if pr["isCrossRepository"] else pr["headRefName"]
        found.setdefault(branch, pr)
    return found


def unclaimed(prs):
    """Open pull requests, other than the deposit robot's, that nothing here tracks."""
    mine = set(tracked())
    return [(branch, pr) for branch, pr in sorted(prs.items(), key=lambda item: item[1]["number"])
            if pr["state"] == "OPEN" and branch not in mine
            and not pr.get("author", {}).get("login", "").startswith("app/")]


def sync():
    """Gather everything: main, and whatever has been pushed to a tracked branch.

    Notes are started wherever the runs are -- a hub session with the data
    makes the skeleton and the figures -- and finished somewhere else, so the
    workbench is where the pieces meet. A conflict on one branch is reported
    and the rest carry on.
    """
    require_bench()
    git("fetch", "--quiet", "--prune", "origin")
    try:
        print("main: %s" % ("merged into the workbench" if absorb(commit_of(MAIN), "sync with main")
                            else "the workbench already has it"))
    except Stop as stop:
        print("main: %s" % stop)
    prs = pull_requests()
    for branch in tracked():
        pr = prs.get(branch)
        if pr and pr["state"] == "MERGED":
            forget(branch)
            print("%s: merged in #%d, no longer tracked. The branch itself is "
                  "untouched." % (branch, pr["number"]))
            continue
        if pr and pr["state"] == "CLOSED":
            print("%s: #%d was closed without merging. `pixi run note drop %s` "
                  "if it is finished with." % (branch, pr["number"], branch))
            continue
        published = fetch(branch) if setting(branch, "fork") else commit_of(published_ref(branch))
        if published and not contains(published, BENCH):
            try:
                absorb(published, "pull %s" % branch)
                print("%s: new commits merged into the workbench" % branch)
            except Stop as stop:
                print("%s: %s" % (branch, stop))
    waiting = unclaimed(prs)
    if waiting:
        print("\nOpen, and not on the bench (`pixi run note pull <number>`):")
        for branch, pr in waiting:
            print("  #%-4d %-40s %s" % (pr["number"], branch, pr["title"]))


# -- list, init, drop --------------------------------------------------------

def listing():
    require_bench()
    git("fetch", "--quiet", "--prune", "origin")
    changed = dirty()
    prs = pull_requests()
    claimed = []
    for branch in tracked():
        if setting(branch, "fork"):
            fetch(branch)
        published = commit_of(published_ref(branch))
        local = commit_of("refs/heads/%s" % branch)
        paths = owned(local or published, [])
        claimed += paths
        state = []
        if (local or published) and contains(local or published, MAIN):
            state.append("all in main: `pixi run note sync` stops tracking it")
        if any(under(path, paths) for path in changed):
            state.append("unsaved edits")
        if published and not contains(published, BENCH):
            state.append("pushed to since you pulled: pull")
        if local and local != published and (not published or contains(published, local)):
            state.append("saved, not pushed")
        if setting(branch, "carriedby"):
            state.append("carried by %s" % setting(branch, "carriedby"))
        pr = prs.get(branch)
        print("  %-44s %-14s %s" % (branch, "#%d %s" % (pr["number"], pr["state"].lower()) if pr else "no PR",
                                     ", ".join(state) or "in step"))
    loose = sorted({"/".join(path.split("/")[:2]) if path.startswith("articles/") else path
                    for path in changed if not under(path, claimed) and path != GENERATED})
    if loose:
        print("\nEdited, but on no branch yet:")
        for path in loose:
            print("  %s" % path)
    waiting = unclaimed(prs)
    if waiting:
        print("\nOpen, and not on the bench (`pixi run note pull <number>`):")
        for branch, pr in waiting:
            print("  #%-4d %-40s %s" % (pr["number"], branch, pr["title"]))


def init():
    head = run("symbolic-ref", "-q", "HEAD").stdout.strip()
    if head == BENCH:
        print("This checkout is already the workbench.")
        return
    if commit_of(BENCH):
        sys.exit("A workbench branch exists, but this checkout is on %s. Switch to "
                 "it when nothing here is unsaved." % head.replace("refs/heads/", ""))
    # Same commit, so no file changes: whatever was being edited stays put.
    git("switch", "-q", "-c", "workbench")
    if head.startswith("refs/heads/") and head != "refs/heads/main":
        remember(head[len("refs/heads/"):], tracked="true")
    print("This checkout is now the workbench (it was on %s)." % head.replace("refs/heads/", ""))


def drop(target):
    branch, _ = resolve(target)
    forget(branch)
    print("%s is no longer tracked. Its files and the branch are untouched." % branch)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="make this checkout the workbench")
    saving = sub.add_parser("save", help="commit a note, or named paths, onto its branch")
    saving.add_argument("target", help="a slug, a branch, or a pull request number")
    saving.add_argument("paths", nargs="*", help="further paths the branch owns")
    saving.add_argument("-m", "--message", required=True)
    saving.add_argument("--push", action="store_true")
    pulling = sub.add_parser("pull", help="merge a branch or pull request into the workbench")
    pulling.add_argument("target")
    sub.add_parser("sync", help="merge main into the workbench")
    sub.add_parser("list", help="what is tracked, and what each needs")
    dropping = sub.add_parser("drop", help="stop tracking a branch")
    dropping.add_argument("target")
    args = parser.parse_args()

    if args.command == "init":
        init()
    elif args.command == "save":
        save(args.target, args.paths, args.message, args.push)
    elif args.command == "pull":
        pull(args.target)
    elif args.command == "sync":
        sync()
    elif args.command == "list":
        listing()
    else:
        drop(args.target)


if __name__ == "__main__":
    main()
