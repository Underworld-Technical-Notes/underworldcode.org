---
title: A Transcript for Every Run
description: >-
  A model in Underworld3 is a Python program, so there is no model document to
  keep; every run keeps a transcript instead. What the record holds, why it is
  laid out the way it is — one line per step, the operators in the order they
  ran, how each solve went, notes only where something changed — and the chart,
  figure and key that make it readable: the residual each solver assembled, set
  as an equation, with the quantities in it under the names the script gave
  them — and the query object that asks the record the questions a debugging
  session always asks, the same questions a language model can ask it.
date: 2026-09-15
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
license: CC-BY-4.0
keywords:
  - Underworld Code
  - Tricks of the Trade
  - reproducibility
exports:
  - format: typst
    logo: ../../static/uwtn-logo.png
    series: "Underworld Technical Notes"
    origin_url: https://www.underworldcode.org/run-transcripts/
    template: ../../templates/pdf
    output: run-transcripts.pdf
    article_id: UWTN 2026-019
    article_version: 1.0.0
    software_version: underworld3 development @ a8890101
---
<!--
REVIEW 2026-11-17 (notes workbench). Checked against underworld3 development
ee9989fc. The transcript landed in #716 (1b4f3b57, 2026-09-24); the query
object, describe, the class view and MCP in #790 (1391e4aa, 2026-09-28).
Changes since that bear on the note: #744 (f414da63: the header prints the
declared reference quantities; adjoint notes and columns), #845 (05d84a02:
snapshots keep each solver's warm-start state, so a solve after a restore can
differ from the never-restored run within solver tolerance; docs/advanced/
snapshot-restore.md), #1076 (ThinSheet projections in the log, not the chart).

Fixed in the prose today, from the code:
- the run directory holds no figure (transcript_figure / transcript_diagram
  draw one from the record afterwards);
- a transcript is written by a run that takes its steps in model.step()
  blocks (a bare loop of solves writes none), shown in a code block;
- t and dt carry the unit of the run's clock;
- the "!!" line prints the record's name (SNES_Stokes(v)) and |F| as .3g;
  the log, chart and figure share the user's names, uw.Transcript and the MCP
  tools use the class names, so "every view" was narrowed;
- snapshots are in memory only, the last record_limit (8) kept; the
  on-disk record has none; uw.read_transcript(path) reads the record back;
- a rewind's reason and numbers are in the record (and backtracks(), the MCP
  problems tool); the log's note does not print them;
- transcript_key has its own renderer, not describe's; patterns() uses the
  chart's rule but is separate code; capped() covers forward solves;
- the figure's equations use matplotlib mathtext when installed.

Rerun 2026-11-17 on development a8890101 (transcript code identical to
ee9989fc), serial, wombat scratch build, 41 s: figures/src/annulus_convection.py
(moved from examples/, now closes the record before rendering, so the
figures read "complete"; writes replay_check.txt). From that one run: the
directory listing, the log and chart excerpts, the chart paragraph's numbers
(dt 0.28 -> 5.96 Myr, 732 Myr rejected, 17 step records -> 5 rows + 2 notes),
both alt texts, the replay timing (0.19 s vs 0.09 s; a restore discards
preconditioner set-up, docs/advanced/snapshot-restore.md), and the pin.
The key's Stokes values are unchanged (0.9712, 1e22, 0).
Measured: the replayed step 13 is bit-identical to its first take, AND two
independent serial runs are bit-identical after step 13 (max |dT| = 0), so
"Restoring is exact where re-running is not ... diverge at 1e-13" was false
here; the paragraph now claims only the restore. Parallel not measured.

