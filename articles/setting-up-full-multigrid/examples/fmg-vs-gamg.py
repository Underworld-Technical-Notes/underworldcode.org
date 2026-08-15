"""FMG against GAMG on the SolKz problem: timing only.

SolKz is the standard smooth-viscosity Stokes benchmark: on the unit box,

    eta(z) = exp(2 B z)          viscosity varying exponentially with depth
    f      = (0, sin(m pi z) cos(n pi x))
    free slip on all four walls

and the viscosity contrast across the box is exp(2B). It has a closed-form
solution, but nothing here uses it: every number below is a TIME, and the point
is how the cost of the solve behaves, not how accurate the answer is.

Two things are deliberately fixed across every run:

  * the solver tolerance. Holding it constant while the mesh refines is the
    usual way to show a multigrid scaling, and it is a choice rather than a
    neutral one -- a finer mesh has a smaller discretisation error, so an
    argument could be made for tightening the solver tolerance alongside it,
    which would make the work per unknown grow. Fixed tolerance answers "what
    does it cost to solve this system", not "what does it cost to reach the
    accuracy the mesh can support".

  * the velocity iteration cap, raised well above the default 200 so that
    neither preconditioner is truncated rather than allowed to converge.

The velocity block is solved with fgmres preconditioned by multigrid, so one
Krylov iteration is one multigrid cycle. Counting them needs care: the Schur
factorisation invokes the velocity solve SIXTEEN times per Stokes solve, so a
naive total folds in a factor that is identical for both preconditioners. What
is reported here is therefore cycles PER VELOCITY SOLVE, which is the
like-for-like number. Even so it counts cycles, not work -- a geometric cycle
and an algebraic one are different amounts of it, which is what the timings
are for.
"""
import math
import time

import sympy
import underworld3 as uw

BASE_CELL = 1 / 8
QDEG = 3
TOL = 1.0e-6
VEL_CAP = 2000
REPEATS = 3          # timings scatter; take the median of a few
N_X, M_Z = 3, 2          # the SolKz wavenumbers


