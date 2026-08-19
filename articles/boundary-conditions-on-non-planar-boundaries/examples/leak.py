"""How much flow does each boundary treatment let through?

The note claims a direct penalty and Nitsche satisfy `u.n = 0` only to the
accuracy of the discretisation, while rotating the degrees of freedom satisfies
it to the accuracy of the arithmetic. This measures that rather than asserting
it.

The test is an annulus -- a boundary with no preferred direction, which is the
whole point -- driven by a single-wavenumber density anomaly, free slip on both
radii.

TWO leaks are reported, and the difference between them is the subject of the
note's section on which normal to use:

  * against the FACET normal, which is what the discrete constraint actually
    imposes;
  * against the TRUE radial direction of the circle the mesh approximates.

A strongly imposed constraint should be at machine precision against the first
and at the faceting error against the second. A weakly imposed one is limited
by its own penalty long before either.

Reproduces the table in the note:

    python3 leak.py sweep      # the resolution table
    python3 leak.py free       # the control: outer boundary left natural

Run against underworld3 `bugfix/multiplier-traction` (PR #617); the
constrained solver's `traction()` is the fix this note prompted.
"""
import sys

import numpy as np
import sympy

import underworld3 as uw

CELL = 0.075
GAMMA = 10.0


def build(mode, cell=CELL, penalty=1.0e4, gamma=GAMMA):
    mesh = uw.meshing.Annulus(radiusInner=0.5, radiusOuter=1.0, cellSize=cell)
    x, y = mesh.X
    r = sympy.sqrt(x**2 + y**2)

    v = uw.discretisation.MeshVariable("U", mesh, mesh.dim, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    solver_class = (uw.systems.Stokes_Constrained if mode == "constraint"
                    else uw.systems.Stokes)
    stokes = solver_class(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = 1.0

    # a degree-4 density anomaly: enough structure that the boundary has to work
    theta = sympy.atan2(y, x)
    stokes.bodyforce = sympy.Matrix(
        [sympy.cos(4 * theta) * x / r, sympy.cos(4 * theta) * y / r])

    # The INNER boundary is no-slip throughout. Two free-slip circles leave
    # the rigid rotation unconstrained, and the resulting nullspace is purely
    # TANGENTIAL -- so a radial leak metric reads zero on a diverged solve and
    # cannot tell a working constraint from a broken one. Measured: the
    # unconstrained control diverged with |u| = 2.7e5 and still reported a
    # radial leak of 2e-14.
    stokes.add_dirichlet_bc((0.0, 0.0), "Lower")

    for boundary in ("Upper",):
        if mode == "free":
            continue          # the control: outer boundary left natural
        if mode == "constraint":
            # A multiplier field h coupled into the saddle-point system, so the
            # constraint is a ROW of the system rather than a term added to
            # one. At convergence h on the boundary is the normal traction,
            # which is why this one is also a way of getting the stress.
            stokes.add_constraint_bc(0.0, boundary)
        elif mode == "rotated":
            stokes.add_rotated_freeslip_bc(0.0, boundary)
        elif mode == "nitsche":
            stokes.add_nitsche_bc(0.0, boundary, gamma=gamma, theta=1)
        elif mode == "penalty":
            # A DIRECT penalty: a boundary traction opposing normal flow, and
            # nothing else -- no consistency term, which is exactly what leaves
            # it consistent only in the limit. The documented form, from
            # docs/advanced/curved-boundary-conditions.md, uses the
            # quadrature-point facet normal mesh.Gamma and a POSITIVE
            # coefficient. A negative one is anti-damping and the linear solve
            # fails immediately, which is how this was got wrong the first time.
            #
            # READ THIS COLUMN WITH stress.py BESIDE IT. Imposed facet by facet
            # on a curved boundary, this constraint LOCKS: the leak falls
            # because the boundary is being frozen, not because the condition is
            # being satisfied in the way that was meant. At cell 0.075 the
            # velocity field here differs from the rotated one by 20% in l2 at
            # a coefficient of 1e4, and stress.py measures the same thing
            # against an exact answer.
            G = mesh.Gamma
            stokes.add_natural_bc(penalty * G.dot(v.sym) * G, boundary)
        elif mode == "penalty_node":
            # The same penalty against the measure-weighted NODE normal, which
            # is one direction per node rather than one per facet, and does not
            # lock. The only difference between this and the line above is which
            # normal.
            G = mesh.boundary_normal(boundary)
            stokes.add_natural_bc(penalty * G.dot(v.sym) * G, boundary)
        else:
            raise ValueError(mode)
    return mesh, stokes, v


def converged(stokes):
    """A diverged solve still leaves numbers in the array, and they look like
    measurements. Two runs in the first parameter sweep here had failed the
    line search and were about to be tabulated."""
    return stokes.snes.getConvergedReason() > 0


def leaks(mesh, v):
    """max |u.n| on the outer boundary, against the facet normal and against
    the true radial direction, both normalised by the flow speed."""
    coords = v.coords
    rad = np.linalg.norm(coords, axis=1)
    on_outer = np.abs(rad - 1.0) < 1.0e-6
    # squeeze: a vector MeshVariable's .array is (N, 1, dim), and the middle
    # axis broadcasts SILENTLY against an (N, dim) array of normals, giving a
    # projection of ~1e-16 for a velocity of ~1e-2. It does not raise.
    allu = np.squeeze(np.asarray(v.array))
    u = allu[on_outer]
    xy = coords[on_outer]
    speed = np.linalg.norm(allu, axis=1).max()

    # true normal of the circle the mesh approximates
    n_true = xy / np.linalg.norm(xy, axis=1)[:, None]
    leak_true = np.abs((u * n_true).sum(axis=1)).max() / speed
    return leak_true, on_outer.sum(), speed


def sweep(cells=(0.15, 0.10, 0.075, 0.05),
          modes=("penalty", "penalty_node", "nitsche", "constraint", "rotated")):
    """Does the leak fall with the mesh, or is it already at round-off?

    A weakly imposed constraint is satisfied to the accuracy of the
    DISCRETISATION, so its leak should fall as the mesh is refined. A strongly
    imposed one is satisfied to the accuracy of the ARITHMETIC, so its leak
    should sit at round-off and stay there. That difference is the claim, and
    the refinement is what tells them apart -- a single resolution cannot.
    """
    print("| cell size | %s |" % " | ".join(m for m in modes))
    print("|---|" + "---|" * len(modes))
    for cell in cells:
        row = []
        for mode in modes:
            mesh, stokes, v = build(mode, cell=cell)
            stokes.solve()
            row.append(("%.2e" % leaks(mesh, v)[0]) if converged(stokes)
                       else "diverged")
        print("| %.3f | %s |" % (cell, " | ".join(row)))


def parameter_sweep():
    """The distinction between a direct penalty and Nitsche, measured.

    Both are bounded above by conditioning: the penalty stops improving past
    1e4 and fails at 1e6, and Nitsche's line search fails from gamma = 1e4.
    Neither escapes tuning. What differs is the floor each reaches first --
    1e-3 for the penalty, 3e-5 for Nitsche -- and that Nitsche is ALSO bounded
    below, at gamma = 1, where the form stops being coercive. Its usable window
    has a threshold at each end, and gamma = 10 sits in the middle of it on any
    mesh because gamma is dimensionless and the term already carries mu/h.
    """
    print("\ndirect penalty (FACET normal): leak against penalty magnitude")
    print("\n| penalty | leak/|u| |")
    print("|---|---|")
    for pen in (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6):
        mesh, stokes, v = build("penalty", penalty=pen)
        stokes.solve()
        cell = ("%.2e" % leaks(mesh, v)[0]) if converged(stokes) else "diverged"
        print("| %.0e | %s |" % (pen, cell))

    print("\ndirect penalty (NODE normal): leak against penalty magnitude")
    print("\n| penalty | leak/|u| |")
    print("|---|---|")
    for pen in (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6):
        mesh, stokes, v = build("penalty_node", penalty=pen)
        stokes.solve()
        cell = ("%.2e" % leaks(mesh, v)[0]) if converged(stokes) else "diverged"
        print("| %.0e | %s |" % (pen, cell))

    print("\nNitsche: leak against gamma")
    print("\n| gamma | leak/|u| |")
    print("|---|---|")
    for g in (1.0, 10.0, 100.0, 1000.0, 1.0e4, 1.0e5):
        mesh, stokes, v = build("nitsche", gamma=g)
        stokes.solve()
        cell = ("%.2e" % leaks(mesh, v)[0]) if converged(stokes) else "diverged"
        print("| %g | %s |" % (g, cell))


if __name__ == "__main__":
    if sys.argv[1:2] == ["sweep"]:
        sweep()
    elif sys.argv[1:2] == ["params"]:
        parameter_sweep()
    else:
        modes = sys.argv[1:] or ["free", "penalty", "penalty_node", "nitsche",
                                 "constraint", "rotated"]
        print("%-9s %10s %10s %8s" % ("mode", "leak/|u|", "|u|max", "nodes"))
        for mode in modes:
            mesh, stokes, v = build(mode)
            stokes.solve()
            lk, n, speed = leaks(mesh, v)
            print("%-9s %10.3e %10.3e %8d" % (mode, lk, speed, n))
