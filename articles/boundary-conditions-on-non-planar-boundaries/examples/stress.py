"""Does the surface stress come out right?

`leak.py` measures the CONSTRAINT -- how much flow each boundary treatment lets
through. This measures the thing the constraint is wanted for: the wall-normal
stress on the boundary, which is dynamic topography once divided by the
buoyancy scale. Against an exact answer, so it is a measurement rather than a
comparison of two methods that might both be wrong.

The oracle
----------
Kramer, Davies & Wilson (2021) give exact Stokes solutions in a cylindrical
annulus, and their `assess` package publishes the RADIAL STRESS directly --
`radial_stress = tau_rr - p` -- which is the quantity here. Underworld wraps
the package as `uw.analytic.CylindricalStokes`.

The case is the smooth one: density (r/r_o)^k cos(n.theta) driving the flow,
free slip on both radii, viscosity 1. On the outer boundary the exact
sigma_rr is a pure cos(n.theta) (checked, residual 1e-16), so the measurement
is the amplitude of that harmonic and the metric is its relative error.

The inner boundary carries the EXACT velocity as a Dirichlet condition rather
than a free-slip treatment of its own. The exact solution satisfies both, so
the problem is unchanged; what it buys is that the treatment under test is the
only free-slip condition in the model, and that the rigid-rotation nullspace of
two free-slip circles is gone.

What is compared
----------------
Two routes to the surface stress, and the difference between them is the
note's argument:

  * RECOVERED -- project r.sigma.r out of the solved velocity and pressure.
    Available for every treatment, and the only route the weak ones have.
  * REACTION -- the constraint reaction of the rotated method
    (`boundary_normal_traction`), and the multiplier field of the constraint
    method. Not recovered from the solution: an unknown the solve returned.

Both are compared against the same exact amplitude, using the TRUE radial
direction, so no treatment is being scored against its own normal.

Sign: `boundary_normal_traction` and the multiplier both return the constraint
reaction, which is opposite in sign to sigma_rr as `assess` publishes it (it is
the traction that holds the boundary, not the traction the fluid exerts). The
dynamic-topography formula h = -(sigma_nn - mean)/(rho.g) carries the sign
back. Amplitudes are compared unsigned and the sign is printed so the
convention stays visible.

    python3 stress.py sweep       # the refinement table
    python3 stress.py params      # penalty coefficient and Nitsche gamma
    python3 stress.py locking     # the facet normal does not converge
    python3 stress.py control     # the metric fires when the BC is removed

Run against underworld3 `bugfix/multiplier-traction` (PR #617); the
constrained solver's `traction()` is the fix this note prompted.
"""
import sys

import numpy as np
import sympy

import underworld3 as uw

# The boundary trace of a field, selected by the mesh boundary LABEL. An earlier
# version of this comparison selected it by a radius band that narrowed with the
# mesh, which quietly admitted a different node set at each resolution. This is
# the same selector the solver's own reaction recovery uses.
from underworld3.utilities.boundary_flux import _boundary_field_nodes

N = 2            # azimuthal wavenumber of the density anomaly
K = 3            # its radial power
R_I, R_O = 0.5, 1.0
CELL = 0.075
PENALTY = 1.0e4
GAMMA = 10.0