def solve_once(pc, refinement, contrast):
    """Time one SolKz solve. Returns (wall seconds, converged, unknowns)."""
    B = 0.5 * math.log(contrast) if contrast > 1.0 else 0.0
    mesh = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0),
        cellSize=BASE_CELL, qdegree=QDEG, refinement=refinement)
    x, z = mesh.X.coords_sym if hasattr(mesh.X, "coords_sym") else mesh.X

    v = uw.discretisation.MeshVariable("U", mesh, mesh.dim, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = sympy.exp(2 * B * z)
    stokes.bodyforce = sympy.Matrix(
        [0, sympy.sin(M_Z * sympy.pi * z) * sympy.cos(N_X * sympy.pi * x)])

    # Free slip: the wall-normal component is held, the tangential one is free.
    for wall, comp in (("Left", (0,)), ("Right", (0,)),
                       ("Bottom", (1,)), ("Top", (1,))):
        stokes.add_dirichlet_bc((0.0,) * mesh.dim, wall, comp)

    stokes.preconditioner = pc
    stokes.tolerance = TOL
    stokes.petsc_options.setValue("fieldsplit_velocity_ksp_max_it", VEL_CAP)

    stokes.solve()                       # build everything; not timed

    # Count iterations across the WHOLE solve, not the last linear solve. A
    # linear Stokes SNES does its work in the first solve and the second
    # converges immediately, so getIterationNumber() afterwards reports the
    # trivial one and makes every resolution look identical.
    ksp = stokes.snes.getKSP()
    sub = ksp.getPC().getFieldSplitSubKSP()[0]
    # Record the ITERATION INDEX, not just a count: every time it restarts at
    # zero the Schur factorisation has invoked the velocity solve again, which
    # is what separates "cycles per solve" from "cycles in total".
    seen = []
    sub.setMonitor(lambda k, i, rn: seen.append(i))

    v.array[...] = 0.0
    p.array[...] = 0.0

    t0 = time.time()
    stokes.solve(zero_init_guess=True)
    wall = time.time() - t0

    ok = stokes.snes.getConvergedReason() > 0 and sub.getConvergedReason() > 0
    starts = [j for j, i in enumerate(seen) if i == 0]
    per_solve = [len(seen[a:b]) for a, b in zip(starts, starts[1:] + [len(seen)])]
    return dict(wall=wall, ok=ok, ndof=stokes.snes.getSolution().getSize(),
                invocations=len(starts), velocity=len(seen),
                cycles=(min(per_solve), max(per_solve)) if per_solve else (0, 0))


def repeat(pc, refinement, contrast):
    """Median of REPEATS timings. Wall clock scatters by a few per cent, so a
    single run is not a number worth reporting to two decimal places."""
    runs = [solve_once(pc, refinement, contrast) for _ in range(REPEATS)]
    walls = sorted(r["wall"] for r in runs)
    out = dict(runs[0])
    out["wall"] = walls[len(walls) // 2]
    out["spread"] = (walls[-1] - walls[0]) / walls[len(walls) // 2]
    return out


def contrast_table():
    """Cost against viscosity contrast, at one resolution."""
    rows = [(c, pc, repeat(pc, 2, c))
            for c in (1.0, 1.0e2, 1.0e4, 1.0e6) for pc in ("fmg", "gamg")]
    # Effort per unknown, relative to FMG on the easiest problem. Dimensionless
    # on purpose: a ratio does not depend on the machine it was measured on, so
    # the table means the same thing wherever it is read.
    base = next(r["wall"] / r["ndof"] for c, pc, r in rows if c == 1.0 and pc == "fmg")
    print("\n| preconditioner | viscosity contrast | relative effort per unknown |")
    print("|---|---|---|")
    for c, pc, r in sorted(rows, key=lambda k: (k[1] != "fmg", k[0])):
        if r["ok"]:
            print("| %s | 10^%d | %d | %.1f |"
                  % (pc.upper(), round(math.log10(c)), r["velocity"],
                     (r["wall"] / r["ndof"]) / base))
        else:
            print("| %s | 10^%d | — | diverged |" % (pc.upper(), round(math.log10(c))))


def scaling_table():
    """Cost against problem size, at constant viscosity. Same columns as above."""
    out = {}
    for pc, refs in (("fmg", (1, 2, 3, 4)), ("gamg", (1, 2, 3))):
        out[pc] = [repeat(pc, r, 1.0) for r in refs]
    # Same normalisation as the contrast table: FMG on the smallest problem.
    base = out["fmg"][0]["wall"] / out["fmg"][0]["ndof"]
    print("\n| preconditioner | unknowns | relative effort per unknown |")
    print("|---|---|---|")
    for pc in ("fmg", "gamg"):
        for r in out[pc]:
            print("| %s | %d | %.1f |"
                  % (pc.upper(), r["ndof"], (r["wall"] / r["ndof"]) / base))
    print("\n| preconditioner | " + " | ".join("%d unknowns" % r["ndof"] for r in out["fmg"][:3]) + " |")
    print("|---|" + "---|" * 3)
    for pc in ("fmg", "gamg"):
        cells = []
        for r in out[pc][:3]:
            lo, hi = r["cycles"]
            cells.append(str(lo) if lo == hi else "%d\u2013%d" % (lo, hi))
        print("| %s | %s |" % (pc.upper(), " | ".join(cells)))
    print("\n(velocity solves per Stokes solve: %s)"
          % sorted({r["invocations"] for rows in out.values() for r in rows}))

    print()
    for pc, rows in out.items():
        xs = [math.log(r["ndof"]) for r in rows]
        ys = [math.log(r["wall"]) for r in rows]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        power = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                 / sum((x - mx) ** 2 for x in xs))
        print("%s: solve time scales as N^%.2f  (worst run-to-run spread %.0f%%)"
              % (pc.upper(), power, 100 * max(r["spread"] for r in rows)))


if __name__ == "__main__":
    contrast_table()
    scaling_table()
