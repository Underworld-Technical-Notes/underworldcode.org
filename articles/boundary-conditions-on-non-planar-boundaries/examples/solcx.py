"""The other half of the stress test: a lateral viscosity contrast.

`stress.py` is the geometry half -- a curved boundary with the rheology
trivial. This is the rheology half, with the geometry trivial. No exact
solution has both, so the two halves are separate tests and the note does not
conflate them.

On a box, "no flow through this wall" is a single velocity component and every
treatment here reduces to the same constraint. Nothing about this test is about
normals. What it is about is whether a WEAKLY imposed constraint holds the
degrees of freedom it was given when the viscosity beside them jumps by six
orders of magnitude -- and SolCx is the only case of the two halves with an
exact surface stress to check that against.

SolCx: unit box, viscosity eta_A left of x = 0.5 and eta_B right of it,
forcing (0, cos(pi.x) sin(pi.z)), free slip on all four walls.
`uw.analytic.SolCx` publishes the exact stress, and `topography_top` is
-sigma_zz on the top boundary, which is the quantity here.

Three walls carry the ordinary component Dirichlet condition. The treatment
under test is on the TOP wall only, so what is measured is attributable to it.

The metrics
-----------
  * the leak, max |u.n| / |u|, reported SEPARATELY over the soft half of the
    wall and the stiff half. One coefficient has to hold both, and whether it
    can is the whole question;
  * the surface stress: relative l2 error of sigma_zz along the top wall
    against the exact one, both mean-removed (the box is enclosed, so the
    pressure -- and with it the level of sigma_zz -- is fixed only up to a
    constant).

    python3 solcx.py sweep        # resolution, each treatment
    python3 solcx.py contrast     # the viscosity ratio, each treatment
    python3 solcx.py params       # the penalty coefficient, both halves
    python3 solcx.py control      # the top wall left free

Run against underworld3 `bugfix/multiplier-traction` (PR #617); the
constrained solver's `traction()` is the fix this note prompted.
"""
import sys

import numpy as np
import sympy

import underworld3 as uw

from underworld3.utilities.boundary_flux import _boundary_field_nodes

RES = 32
ETA_B = 1.0e6
PENALTY = 1.0e4
GAMMA = 10.0