def build(mode, cell=CELL, penalty=PENALTY, gamma=GAMMA):
    """The annulus, the forcing, and one boundary treatment on the outer arc."""
    mesh = uw.meshing.Annulus(radiusInner=R_I, radiusOuter=R_O, cellSize=cell)
    x, y = mesh.X
    r = sympy.sqrt(x**2 + y**2)
    theta = sympy.atan2(y, x)

    v = uw.discretisation.MeshVariable("U", mesh, mesh.dim, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    solver_class = (uw.systems.Stokes_Constrained if mode == "constraint"
                    else uw.systems.Stokes)
    stokes = solver_class(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = 1.0

    # The forcing `assess` solves for: rho = (r/r_o)^k cos(n.theta), gravity
    # inward. This is the convention the Kramer benchmark in underworld3's
    # docs/examples uses, and the velocity error below is what checks it.
    rho = ((r / R_O) ** K) * sympy.cos(N * theta)
    stokes.bodyforce = -rho * sympy.Matrix([[x / r, y / r]])

    exact = uw.analytic.CylindricalStokes(
        mesh, n=N, k=K, r_inner=R_I, r_outer=R_O,
        density="smooth", boundary="free")

    v_exact = uw.discretisation.MeshVariable("Uex", mesh, mesh.dim, degree=2)
    v_exact.data[:] = exact.evaluate("velocity", v_exact.coords)
    stokes.add_dirichlet_bc(v_exact.sym, "Lower")

    if mode == "constraint":
        stokes.add_constraint_bc(0.0, "Upper")
    elif mode == "rotated":
        stokes.add_rotated_freeslip_bc(0.0, "Upper")
    elif mode == "nitsche":
        # Nitsche's default normal is mesh.boundary_normal(boundary) -- the
        # measure-weighted node normal, not the per-facet one.
        stokes.add_nitsche_bc(0.0, "Upper", gamma=gamma, theta=1)
    elif mode == "penalty":
        # The documented direct penalty, with the quadrature-point FACET normal.
        stokes.add_natural_bc(penalty * mesh.Gamma.dot(v.sym) * mesh.Gamma, "Upper")
    elif mode == "penalty_node":
        # The same penalty against the measure-weighted NODE normal. The only
        # difference between this and the line above is which normal, and it is
        # the difference between a method that converges and one that locks.
        node_n = mesh.boundary_normal("Upper")
        stokes.add_natural_bc(penalty * node_n.dot(v.sym) * node_n, "Upper")
    elif mode == "free":
        pass                      # the control: no condition on the outer arc
    else:
        raise ValueError(mode)

    return mesh, stokes, v, exact


def converged(stokes):
    """A diverged solve leaves numbers in the array that look like measurements."""
    return stokes.snes.getConvergedReason() > 0


def exact_amplitude(exact):
    """Amplitude of cos(n.theta) in the exact sigma_rr on the outer boundary.

    Sampled densely on the true circle and least-squares fitted. The residual
    is returned too: it is 1e-16, which is what says the exact surface stress
    really is a single harmonic and the amplitude is the whole of it.
    """
    phi = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    points = np.c_[R_O * np.cos(phi), R_O * np.sin(phi)]
    sigma = np.array([exact._above.radial_stress_cartesian(pt) for pt in points])
    (mean, c, s), residual = _fit(phi, sigma)
    return c, residual


def _fit(angles, values):
    """Least squares fit of a constant plus the degree-N harmonic.

    A least-squares fit rather than a quadrature: boundary nodes are not evenly
    spaced in theta, and on a P2 trace vertices and edge midpoints alternate
    with unequal gaps. Returns ((mean, cos, sin), max residual).
    """
    basis = np.c_[np.ones_like(angles), np.cos(N * angles), np.sin(N * angles)]
    coefficients, *_ = np.linalg.lstsq(basis, values, rcond=None)
    residual = np.abs(values - basis @ coefficients).max()
    return coefficients, residual


def trace(solver, field_id, var, boundary="Upper"):
    """(coords, values) for `var` at the nodes it carries on `boundary`."""
    nodes, *_ = _boundary_field_nodes(solver, boundary, field_id)
    coords = np.array([node[2] for node in nodes])
    tree = uw.kdtree.KDTree(np.ascontiguousarray(var.coords))
    index = np.asarray(tree.query(np.ascontiguousarray(coords), 1)[1]).flatten()
    # squeeze: a MeshVariable's .array carries a middle axis that broadcasts
    # silently against an (N,) index -- see leak.py.
    return coords, np.squeeze(np.asarray(var.array))[index]


def recovered_traction(mesh, stokes):
    """sigma_rr on the outer boundary, projected out of the solved fields.

    The recovery every treatment can do, and the only one the weak forms have.
    Against the TRUE radial direction, which is also the direction the oracle
    publishes, so the comparison does not depend on the solver's normal.
    """
    x, y = mesh.X
    r = sympy.sqrt(x**2 + y**2)
    radial = sympy.Matrix([[x / r, y / r]])
    sigma_rr = (radial * stokes.stress * radial.T)[0, 0]

    field = uw.discretisation.MeshVariable("Srr", mesh, 1, degree=2)
    projection = uw.systems.Projection(mesh, field)
    projection.uw_function = sigma_rr
    projection.solve()
    return trace(projection, 0, field)


# The augmented-Lagrangian parameter this problem gets by default: the base
# (1e4) times the local viscosity, which is 1 here.
AUGMENTATION = 1.0e4


def multiplier_traction(stokes, v, boundary="Upper"):
    """The WHOLE traction a multiplier constraint holds the boundary with.

    The momentum row carries `h + r(u.n - g)`, so `h` alone is short by `r` times
    the discrete constraint residual. `stokes.traction(boundary)` is that sum as
    an expression; this reads it off the node arrays instead, because evaluating
    an expression at points sitting exactly on a convex curved boundary
    extrapolates from the containing cell (underworld3#605) and that error would
    land on top of the measurement.

    `u.n` is taken against the true radial direction rather than the constraint's
    node normal. The two differ at O(h^2) and they multiply a term that is itself
    a correction.
    """
    coords, h = trace(stokes, 2, stokes.multiplier(boundary))
    tree = uw.kdtree.KDTree(np.ascontiguousarray(v.coords))
    index = np.asarray(tree.query(np.ascontiguousarray(coords), 1)[1]).flatten()
    u = np.squeeze(np.asarray(v.array))[index]
    normal = coords / np.linalg.norm(coords, axis=1)[:, None]
    return coords, np.asarray(h) + AUGMENTATION * (u * normal).sum(axis=1)


def reaction_traction(stokes, mode, v=None):
    """The constraint reaction, for the two methods that return one."""
    if mode == "rotated":
        return stokes.boundary_normal_traction("Upper")
    if mode == "constraint":
        return multiplier_traction(stokes, v)
    return None


def amplitude_error(coords, values, reference):
    """Relative error in the harmonic amplitude, unsigned, and the sign."""
    angles = np.arctan2(coords[:, 1], coords[:, 0])
    (_mean, c, _s), _residual = _fit(angles, values)
    return abs(abs(c) - abs(reference)) / abs(reference), np.sign(c)


def split(coords):
    """Vertices from edge midpoints. A vertex of the annulus mesh sits exactly
    on the circle; a P2 edge midpoint sits on the chord, inside it by the
    sagitta. They are not interchangeable: vertex values of sigma_nn carry the
    O(h) facet-geometry error and midpoint values are superconvergent
    (underworld3#414)."""
    on_circle = np.abs(np.linalg.norm(coords, axis=1) - R_O) < 1.0e-9
    return {"vertex": on_circle, "midpoint": ~on_circle}


def leak(v):
    """max |u.n| on the outer boundary against the TRUE radial direction,
    normalised by the flow speed -- the measurement leak.py tabulates."""
    coords = v.coords
    radius = np.linalg.norm(coords, axis=1)
    outer = np.abs(radius - R_O) < 1.0e-6
    u = np.squeeze(np.asarray(v.array))
    normal = coords[outer] / radius[outer][:, None]
    return np.abs((u[outer] * normal).sum(axis=1)).max() / np.linalg.norm(u, axis=1).max()


def measure(mode, cell=CELL, **kwargs):
    """One solve, and everything read off it."""
    mesh, stokes, v, exact = build(mode, cell=cell, **kwargs)
    stokes.solve()
    if not converged(stokes):
        return None
    reference, _residual = exact_amplitude(exact)
    out = {
        "leak": leak(v),
        "velocity": exact.error("velocity", v),
        "exact": reference,
    }
    coords, values = recovered_traction(mesh, stokes)
    out["recovered"], out["sign"] = amplitude_error(coords, values, reference)
    read = reaction_traction(stokes, mode, v=v)
    if read is not None:
        coords, values = read
        out["reaction"], out["reaction_sign"] = amplitude_error(coords, values, reference)
        for name, mask in split(coords).items():
            out["reaction_" + name] = amplitude_error(
                coords[mask], values[mask], reference)[0]
    return out


MODES = ("penalty", "penalty_node", "nitsche", "constraint", "rotated")


def sweep(cells=(0.15, 0.10, 0.075, 0.05), modes=MODES):
    """Does the surface stress converge to the exact one, and how fast?"""
    exact, residual = exact_amplitude(build("free", cell=0.2)[3])
    print("exact sigma_rr on r = %.2f:  %.10f cos(%d.theta), residual %.1e"
          % (R_O, exact, N, residual))
    print()
    print("relative error in the surface stress amplitude")
    print()
    print("| cell size | " + " | ".join(modes) + " | rotated (reaction) | multiplier |")
    print("|---" * (len(modes) + 3) + "|")
    for cell in cells:
        row, extra = [], {}
        for mode in modes:
            got = measure(mode, cell=cell)
            row.append("diverged" if got is None else "%.2e" % got["recovered"])
            if got and "reaction" in got:
                extra[mode] = "%.2e" % got["reaction"]
        print("| %.3f | %s | %s | %s |"
              % (cell, " | ".join(row),
                 extra.get("rotated", "-"), extra.get("constraint", "-")), flush=True)


def parameters(cell=CELL):
    """The two weak methods against their own parameter, with the leak beside
    the stress -- which is where they part company."""
    for mode, values, label in (
            ("penalty", (1e3, 1e4, 1e5, 1e6, 1e8), "penalty (facet normal)"),
            ("penalty_node", (1e3, 1e4, 1e5, 1e6), "penalty (node normal)"),
            ("nitsche", (1.0, 10.0, 100.0, 1000.0, 1e4), "Nitsche gamma")):
        print("\n%s, cell %.3f" % (label, cell))
        print("\n| %s | leak | velocity error | stress error |"
              % ("gamma" if mode == "nitsche" else "coefficient"))
        print("|---|---|---|---|")
        for value in values:
            kwargs = {"gamma": value} if mode == "nitsche" else {"penalty": value}
            got = measure(mode, cell=cell, **kwargs)
            if got is None:
                print("| %g | diverged | | |" % value)
                continue
            print("| %g | %.2e | %.2e | %.2e |"
                  % (value, got["leak"], got["velocity"], got["recovered"]), flush=True)


def locking(cells=(0.15, 0.10, 0.075, 0.05, 0.035), penalty=1.0e6):
    """The facet normal, pushed hard, does not converge to free slip.

    Imposing u.n = 0 facet by facet on a curved boundary constrains a corner
    node in two directions at once, and the discrete limit is not the smooth
    problem. Refine it and it stays wrong -- while the leak, which is the
    metric that would normally be trusted, reads 1e-5.
    """
    print("direct penalty at %.0e, against the FACET normal" % penalty)
    print("\n| cell size | leak | velocity error | stress error |")
    print("|---|---|---|---|")
    for cell in cells:
        got = measure("penalty", cell=cell, penalty=penalty)
        if got is None:
            print("| %.3f | diverged | | |" % cell)
            continue
        print("| %.3f | %.2e | %.2e | %.2e |"
              % (cell, got["leak"], got["velocity"], got["recovered"]), flush=True)
    print("\nthe same coefficient against the measure-weighted NODE normal")
    print("\n| cell size | leak | velocity error | stress error |")
    print("|---|---|---|---|")
    for cell in cells:
        got = measure("penalty_node", cell=cell, penalty=penalty)
        if got is None:
            print("| %.3f | diverged | | |" % cell)
            continue
        print("| %.3f | %.2e | %.2e | %.2e |"
              % (cell, got["leak"], got["velocity"], got["recovered"]), flush=True)


def control(cell=CELL):
    """Take the boundary condition away. A metric that cannot see that is not
    measuring anything."""
    for mode in ("free", "rotated"):
        got = measure(mode, cell=cell)
        print("%-9s leak %.2e   velocity error %.2e   stress error %.2e"
              % (mode, got["leak"], got["velocity"], got["recovered"]), flush=True)


if __name__ == "__main__":
    command = sys.argv[1:2] or ["sweep"]
    {"sweep": sweep, "params": parameters,
     "locking": locking, "control": control}[command[0]]()
