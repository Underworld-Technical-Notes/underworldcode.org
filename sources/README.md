# Drafted sources for the recent notes

Verbatim copy of `publications/blog-posts/` from the underworld3 worktree
`.claude/worktrees/blog-posts`, taken 2026-08-06.

**Why this is here.** These are the markdown originals the recent posts were
written from, together with the Typst sources, JSON data and generator scripts
for their figures. They matter twice over: they carry authoring intent that a
Ghost HTML render cannot (a figure is a figure, code is fenced and tagged), and
their maths is intact where Ghost's editor damaged the published copy.

**Why a copy rather than a reference.** When this was first looked for, the
copy on `development` was stale — `finding-particles.md` there shares only 34%
of its sentences with what was published, against 85% for the worktree copy.
The newer material existed solely as *uncommitted changes* in one worktree,
along with untracked figure sources (`element-location-demo.typ` and its data),
and would have been lost with that worktree. It is committed here so the
migration cannot depend on a working tree that nobody has committed.

These files are inputs to the migration, not published content. The canonical
home for future notes is `articles/`; see `CONTRIBUTING.md`.
