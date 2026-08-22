"""SolCx in a rotated frame: an exact solution on walls that are not axis-aligned.

`solcx.py` runs SolCx on the unit box, where "no flow through the top wall" is a
single velocity component and every treatment reduces to the same constraint.
That is deliberate -- it isolates the viscosity contrast from the geometry -- but
it also means the box says nothing about normals.

This rotates the whole problem instead. The mesh is turned through THETA, and the
viscosity, the forcing and the exact solution are turned with it, so the physics
is identical and no wall is aligned with a coordinate direction. The exact
solution is still SolCx's, read at the pre-image of each point.

With x the rotated coordinate and xi = R^T x the material coordinate,

    eta(x)   = eta_solcx(xi)
    f(x)     = R f_solcx(xi)
    u(x)     = R u_solcx(xi)
    sigma(x) = R sigma_solcx(xi) R^T

and because sigma_nn is frame-invariant, the surface stress on the rotated top
wall is exactly sigma_zz of the unrotated solution at the pre-image. Nothing has
to be un-rotated to make the comparison.

Every wall carries the treatment under test: a component Dirichlet condition
cannot express u.n = 0 on a wall at 45 degrees, which is the point. The corners
are where two walls meet, and there both constraints apply -- u.n = 0 against two
orthogonal normals, which fixes the node at zero. That is what the exact solution
says a free-slip corner does, so it is a constraint and not a choice.

    python3 solcx_rotated.py            # every treatment, at THETA
    python3 solcx_rotated.py angles     # the rotated constraint against the angle

Run against underworld3 `bugfix/multiplier-traction` (PR #617).
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
THETA = np.pi / 4.0
WALLS = ("Left", "Right", "Bottom", "Top")


def rotation(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def build(mode, res=RES, eta_B=ETA_B, penalty=PENALTY, gamma=GAMMA, theta=THETA):
    """The rotated problem, and one boundary treatment on every wall."""
    mesh = uw.meshing.StructuredQuadBox(
        elementRes=(res, res), minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), qdegree=3)

    R = rotation(theta)
    mesh.deform(np.asarray(mesh.X.coords) @ R.T)

    v = uw.discretisation.MeshVariable("U", mesh, mesh.dim, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    solver_class = (uw.systems.Stokes_Constrained if mode == "constraint"
                    else uw.systems.Stokes)
    stokes = solver_class(mesh, velocityField=v, pressureField=p)

    # Built on the rotated mesh, but only for its SYMBOLS: every expression below
    # is composed with xi = R^T x before it is used, which is what turns the
    # solution with the mesh.
    exact = uw.analytic.SolCx(mesh, eta_A=1.0, eta_B=eta_B, x_c=0.5, n=1)
    x, z = mesh.X
    c, s = sympy.cos(theta), sympy.sin(theta)
    material = {x: c * x + s * z, z: -s * x + c * z}          # xi = R^T x
    Rs = sympy.Matrix([[c, -s], [s, c]])

    def turn(expr):
        """An expression of the material coordinate, written in the rotated one."""
        return expr.subs(material, simultaneous=True)

    fn_viscosity = turn(exact.fn_viscosity)
    fn_bodyforce = (Rs * turn(exact.fn_bodyforce).T).T
    fn_velocity = (Rs * turn(sympy.Matrix(exact.fn_velocity)).reshape(2, 1)).T
    # sigma_nn is invariant, so the exact surface stress on the rotated top wall
    # is the unrotated sigma_zz at the pre-image -- no rotation of the stress.
    fn_sigma_nn = turn(exact.fn_stress[1, 1])

    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = fn_viscosity
    if mode != "constraint":
        stokes.saddle_preconditioner = 1.0 / fn_viscosity
    stokes.bodyforce = fn_bodyforce
    stokes.tolerance = 1.0e-9
    stokes.petsc_use_pressure_nullspace = True

    if mode == "aligned":
        # The NEGATIVE CONTROL, and the reason the rotated run means anything:
        # the condition the unrotated box would use, imposed unchanged on walls
        # that have been turned. It pins the wrong component of the velocity at
        # every boundary node, so if the rotation matrix were quietly the
        # identity somewhere in the machinery, this is the answer we would get.
        stokes.add_dirichlet_bc((0.0, None), "Left")
        stokes.add_dirichlet_bc((0.0, None), "Right")
        stokes.add_dirichlet_bc((None, 0.0), "Bottom")
        stokes.add_dirichlet_bc((None, 0.0), "Top")
        return mesh, stokes, v, dict(velocity=fn_velocity, sigma_nn=fn_sigma_nn,
                                     viscosity=fn_viscosity, R=R, theta=theta)

    for wall in WALLS:
        if mode == "rotated":
            stokes.add_rotated_freeslip_bc(0.0, wall)
        elif mode == "constraint":
            stokes.add_constraint_bc(0.0, wall)
        elif mode == "nitsche":
            stokes.add_nitsche_bc(0.0, wall, gamma=gamma, theta=1)
        elif mode == "penalty":
            n = mesh.boundary_normal(wall)
            stokes.add_natural_bc(penalty * n.dot(v.sym) * n, wall)
        else:
            raise ValueError(mode)

    return mesh, stokes, v, dict(velocity=fn_velocity, sigma_nn=fn_sigma_nn,
                                 viscosity=fn_viscosity, R=R, theta=theta)


def converged(stokes):
    return stokes.snes.getConvergedReason() > 0


def velocity_error(v, truth):
    got = np.squeeze(np.asarray(v.array))
    want = np.asarray(uw.function.evaluate(truth["velocity"], v.coords)).reshape(got.shape)
    return float(np.linalg.norm(got - want) / np.linalg.norm(want))


def leak(v, mesh, theta=THETA):
    """max |u.n| / |u| on the rotated top wall, against the TRUE wall normal."""
    n = rotation(theta) @ np.array([0.0, 1.0])
    coords = np.asarray(v.coords)
    material = coords @ rotation(theta)                      # xi = R^T x
    top = np.abs(material[:, 1] - 1.0) < 1.0e-9
    u = np.squeeze(np.asarray(v.array))
    return float(np.abs(u[top] @ n).max() / np.linalg.norm(u, axis=1).max())


def corner_speed(v, theta=THETA):
    """|u| at the four corners, which two free-slip walls fix at zero."""
    coords = np.asarray(v.coords)
    material = coords @ rotation(theta)
    u = np.squeeze(np.asarray(v.array))
    corner = ((np.abs(material[:, 0] - 0.0) < 1.0e-9) | (np.abs(material[:, 0] - 1.0) < 1.0e-9)) \
        & ((np.abs(material[:, 1] - 0.0) < 1.0e-9) | (np.abs(material[:, 1] - 1.0) < 1.0e-9))
    if not corner.any():
        return float("nan")
    return float(np.linalg.norm(u[corner], axis=1).max() / np.linalg.norm(u, axis=1).max())


def trace_top(solver, mesh, theta=THETA):
    """Velocity-degree nodes on the rotated top wall."""
    nodes, *_ = _boundary_field_nodes(solver, "Top", 0)
    return np.array([node[2] for node in nodes])


def stress_error(coords, values, truth, trim=0.0, theta=THETA):
    """Relative l2 error in sigma_nn along the rotated top wall, mean removed."""
    coords = np.asarray(coords)
    values = np.asarray(values).reshape(-1)
    material = coords @ rotation(theta)
    if trim > 0.0:
        keep = (material[:, 0] > trim) & (material[:, 0] < 1.0 - trim)
        coords, values, material = coords[keep], values[keep], material[keep]
    want = np.asarray(uw.function.evaluate(truth["sigma_nn"], coords)).reshape(-1)
    order = np.argsort(material[:, 0])
    got = values[order] - values.mean()
    want = want[order] - want.mean()
    return float(np.linalg.norm(got - want) / np.linalg.norm(want))


def recovered_sigma_nn(mesh, stokes, theta=THETA):
    """sigma_nn on the rotated top wall, projected out of the solved fields."""
    n = rotation(theta) @ np.array([0.0, 1.0])
    normal = sympy.Matrix([[n[0], n[1]]])
    field = uw.discretisation.MeshVariable("Snn", mesh, 1, degree=2)
    projection = uw.systems.Projection(mesh, field)
    projection.uw_function = (normal * stokes.stress * normal.T)[0, 0]
    projection.solve()
    coords = trace_top(projection, mesh, theta)
    tree = uw.kdtree.KDTree(np.ascontiguousarray(field.coords))
    index = np.asarray(tree.query(np.ascontiguousarray(coords), 1)[1]).flatten()
    return coords, np.squeeze(np.asarray(field.array))[index]


def reaction_sigma_nn(mesh, stokes, v, mode, penalty=PENALTY, theta=THETA):
    """The traction the solve already has, for the three treatments that have one."""
    n = rotation(theta) @ np.array([0.0, 1.0])
    if mode == "rotated":
        coords, values = stokes.boundary_normal_traction("Top")
        return coords, -np.asarray(values)
    if mode == "constraint":
        coords = trace_top(stokes, mesh, theta)
        return coords, -np.asarray(
            uw.function.evaluate(stokes.traction("Top"), coords)).reshape(-1)
    if mode == "penalty":
        coords = trace_top(stokes, mesh, theta)
        tree = uw.kdtree.KDTree(np.ascontiguousarray(v.coords))
        index = np.asarray(tree.query(np.ascontiguousarray(coords), 1)[1]).flatten()
        u = np.squeeze(np.asarray(v.array))[index]
        return coords, -penalty * (u @ n)
    return None


MODES = ("rotated", "constraint", "penalty", "nitsche", "aligned")


def measure(mode, **kwargs):
    mesh, stokes, v, truth = build(mode, **kwargs)
    stokes.solve()
    if not converged(stokes):
        return None
    theta = kwargs.get("theta", THETA)
    out = {
        "leak": leak(v, mesh, theta),
        "corner": corner_speed(v, theta),
        "velocity": velocity_error(v, truth),
    }
    coords, values = recovered_sigma_nn(mesh, stokes, theta)
    out["recovered"] = stress_error(coords, values, truth, theta=theta)
    read = reaction_sigma_nn(mesh, stokes, v, mode,
                             penalty=kwargs.get("penalty", PENALTY), theta=theta)
    if read is not None:
        coords, values = read
        out["reaction"] = stress_error(coords, values, truth, theta=theta)
        # Two elements off each end. A corner node belongs to two walls, and the
        # measure-weighted normal there is the bisector of two orthogonal ones,
        # so u.n at a corner is not the quantity either wall asked for.
        out["reaction_trimmed"] = stress_error(
            coords, values, truth, trim=2.0 / kwargs.get("res", RES), theta=theta)
    return out


def table(modes=MODES, **kwargs):
    print("SolCx rotated through %.1f degrees, %d x %d."
          % (np.degrees(kwargs.get("theta", THETA)), RES, RES))
    print()
    print("| treatment | leak | corner |u| | velocity | sigma_nn, recovered | sigma_nn, from the solve |")
    print("|---|---|---|---|---|---|")
    for mode in modes:
        got = measure(mode, **kwargs)
        if got is None:
            print("| %s | did not converge | | | | |" % mode, flush=True)
            continue
        print("| %s | %.1e | %.1e | %.2e | %.3f | %s |"
              % (mode, got["leak"], got["corner"], got["velocity"], got["recovered"],
                 "%.3f" % got["reaction"] if "reaction" in got else "—"), flush=True)


def angles(degrees=(0.0, 15.0, 30.0, 45.0), mode="rotated"):
    print("%s, against the angle of the frame" % mode)
    print()
    print("| degrees | leak | velocity | sigma_nn, from the solve |")
    print("|---|---|---|---|")
    for d in degrees:
        got = measure(mode, theta=np.radians(d))
        if got is None:
            print("| %.0f | did not converge | | |" % d, flush=True)
            continue
        print("| %.0f | %.1e | %.2e | %s |"
              % (d, got["leak"], got["velocity"],
                 "%.3f" % got["reaction"] if "reaction" in got else "—"), flush=True)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "table"
    {"table": table, "angles": angles}[command]()