def build(mode, res=RES, eta_B=ETA_B, penalty=PENALTY, gamma=GAMMA):
    mesh = uw.meshing.StructuredQuadBox(
        elementRes=(res, res), minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), qdegree=3)

    v = uw.discretisation.MeshVariable("U", mesh, mesh.dim, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    solver_class = (uw.systems.Stokes_Constrained if mode == "constraint"
                    else uw.systems.Stokes)
    stokes = solver_class(mesh, velocityField=v, pressureField=p)

    exact = uw.analytic.SolCx(mesh, eta_A=1.0, eta_B=eta_B, x_c=0.5, n=1)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = exact.fn_viscosity
    if mode != "constraint":
        # Stokes_Constrained builds its own Schur preconditioner from the
        # operator's blocks and refuses this assignment.
        stokes.saddle_preconditioner = 1.0 / exact.fn_viscosity
    stokes.bodyforce = exact.fn_bodyforce
    stokes.tolerance = 1.0e-9
    # Enclosed: the constant pressure mode is a nullspace and a direct solve on
    # the singular saddle returns a quiet, wrong answer without this. With the
    # top wall left free (the control) the domain is open and there is no such
    # mode -- asserting one there is what makes the control fail to solve
    # rather than fail to hold the boundary.
    stokes.petsc_use_pressure_nullspace = (mode != "free")

    stokes.add_dirichlet_bc((0.0, None), "Left")
    stokes.add_dirichlet_bc((0.0, None), "Right")
    stokes.add_dirichlet_bc((None, 0.0), "Bottom")

    if mode == "dirichlet":
        # What a box lets you do, and the reference the others are judged by.
        stokes.add_dirichlet_bc((None, 0.0), "Top")
    elif mode == "constraint":
        stokes.add_constraint_bc(0.0, "Top")
    elif mode == "rotated":
        stokes.add_rotated_freeslip_bc(0.0, "Top")
    elif mode == "nitsche":
        stokes.add_nitsche_bc(0.0, "Top", gamma=gamma, theta=1)
    elif mode == "penalty":
        # A CONSTANT coefficient, deliberately. Scaling it by the local
        # viscosity is the fair thing to want here -- one number cannot be large
        # against 1e6 and moderate against 1 -- and it does not solve: a
        # Piecewise viscosity inside the boundary term fails the line search at
        # every magnitude tried, from 1 to 1e3 times mu, against both normals.
        # A constant 1e4 solves, and that is what this column is.
        stokes.add_natural_bc(penalty * mesh.Gamma.dot(v.sym) * mesh.Gamma, "Top")
    elif mode == "free":
        pass
    else:
        raise ValueError(mode)

    return mesh, stokes, v, exact


def converged(stokes):
    return stokes.snes.getConvergedReason() > 0


def trace(solver, field_id, var, boundary="Top"):
    """(coords, values) for `var` at the nodes it carries on `boundary`,
    selected by the mesh boundary LABEL."""
    nodes, *_ = _boundary_field_nodes(solver, boundary, field_id)
    coords = np.array([node[2] for node in nodes])
    tree = uw.kdtree.KDTree(np.ascontiguousarray(var.coords))
    index = np.asarray(tree.query(np.ascontiguousarray(coords), 1)[1]).flatten()
    return coords, np.squeeze(np.asarray(var.array))[index]


def recovered_traction(mesh, stokes):
    """sigma_zz on the top wall, projected out of the solved fields."""
    field = uw.discretisation.MeshVariable("Szz", mesh, 1, degree=2)
    projection = uw.systems.Projection(mesh, field)
    projection.uw_function = stokes.stress[1, 1]
    projection.solve()
    return trace(projection, 0, field)


def reaction_traction(stokes, mode):
    """The traction the solve returned, for the two methods that return one."""
    if mode == "rotated":
        return stokes.boundary_normal_traction("Top")
    if mode == "constraint":
        # `traction()` is h + r(u.n - g), the WHOLE boundary term. Reading the
        # multiplier alone here was wrong by an order of magnitude and a sign at
        # a 1e6 viscosity contrast, because the default r is viscosity-weighted
        # (underworld3#607, fixed in #617). The box is flat, so evaluating the
        # expression at the trace nodes is safe -- on a convex curved boundary it
        # would extrapolate (#605), which is why stress.py reads arrays instead.
        coords, _h = trace(stokes, 2, stokes.multiplier("Top"))
        return coords, np.asarray(
            uw.function.evaluate(stokes.traction("Top"), coords)).reshape(-1)
    return None


def stress_error(coords, values, exact, trim=0.0):
    """Relative l2 error along the wall, both mean-removed.

    The mean is the gauge: the box is enclosed, so the pressure and with it the
    level of sigma_zz is fixed only up to a constant. The deviation is what
    topography is built from and the only part that is determined.

    `trim` drops nodes within that distance of the two ends of the wall. The
    corners are where the treatment under test meets the side walls' component
    conditions, so a node there is constrained twice and by two different
    mechanisms; trimming separates what the wall does from what the corner does.
    """
    coords = np.asarray(coords)
    values = np.asarray(values)
    if trim > 0.0:
        keep = (coords[:, 0] > trim) & (coords[:, 0] < 1.0 - trim)
        coords, values = coords[keep], values[keep]
    truth = -exact.topography_top(coords)          # topography_top is -sigma_zz
    order = np.argsort(coords[:, 0])
    got = values[order] - values.mean()
    truth = truth[order] - truth.mean()
    return float(np.linalg.norm(got - truth) / np.linalg.norm(truth))


def leaks(v):
    """max |u_z| / |u| on the top wall, over the soft half and the stiff half.

    Reported separately because one penalty coefficient has to hold both, and
    the two sides do not ask the same thing of it.
    """
    coords = v.coords
    top = np.abs(coords[:, 1] - 1.0) < 1.0e-9
    u = np.squeeze(np.asarray(v.array))
    speed = np.linalg.norm(u, axis=1).max()
    out = []
    for side in (coords[:, 0] < 0.5, coords[:, 0] > 0.5):
        mask = top & side
        out.append(np.abs(u[mask, 1]).max() / speed)
    return out


def measure(mode, **kwargs):
    mesh, stokes, v, exact = build(mode, **kwargs)
    stokes.solve()
    if not converged(stokes):
        return None
    soft, stiff = leaks(v)
    out = {"soft": soft, "stiff": stiff, "velocity": exact.velocity_error(v)}
    coords, values = recovered_traction(mesh, stokes)
    out["recovered"] = stress_error(coords, values, exact)
    out["trimmed"] = stress_error(coords, values, exact, trim=2.0 / kwargs.get("res", RES))
    read = reaction_traction(stokes, mode)
    if read is not None:
        coords, values = read
        # The reaction is the traction holding the wall, opposite in sign to
        # sigma_zz -- the same convention as in stress.py.
        out["reaction"] = stress_error(coords, -np.asarray(values), exact)
    return out


MODES = ("dirichlet", "penalty", "nitsche", "constraint", "rotated")


def sweep(resolutions=(16, 32, 64), modes=MODES):
    print("surface stress error, eta_B/eta_A = %.0e" % ETA_B)
    print()
    print("| elements | " + " | ".join(modes) + " | rotated (reaction) | multiplier |")
    print("|---" * (len(modes) + 3) + "|")
    for res in resolutions:
        row, extra = [], {}
        for mode in modes:
            got = measure(mode, res=res)
            row.append("diverged" if got is None else "%.2e" % got["recovered"])
            if got and "reaction" in got:
                extra[mode] = "%.2e" % got["reaction"]
        print("| %d | %s | %s | %s |"
              % (res, " | ".join(row), extra.get("rotated", "-"),
                 extra.get("constraint", "-")), flush=True)


def contrast(ratios=(1.0e1, 1.0e2, 1.0e3, 1.0e4, 1.0e6), modes=MODES):
    """Does the treatment survive the viscosity jump getting bigger?

    `dirichlet` is the control, and it is the one to read first. It is the
    ordinary component condition a box allows, it holds u.n exactly, and its
    velocity error is 1e-5 at every contrast here -- so whatever it reads in
    the stress column is the RECOVERY's error and not a boundary condition's.
    A treatment can only be said to be worse than the reference where it is
    worse than that.
    """
    print("whole wall / trimmed by two elements at each end")
    print()
    print("| eta_B/eta_A | " + " | ".join(modes) + " |")
    print("|---" * (len(modes) + 1) + "|")
    for ratio in ratios:
        row = []
        for mode in modes:
            got = measure(mode, eta_B=ratio)
            row.append("diverged" if got is None
                       else "%.2e / %.2e" % (got["recovered"], got["trimmed"]))
        print("| %.0e | %s |" % (ratio, " | ".join(row)), flush=True)


def parameters():
    """The leak on each half of the wall, against the parameter.

    A dimensionless gamma carries mu/h with it and so asks the same of both
    halves. A bare penalty coefficient does not, and the stiff half is where
    that shows.
    """
    for mode, values, label in (
            ("penalty", (1e2, 1e4, 1e6, 1e8), "penalty coefficient"),
            ("nitsche", (1.0, 10.0, 100.0, 1000.0), "Nitsche gamma")):
        print("\n%s, eta_B/eta_A = %.0e" % (label, ETA_B))
        print("\n| %s | leak, soft half | leak, stiff half | stress error |" % label)
        print("|---|---|---|---|")
        for value in values:
            kwargs = {"gamma": value} if mode == "nitsche" else {"penalty": value}
            got = measure(mode, **kwargs)
            if got is None:
                print("| %g | diverged | | |" % value)
                continue
            print("| %g | %.2e | %.2e | %.2e |"
                  % (value, got["soft"], got["stiff"], got["recovered"]), flush=True)


def control():
    for mode in ("free", "dirichlet"):
        got = measure(mode)
        if got is None:
            print("%-10s diverged" % mode, flush=True)
            continue
        print("%-10s leak soft %.2e  stiff %.2e   velocity %.2e   stress %.2e"
              % (mode, got["soft"], got["stiff"], got["velocity"],
                 got["recovered"]), flush=True)


if __name__ == "__main__":
    command = sys.argv[1:2] or ["sweep"]
    {"sweep": sweep, "contrast": contrast,
     "params": parameters, "control": control}[command[0]]()
