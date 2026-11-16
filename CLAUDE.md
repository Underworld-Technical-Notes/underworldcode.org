# Working in this repository

## The workbench

This checkout may be the workbench: the local branch `workbench`, holding every
note in progress side by side, with several sessions writing in it at once.
`git branch --show-current` says whether it is. CONTRIBUTING.md has the whole
workflow; on the workbench:

- Work in your own note's directory, `articles/<slug>/`, and its entry in
  `classification.yml`. The other directories are other sessions' work.
- Commit with `pixi run note save <slug> -m "..."`, adding `--push` to publish
  the branch. Anything outside a note: `pixi run note save <branch> <paths...> -m "..."`.
- Bring in a pull request with `pixi run note pull <number>`, and main with
  `pixi run note sync`. `pixi run note list` says what each branch needs.
- Never `git checkout`, `switch`, `stash`, `reset` (except `-- <paths>`),
  `restore`, `clean`, `rebase`, `pull` or `commit -a`. Each changes or hides
  every session's files; a hook refuses them.
- Do not run `pixi run build`: it rewrites the `myst.yml` contents list that
  `pixi run start` is serving.

## Anywhere else: a hub session, another machine

A checkout that is not the workbench is an ordinary one, and contributes by
branch and pull request on this repository:

- A note's branch is `note/<slug>`. If it exists on origin, work on it and push
  to it; otherwise branch from `origin/main`. Its pull request is the note's.
- Work for someone else to fold into a note — figures from the runs, a draft
  section — may go on a branch of its own instead, changing only
  `articles/<slug>/` and the note's entry in `classification.yml`. The
  workbench carries such a branch into the note with its commits intact.
- Figures ship with the script that made them, in the note's `figures/src/`.
- Push and open a pull request. Never push to `main`.
