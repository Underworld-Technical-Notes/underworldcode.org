# The examples, and what each one measures

Every table and figure in the note is produced by one of these. Run them from
this directory with an Underworld3 environment on the path.

| script | what it produces |
|---|---|
| `leak.py` | the constraint tables — how much flow each treatment lets through, under refinement (`sweep`) and against its own parameter (`params`) |
| `stress.py` | the surface-stress tables against the exact `uw.analytic.CylindricalStokes` answer: `sweep`, `params`, `locking`, `control` |
| `solcx.py` | the lateral-viscosity half, against `uw.analytic.SolCx`: `sweep`, `contrast`, `params`, `control` |
| `generate-locking-figure.py` | `figures/locking.png` and `figures/banner.png` |
| `generate-rotated-basis.py` | the data behind `rotated-basis.typ`, which draws `figures/rotated-basis.svg` |

## The traps, all paid for once

- **`v.array` is `(N, 1, dim)`.** It broadcasts silently against `(N, dim)`
  normals and returns ~1e-16 projections for a 1e-2 velocity, with no error.
  `np.squeeze` it. Every number in the first leak run was this artefact.
- **Give every metric a negative control and run it.** Two free-slip circles
  leave the rigid rotation unconstrained, and that nullspace is purely
  tangential — so a radial leak metric read 2e-14 on a solve that had diverged
  with `|u| = 2.7e5`. The inner boundary is now held.
- **Check `snes.getConvergedReason() > 0` before tabulating anything.** Diverged
  runs leave plausible numbers in the array; two nearly reached the note.
- **Vertex against edge midpoint.** On a curved boundary, vertex values of
  `sigma_nn` carry the O(h) facet error and midpoints are superconvergent
  (underworld3#414). `stress.py` splits them and the note says which it uses.
- **Select a boundary trace by the mesh LABEL, not by a radius band.** A band
  that narrows with the mesh admits a different node set at each resolution, and
  the earlier version of this comparison drifted by four nodes between methods
  because of it.
- **Enclosed domain**: the multiplier, the pressure and the traction are each
  determined only up to a constant. Compare deviations, which is what topography
  is anyway.
- **A `Piecewise` viscosity inside a boundary penalty term does not solve** on
  SolCx, at any magnitude tried.

## What is still open

- The spherical case. `uw.analytic.Zhong2008` publishes
  `.response().surface_topography = 0.4191904156575601` for the default
  degree-2 case (load r = 0.775, r_inner = 0.55, isoviscous), which is the right
  oracle for dynamic topography proper. It is a 3-D shell, and that is the cost
  step this note stopped short of.
- Behr (2004) reports non-physical recirculation at curved walls even with the
  consistent normal. We have not looked for it here.
- underworld3 issues #607 (the multiplier misses the augmented-Lagrangian share)
  and #608 (the rotated constraint at a corner shared with a component
  condition) both came out of these runs and are open.