Open, for Louis:
- On the rotated free-slip path (this note's own run) the fall back to GAMG
  is a print, "[rotated_bc] WARNING ..." (rotated_bc.py:2472, since bccad29e,
  2026-10-17), not a Python warning, so the transcript does not record it.
  The "~~" example (solvers.py:2910's RuntimeWarning) is the unrotated path's
  and is still right. A library fix, not a prose one.
- metadata subjects/methods are empty; the vocabulary has no provenance or
  reproducibility facet.
- The PDF build (preview checked 2026-11-17, ../underworld-technical-notes-build)
  prints the figures' solve marks as "?" boxes: transcript_figure's SVG sets
  them as emoji text (transcript_report.py:45, :776; by design, the PDF
  writer strokes them), and typst's SVG renderer has no emoji font. A MyST
  wildcard (figures/x.*) still hands typst the SVG. Fix in the library (stroke
  the marks in SVG too, then rerun, 41 s) or ship PNGs for print. Emoji also
  vary by browser and platform on the web. The chart-and-key figure is set at
  70% width so it fits one page (it was clipped at full width).

Not checked at runtime: the 13 bytes per DOF, the MCP server (the `mcp`
package is not in pixi.toml).
-->
Six months after a result, the questions are always the same: which version of
the code produced it, what the parameters were, and whether the run did what
the caption says it did. Underworld 1 could answer all three from one file.
Underworld3 could answer none of them until recently, and the reason is worth
a paragraph, because it is a consequence of what makes the current code usable
at all.

## Why a Python model has no document to keep

A model in Underworld 1 was an XML document. The launcher read it, StGermain
assembled the components it named, and the run followed. Provenance came for
free: the XML *was* the model, so keeping it kept everything. The cost was that
the XML was a programming language without being one — no expressions worth
the name, no control flow, no debugger — and anything the schema had not
anticipated needed C.

A model in Underworld3 is a Python program. The library takes SymPy
expressions for constitutive behaviour, boundary conditions and sources, it
puts no constraint on what happens between solves, and the timestep loop is
written by the user. That openness is what makes the library drivable by a
colleague who has never used it, or by a language model: the surface is
compositional, so a reader can predict what a call does from what the pieces
mean. It also means no serialisable model document exists, even in principle.
The model is a program, and what it did is a sequence of calls whose arguments
depended on runtime state.

So we keep a record of what the run *did*. The rest of this note is about
what that record looks like, because a record nobody can read is a record
nobody checks.

## What a run leaves

A script says where its steps are, by taking each one inside a step block:

```python
with model.step(dt, label="convect"):
    adv.solve(timestep=dt)
    stokes.solve()
```

Every run that takes a step this way writes a transcript. There is nothing to
configure, a run that takes no step writes nothing, and a run under `pytest`
writes nothing, so the default costs nothing where it would only be noise.

```
transcripts/2026-11-17T13-55-26-annulus_convection/
    annulus_convection.py    the script that launched it, verbatim
    launch.json              argv, interpreter, cwd, version, commit
    transcript.log           one aligned line per step — for watching
    transcript.jsonl         one JSON object per step — for reading back
transcripts/latest -> 2026-11-17T13-55-26-annulus_convection
```

The directory is stamped, so this morning's run is still there this afternoon;
`latest` points at the newest; the path is announced when the run ends. The
script is copied because a run's own launch line is the first thing a reader
wants and the first thing that is gone.

## One line per step, aligned, flushed

The text log is written to be watched. Each step is one line, appended and
flushed as the step closes, so `tail -f` follows a running job and a job that
is killed keeps every step it finished.

```
# underworld3 run transcript · annulus_convection · started 2026-11-17T13:55:26+11:00
# scales: shell_thickness 2200 km | thermal_diffusivity 1e-06 m ** 2/s | mantle_viscosity 1e+22 Pa s | temperature_contrast 2500 K
  -- solves: AdvDiffusion(T)  [F0, F1]  (the form is in the record; uw.transcript_key renders it)
  -- solves: Stokes(v)  [F0, F1, PF0]  (the form is in the record; uw.transcript_key renders it)
# step           t/Myr          dt/Myr    wall/s  outcome    operators, in order
      0        0.278826        0.278826      1.59  ok         [convect] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
      1        0.757079        0.478253      0.09  ok         [convect] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
     ...
     11         11.1497         2.27551      0.09  ok         [convect] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
     12         14.5488         3.39904      0.09  ok         [convect] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
     13         20.5101         5.96132      0.09  ok         [convect] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
     14         752.995         732.485      0.10  ABANDONED  [too big] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
  -- restore from a snapshot; the clock now reads 20.5101 Myr
  -- rewind to the start of step 13 (t = 14.5488 Myr); 1 step(s) undone
     13         20.5101         5.96132      0.19  ok         [replay] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
     14         35.1598         14.6497      0.17  ok         [taken twice] AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v) > AdvDiffusion(T) > shift EulerianSUPG(T) > Stokes(v)
# run ended after 15 recorded step(s) · 2026-11-17T13:55:30+11:00
```

Every column is there because someone watching a run wants it. `t` and `dt`
are in one unit, the unit of the run's clock, named in the column header, so a
reader is not converting between lines. `wall/s` is the first
number to move when a solver gets into trouble — the
replayed step 13 took 0.19 s against the original's 0.09, because a restore
discards each solver's preconditioner set-up and the replay built it again. The label in brackets is the name the script gave
the step, so a run that does different things at different times says which.
And the operators are listed in the order they ran, which is the thing a
caption asserts and a reader cannot otherwise check.

The names are the names the user wrote. The record itself holds the class that
implemented each operator — `SNES_AdvectionDiffusion_Composed` — but the log
says `AdvDiffusion(T)`, which is what the script said, and `Stokes(v)`, and
`shift EulerianSUPG(T)` for the transport history that advanced. The chart and
the figure use the same names, so a name learned in the log is the name found
in the figure.

## How it went, not just that it ran

The `outcome` column reads `ok`, `DIVERGED` or `ABANDONED`. A solve that did
not converge is named under its step, with the reason and the work:

```
      7         2.63841        0.523655      4.81  DIVERGED   [convect] Stokes(v) > ...
  !! SNES_Stokes(v): DIVERGED_LINEAR_SOLVE after 6 its (1200 ksp), |F| 0.000311
```

Behind the column, each solve's record carries the converged reason, the
nonlinear and Krylov counts, the residual norm, and whether a fieldsplit block
hit its iteration cap. That last one is worth its own state: a Stokes solve
whose velocity block gave up reports converged, and the pressure it returned
was solved on an operator that was still moving. The record says which, and
the figure marks it.

Warnings raised inside a step are recorded with where they came from:

```
  ~~ RuntimeWarning: Stokes: the velocity block fell back to 'gamg' — no mesh hierarchy was available...
```

"The velocity block fell back to gamg" changes what the numbers mean. A record
that kept the residual norms but not that line would be an account of the run
with the explanation removed.

## Notes only when something changes

A log that repeats itself is a log nobody reads. The step lines repeat because
each is a fact; everything else is written once, when it happens. A restore
and a rewind are notes between the steps they sit between, so a log that shows
step 13, then step 13 again, says what happened in between. Identical warnings
within a step are written once with a count. The one-line-per-step promise
holds, and the notes are the places to look.

## The chart: collapsing what repeated, by rule

The log is complete, and that creates the problem a profiler has: most steps
are identical, and the ones that matter are buried. Removing the repetitive
ones by hand would be a judgement about what mattered. The chart removes them
by rule instead — consecutive steps that did exactly the same thing collapse
into one line, which carries the first and last value of anything that changed
across them.

```
 step      t/Myr     dt/Myr │ AdvDiffusion(T) │ EulerianSUPG(T) │    Stokes(v)    │
───────────────────────────────────────────────────────────────────────────────────
    0   0.278826   0.278826 │        1        │        2        │        3        │
  …13    20.5101    5.96132 │        ↓        │        ↓        │        ↓        │   ×13 unchanged, dt 0.2788 → 5.961
   14    752.995    732.485 │        1        │        2        │        3        │   ABANDONED
                            │ restore from a snapshot; the clock now reads 20.5101 Myr
                            │ rewind to the start of step 13 (t = 14.5488 Myr); 1 step(s) undone
   13    20.5101    5.96132 │        1        │        2        │        3        │
   14    35.1598    14.6497 │       1,4       │       2,5       │       3,6       │
```

Each column is a participant, and the digits give the order it ran within the
step. The collapsed line asserts that steps 1 to 13 were *identical* to step 0
in what ran and in what order, so nothing hides behind it — and it still says
that `dt` grew from 0.28 to 5.96 Myr across them, because a timestep that
grew twentyfold is a diagnostic. Seventeen step records become five rows and
two notes, and the rows that remain are the ones a reader would have picked
out: the step that tried 732 Myr and was rejected, the step taken again, and the last step that ran
everything twice — `1,4 │ 2,5 │ 3,6` — a predictor-corrector written without
noticing that the transport history advances on every solve, so the
temperature advanced two intervals while the clock advanced one.

Collapsing is optional. A run whose timestep is itself the thing under
examination is easier to read one row at a time.

## The figure

```{figure} figures/run-chart-key.svg
:label: fig-chart
:width: 70%
:alt: The annulus run as a chart. Three columns — AdvDiffusion(T), EulerianSUPG(T), Stokes(v) — and a bar per step in which the marks descend, one line each, joined by a stepped path that runs level and drops halfway between columns; steps 1 to 12 collapsed into one band with the first and last t and dt; step 14 marked abandoned, its marks drawn as dashed rings, with a rewind arrow back to step 13 and an arrow down to the replayed step 13; the last step's bar twice as tall, its path making two descents. Below, a legend, and a key setting each part's residual forms as equations, the named quantities in them with values and units, and its boundary conditions.

The same run as a figure. Each step is a bar, and inside it what ran sits one
line below what ran before, in its own column, joined by a path: the shape of
the path is the sequence. A step that runs everything twice is twice as tall,
and shows it. Each mark says how the solve went — converged, converged with a
block at its cap, or diverged. A run of identical steps collapses into a band
carrying the range of anything that changed. The backtrack is drawn where it
happened: back out of the abandoned step, down to the step taken again. The
key beneath is the model: each part's residual forms set as equations, and
the quantities in them.
```

The three marks are the three things a solve can do. A page that says every
solve converged is a page that can be skimmed; a page with one amber mark in
three hundred is a page that says where to look. The figure is SVG for the
web and PDF for print. Underworld3 draws the bars, marks and paths itself, and
sets the key's equations with matplotlib's mathtext when it is installed, or
as plain text when it is not, so a figure can be drawn wherever the run was.

```{figure} figures/run-transcript.svg
:label: fig-run-transcript
:alt: The same run with time down the page and dt as a horizontal bar per step on a log scale, growing from 0.28 to 5.96 Myr; the abandoned step, which tried 732 Myr, drawn as a dashed bar; the rewind and replay arrows in the gutter; each row lettered by its operator sequence, with the sequences defined once at the foot.

Time down the page, `dt` across it. Each distinct operator sequence gets a
letter, defined once at the foot, so the one step that did something different
is the one letter that differs.
```

## The equations, as implemented

The header lines say each solver's form is in the record. It is: each solver
records the residual it assembled — the templates with their own symbols and
docstrings, the named expressions inside them expanded down to the
constitutive model, the boundary conditions, and the terms it was given — once
per run and again if it changes. `uw.transcript_key` renders that as a key, in
Markdown with LaTeX for a note or a notebook, or in plain text for a terminal.
For the Stokes solver in the run above:

```{math}
\mathbf{f}_0(\mathbf{u}) = \left[\begin{matrix}\dfrac{x\,\rho_0 \alpha g\,T}{\sqrt{x^{2} + y^{2}}}\\[6pt] \dfrac{y\,\rho_0 \alpha g\,T}{\sqrt{x^{2} + y^{2}}}\end{matrix}\right]
\qquad
\mathbf{F}_1(\mathbf{u}) = 2\eta\,\dot{\boldsymbol\varepsilon} + \eta\lambda\,(\nabla\cdot\mathbf{v})\,\mathbf{I} - p\,\mathbf{I}
```

where $\rho_0 \alpha g = 0.9712\ \mathrm{kg/K/m^{2}/s^{2}}$ — buoyancy
coefficient: reference density × thermal expansivity × gravity; $\eta =
10^{22}\ \mathrm{Pa\cdot s}$ — shear viscosity; $\lambda = 0$ — numerical
penalty; with rotated free-slip on the upper and lower boundaries,
$\mathbf{u}\cdot\hat{\mathbf{n}} = 0$.

Two things make that more than a pretty-print. The equation is read from the
solver at the moment it solved, so it is the equation that ran, not the one
the script intended. And the names are the user's: the buoyancy coefficient
appears under the name it was given, with its description, rather than as the
number it collapsed to. A coefficient written as an anonymous float would have
appeared as a float. The key is where the discipline of naming things pays
off, and it pays off in the record rather than in the source.

## Reproducing a result from the record

Restoring is exact. A snapshot holds the fields, the transport history, the
clock and what each solver carries from one solve to the next, and a restore
discards each solver's preconditioner set-up, so the solves after it run as
they would in a run started from the restored state. In the run above, step 13
taken again after the rewind reproduces its first temperature field bit for
bit, `max |ΔT| = 0`.

That is why a run can keep its own restore points.
`model.record_every = 1` keeps the state each step started from — fields,
transport history and clock together — and `model.rewind()` returns to it.
While the run is live, `model.transcript` lists the recorded steps in order,
with the interval each covered and the operators it applied, and any step that
still holds its snapshot can be re-entered with `model.load_state(entry.snapshot)`.
A step that misbehaved can be looked at twice without running the script
again up to it. Snapshots cost about 13 bytes per primary degree of freedom
per step, are off unless asked for, and stay in memory: the last eight are
kept unless `model.record_limit` says otherwise, and none is written to disk.
The transcript on disk is bytes, and `uw.read_transcript(path)` reads it back.

A rewind is a decision, and the record now keeps the decision rather than
only the backtrack. The transcript cannot infer why a run went back, because
the acceptance test lives in the caller's loop, so the caller says:

```python
model.rewind(1, reason="free surface displacement over the limit",
             observed=0.18, threshold=0.10, action="halve dt")
```

The record keeps the reason and the numbers with the rewind, and the log's note between the steps
marks where it happened. A step stopped by an exception
records the exception's class and message as the thing that abandoned it.
And a part is recorded again when a parameter changes between solves, not
only when its form is rebuilt: a diffusivity set to a new value is a
different equation even though no kernel was recompiled, and the record says
so at the step it happened.

## Asking the record questions

Reading a record is one thing; interrogating it is another, and the
questions a debugging session asks are always the same ones. Which steps
were abandoned, and by what? Where did the run go back, and why? Which
solves failed, and which ran with an inner block at its iteration cap? What
was this solver solving at step 600? What changed between step 12 and step
13? Each of those is a walk over the JSON Lines that every reader used to
write for themselves, and each reader wrote it slightly differently.

`uw.Transcript` is one query object over the record, so a notebook, a test,
the digest and a tool all ask the same questions of the same interpretation:

```python
t = uw.Transcript("transcripts/latest/transcript.jsonl")   # or a live model
t.abandoned()                  # rejected steps, each with what stopped it
t.backtracks()                 # rewinds, with the reason the caller gave
t.failed(), t.capped()         # solves by outcome, by the figure's own rule
t.patterns()                   # the run collapsed to its distinct step patterns
t.part("SNES_Stokes#3", at_step=600)   # the equation in force at that step
t.compare(12, 13)              # operators, outcomes, dt, wall time, completion
```

Every answer is the record's own data. A forward solve is `capped` here exactly when
the figure marks it amber, because both read the same rule. `patterns()`
collapses repeated steps by the chart's rule, keyed by position in the
sequence rather than by step index, since after a rewind the run numbers its
steps again from where it went back to and one index can name several
attempts.

The query object describes itself in the same shape as everything else in
the library — kind, name, summary, facts, children — and one renderer sets
that description as Markdown with mathematics for a notebook, plain text for
a terminal, a LaTeX fragment for a note, or YAML for a tool. A solver
describes itself the same way, at the moment it solves and, without an
instance, at the class level: `uw.systems.Stokes.view()` lists the residual
templates it declares, the terms it is given, the conditions it accepts and
the guides that apply to it. So the record and the live object agree on what
an equation looks like, and "what was being solved at step 600" and "what can
this solver solve" are answered from the same description.

That last point is what makes the record usable by a language model as well
as by a person. A small read-only server speaks the Model Context Protocol
over the same queries — a run's summary, its problems, a part at a step, the
catalogue of what the library can solve, and the curated guides that say
which scheme or boundary treatment to choose — and answers in the compact
form first, with the full symbolic form only when asked. A model helping to
debug a run reads the record's own interpretation of it rather than
reconstructing the model from the source, and reads the same interpretation
the author reads. The guides it serves are documentation pages, and the
recipes an assistant loads are links to them, so there is one text to keep
current and a change to a solver is reviewed against the guides that name it.

## Where this lands against FAIR

*Findable* is the stamped directory, the `latest` pointer and the announced
path. *Accessible* is the two formats: the log for `tail -f`, the JSON Lines
for `jq` or `read_transcript`, neither needing Underworld3 to open.
*Interoperable* is how dimensional values are stored — each with its own
magnitude and unit string, `{"magnitude": 4.31, "units": "megayear"}`, rather
than a convention a reader has to be told. *Reusable* is the launch record and
the key together: what ran it, and what it solved.

## What is not in it yet

A part that does nothing in a step is marked as having done nothing only in
the chart, from the roster of parts that played; the log does not mention it.
Mesh deformation and adaptation are not recorded as events, so a history
stored before the mesh moved and read after it has nothing in the record to
flag it. The time integrator a part used is in the key through the names of
its coefficients, and in the part's own description through its scheme and
order, but not yet as a field a query can filter on. And what a step is
*supposed* to contain is inferred from what repeated rather than declared by
the script, so the record can say that one step differs from its neighbours
and cannot yet say that a run disagrees with its own description. That last one is where the Underworld 1 comparison ends
up: a declared plan would be the XML's descendant, a statement of what a step
should contain, checked against the transcript rather than executed from it.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=run-transcripts">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=run-transcripts">Start one</a></div></div>
