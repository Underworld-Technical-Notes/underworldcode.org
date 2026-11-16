#!/usr/bin/env python3
"""Stop a Claude session from moving the workbench out from under the others.

A PreToolUse hook on Bash (see .claude/settings.json). Several sessions share
the workbench checkout, each writing its own note; one of them running
``git checkout`` or ``git stash`` changes or hides every other session's files
at once. scripts/note.py does what those commands would otherwise be wanted
for, without touching the working tree.

It acts only when the checkout is on the workbench branch, so a checkout on
an ordinary branch -- a contributor's, or a worktree -- is left alone.
"""

import json
import re
import subprocess
import sys

# Each is (pattern on the arguments after the subcommand, what to do instead).
RULES = {
    "checkout": (r"", "it changes files other sessions are editing. "
                      "Save with `pixi run note save`; a branch never needs checking out here."),
    "switch": (r"", "the workbench stays on the workbench branch. `pixi run note save` builds branches without switching."),
    "stash": (r"^(?!\s*(list|show)\b)", "it hides every session's edits, not just yours."),
    "reset": (r"--hard|--keep|--merge|--soft|^(?!.*\s--(\s|$))\s*\S",
              "only the path form (`git reset -- <paths>`) is safe here; anything else moves the workbench or other sessions' files."),
    "restore": (r"^(?!.*--staged)|--worktree|\s-W\b", "it discards working-tree edits, which may be another session's."),
    "clean": (r"", "it deletes untracked files, which include other sessions' new notes."),
    "rebase": (r"", "the workbench's history is how `note save` knows what it has seen; rewriting it breaks that."),
    "pull": (r"", "use `pixi run note pull <branch|PR>` or `pixi run note sync`."),
    "commit": (r"(^|\s)(-a|--all|-[a-zA-Z]*a[a-zA-Z]*)(\s|$)", "`-a` commits every session's edits together. Use `pixi run note save`."),
}

GIT = re.compile(r"(?:^|[;&|(\n]|&&|\|\|)\s*git((?:\s+-[Cc]\s+\S+)*)\s+([a-z-]+)([^;&|\n]*)")


def on_workbench(cwd, options):
    target = re.search(r"-C\s+(\S+)", options or "")
    path = target.group(1).strip("'\"") if target else cwd
    head = subprocess.run(["git", "-C", path, "symbolic-ref", "-q", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    return head == "refs/heads/workbench"


def main():
    event = json.load(sys.stdin)
    command = event.get("tool_input", {}).get("command", "")
    for options, sub, rest in GIT.findall(command):
        rule = RULES.get(sub)
        if not rule or not re.search(rule[0], rest):
            continue
        if not on_workbench(event.get("cwd", "."), options):
            return
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason":
                "`git %s` is blocked in the workbench: %s See CLAUDE.md." % (sub, rule[1]),
        }}))
        return


if __name__ == "__main__":
    main()
