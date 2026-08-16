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

Run against underworld3 `development` at commit `0addec15`
(0addec1595f8d7a59b99e15b42455267a73dab86, 2026-08-15). `uw.__version__`
reports 0.0.0 for every build, so the commit is the only thing that
identifies what these numbers came from.
"""
import math
import os
import subprocess
import sys
import time

from petsc4py import PETSc

PETSc.Log.begin()   # before any solving, or the counts start from nowhere

import sympy
import underworld3 as uw

BASE_CELL = 1 / 8
QDEG = 3
TOL = 1.0e-6
VEL_CAP = 20000      # high enough that NOTHING is truncated at any size
                     # measured here. At 2000, GAMG at the largest problem is
                     # cut off mid-solve, the outer solve compensates with twice
                     # as many velocity solves, and the reported work jumps 35%
                     # for a reason that has nothing to do with the method.
# Each configuration is measured in a FRESH PROCESS.
#
# Measured alone, every configuration here is exactly reproducible: the same
# flop count to five figures, and sixteen velocity solves per Stokes solve.
# Run back to back in one process they are not -- one sweep reported a doubled
# invocation count and a 35% larger GAMG figure, which no configuration
# reproduces on its own. Something survives between solves. Rather than trust a
# number that depends on what ran before it, the parent process below invokes
# this file once per configuration and parses one line back.
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
    if pc == "gamg":
        # Back to the PETSc default; Underworld sets `additive`.
        stokes.petsc_options.setValue(
            "fieldsplit_velocity_pc_mg_type", "multiplicative")

    stokes.solve()                       # build everything; not timed

    if pc == "gamg":
        # Tell GAMG the field has two components per node, so it aggregates
        # nodes rather than scalars. The operator is built by PETSc from the
        # DM, so this has to be set after it exists and the PC rebuilt.
        sub_v = stokes.snes.getKSP().getPC().getFieldSplitSubKSP()[0]
        A, P = sub_v.getOperators()
        A.setBlockSize(mesh.dim)
        if P.handle != A.handle:
            P.setBlockSize(mesh.dim)
        sub_v.getPC().reset()

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

    # Flops as well as time. The flop count is deterministic and independent of
    # the machine, so it measures the METHOD; the time measures this machine.
    # Their ratio is the rate, which is where the two disagree.
    f0 = PETSc.Log.getFlops()
    t0 = time.time()
    stokes.solve(zero_init_guess=True)
    wall = time.time() - t0
    flops = PETSc.Log.getFlops() - f0

    ok = stokes.snes.getConvergedReason() > 0 and sub.getConvergedReason() > 0
    starts = [j for j, i in enumerate(seen) if i == 0]
    per_solve = [len(seen[a:b]) for a, b in zip(starts, starts[1:] + [len(seen)])]
    return dict(wall=wall, flops=flops, ok=ok,
                ndof=stokes.snes.getSolution().getSize(),
                invocations=len(starts), velocity=len(seen),
                cycles=(min(per_solve), max(per_solve)) if per_solve else (0, 0))


def _measure_and_print(pc, refinement, contrast):
    """Child-process entry point: measure one configuration, print one line."""
    r = solve_once(pc, refinement, contrast)
    print("RESULT %s %d %g %d %r %.6e %.6f %d %d %d"
          % (pc, refinement, contrast, r["ndof"], r["ok"], r["flops"],
             r["wall"], r["invocations"], r["cycles"][0], r["cycles"][1]))


def measure(pc, refinement, contrast):
    """Run one configuration in a fresh interpreter and read the result back."""
    out = subprocess.run(
        [sys.executable, os.path.abspath(__file__),
         "--one", pc, str(refinement), repr(contrast)],
        capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith("RESULT "):
            f = line.split()
            return dict(pc=f[1], ndof=int(f[4]), ok=f[5] == "True",
                        flops=float(f[6]), wall=float(f[7]),
                        invocations=int(f[8]),
                        cycles=(int(f[9]), int(f[10])))
    sys.stderr.write(out.stdout + out.stderr)
    raise RuntimeError("no result from %s at refinement %d, contrast %g"
                       % (pc, refinement, contrast))


def contrast_table():
    """Cost against viscosity contrast, at one resolution."""
    rows = [(c, pc, measure(pc, 2, c))
            for c in (1.0, 1.0e2, 1.0e4, 1.0e6) for pc in ("fmg", "gamg")]
    # Work per unknown, relative to FMG on the easiest problem. A ratio does
    # not depend on the machine it was measured on.
    bw = next(r["flops"] / r["ndof"] for c, pc, r in rows if c == 1.0 and pc == "fmg")
    bt = next(r["wall"] / r["ndof"] for c, pc, r in rows if c == 1.0 and pc == "fmg")
    print("\n| preconditioner | viscosity contrast | relative work per unknown "
          "| relative time per unknown |")
    print("|---|---|---|---|")
    for c, pc, r in sorted(rows, key=lambda k: (k[1] != "fmg", k[0])):
        if r["ok"]:
            print("| %s | 10^%d | %.1f | %.1f |"
                  % (pc.upper(), round(math.log10(c)),
                     (r["flops"] / r["ndof"]) / bw, (r["wall"] / r["ndof"]) / bt))
        else:
            print("| %s | 10^%d | diverged | diverged |"
                  % (pc.upper(), round(math.log10(c))))


def scaling_table():
    """Cost against problem size, at constant viscosity."""
    # FMG runs one level further: the trend towards O(N) is only visible once
    # the fixed costs stop dominating, and GAMG at that size costs four minutes.
    out = {pc: [measure(pc, r, 1.0) for r in refs]
           for pc, refs in (("fmg", (1, 2, 3, 4, 5)), ("gamg", (1, 2, 3, 4)))}

    bw = out["fmg"][0]["flops"] / out["fmg"][0]["ndof"]
    bt = out["fmg"][0]["wall"] / out["fmg"][0]["ndof"]
    print("\n| preconditioner | unknowns | relative work per unknown "
          "| relative time per unknown | Gflop/s |")
    print("|---|---|---|---|---|")
    for pc in ("fmg", "gamg"):
        for r in out[pc]:
            print("| %s | %d | %.1f | %.1f | %.1f |"
                  % (pc.upper(), r["ndof"], (r["flops"] / r["ndof"]) / bw,
                     (r["wall"] / r["ndof"]) / bt, r["flops"] / r["wall"] / 1e9))

    print("\n| preconditioner | %s |"
          % " | ".join("%d unknowns" % r["ndof"] for r in out["fmg"][:3]))
    print("|---|" + "---|" * 3)
    for pc in ("fmg", "gamg"):
        cells = []
        for r in out[pc][:3]:
            lo, hi = r["cycles"]
            cells.append(str(lo) if lo == hi else "%d\u2013%d" % (lo, hi))
        print("| %s | %s |" % (pc.upper(), " | ".join(cells)))
    invocations = sorted({r["invocations"] for rows in out.values() for r in rows})
    print("\n(velocity solves per Stokes solve: %s)" % invocations)

    print()
    for pc, rows in out.items():
        steps = [math.log(b["flops"] / a["flops"]) / math.log(b["ndof"] / a["ndof"])
                 for a, b in zip(rows, rows[1:])]
        xs = [math.log(r["ndof"]) for r in rows]
        ys = [math.log(r["wall"]) for r in rows]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        power = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                 / sum((x - mx) ** 2 for x in xs))
        print("%s: time ~ N^%.2f, flops ~ N^%s per step"
              % (pc.upper(), power, [round(s, 2) for s in steps]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        _measure_and_print(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
    else:
        contrast_table()
        scaling_table()
