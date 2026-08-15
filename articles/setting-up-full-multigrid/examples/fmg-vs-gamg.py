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

GAMG here is GAMG AS UNDERWORLD CONFIGURES IT. Algebraic multigrid on an
elasticity-like operator wants the rigid-body near-null space, and Underworld
does not supply it for the Stokes velocity block. Attaching it from outside was
attempted with PCSetCoordinates on the velocity sub-PC, with and without a PC
reset, and had no effect -- byte-identical iteration counts either way -- so it
needs a change inside Underworld. Read the GAMG column as "the default", not as
"the best algebraic multigrid can do".
"""
import math
import time

import sympy
import underworld3 as uw

BASE_CELL = 1 / 8
QDEG = 3
TOL = 1.0e-6
VEL_CAP = 2000
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
    tally = {"outer": 0, "velocity": 0}
    ksp.setMonitor(lambda k, i, rn: tally.__setitem__("outer", tally["outer"] + 1))
    sub.setMonitor(lambda k, i, rn: tally.__setitem__("velocity", tally["velocity"] + 1))

    v.array[...] = 0.0
    p.array[...] = 0.0

    t0 = time.time()
    stokes.solve(zero_init_guess=True)
    wall = time.time() - t0

    ok = stokes.snes.getConvergedReason() > 0 and sub.getConvergedReason() > 0
    return dict(wall=wall, ok=ok, ndof=stokes.snes.getSolution().getSize(),
                outer=tally["outer"], velocity=tally["velocity"])


def contrast_table():
    """Cost against viscosity contrast, at one resolution."""
    rows = [(c, pc, solve_once(pc, 2, c))
            for c in (1.0, 1.0e2, 1.0e4, 1.0e6) for pc in ("fmg", "gamg")]
    # Effort per unknown, relative to FMG on the easiest problem. Dimensionless
    # on purpose: a ratio does not depend on the machine it was measured on, so
    # the table means the same thing wherever it is read.
    base = next(r["wall"] / r["ndof"] for c, pc, r in rows if c == 1.0 and pc == "fmg")
    print("\n| preconditioner | viscosity contrast | velocity iterations | relative effort per unknown |")
    print("|---|---|---|---|")
    for c, pc, r in sorted(rows, key=lambda k: (k[1] != "fmg", k[0])):
        if r["ok"]:
            print("| %s | 10^%d | %d | %.2f |"
                  % (pc.upper(), round(math.log10(c)), r["velocity"],
                     (r["wall"] / r["ndof"]) / base))
        else:
            print("| %s | 10^%d | — | diverged |" % (pc.upper(), round(math.log10(c))))


def scaling_table():
    """Cost against problem size, at constant viscosity. Same columns as above."""
    out = {}
    for pc, refs in (("fmg", (1, 2, 3, 4)), ("gamg", (1, 2, 3))):
        out[pc] = [solve_once(pc, r, 1.0) for r in refs]
    # Same normalisation as the contrast table: FMG on the smallest problem.
    base = out["fmg"][0]["wall"] / out["fmg"][0]["ndof"]
    print("\n| preconditioner | unknowns | velocity iterations | relative effort per unknown |")
    print("|---|---|---|---|")
    for pc in ("fmg", "gamg"):
        for r in out[pc]:
            print("| %s | %d | %d | %.2f |"
                  % (pc.upper(), r["ndof"], r["velocity"],
                     (r["wall"] / r["ndof"]) / base))
    print()
    for pc, rows in out.items():
        xs = [math.log(r["ndof"]) for r in rows]
        ys = [math.log(r["wall"]) for r in rows]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        power = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                 / sum((x - mx) ** 2 for x in xs))
        print("%s: wall clock scales as N^%.2f" % (pc.upper(), power))


if __name__ == "__main__":
    contrast_table()
    scaling_table()
