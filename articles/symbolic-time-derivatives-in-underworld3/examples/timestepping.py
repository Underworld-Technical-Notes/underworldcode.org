#!/usr/bin/env python3
"""One field, three time derivatives, the same answer.

A Gaussian blob of temperature is carried once across a periodic-in-effect
box by a uniform wind while it diffuses. The exact answer is known -- a
Gaussian advects rigidly and spreads as sqrt(4 k t) -- so each scheme can be
scored against it rather than against the others.

The point is that the SOLVER is the same in all three runs. Only the history
manager changes, and with it whether transport is assembled implicitly in the
residual (Eulerian SUPG), traced along characteristics (semi-Lagrangian), or
corrected explicitly on the mesh (Eulerian).

Dimensional throughout: metres, seconds, kelvin. The Courant number is set
deliberately above 1 for the last run, which is where the schemes part company.

Usage:
    python3 timestepping.py                    # all three, default resolution
    python3 timestepping.py -uw_cells 48       # finer
    python3 timestepping.py -uw_courant 2.0    # push past the CFL limit
"""

import numpy as np
import sympy

import underworld3 as uw

params = uw.Params(
    cells=uw.Param(32, "cells across the box"),
    courant=uw.Param(0.5, "Courant number: |v| dt / h"),
    steps=uw.Param(20, "timesteps"),
)

# --- the physical problem, in units -----------------------------------------
L = uw.quantity(1.0e6, "m")            # box side, 1000 km
V = uw.quantity(1.0e-9, "m/s")         # wind, ~3 cm/yr
KAPPA = uw.quantity(1.0e-6, "m**2/s")  # thermal diffusivity of rock
T0 = uw.quantity(100.0, "K")           # blob amplitude
WIDTH = 0.08                           # blob sigma, as a fraction of L

CELLS = int(params.cells)
h = L / CELLS
dt = float(params.courant) * h / V     # a time, in seconds


def gaussian(x, y, cx, cy, sigma):
    """The exact blob: amplitude T0, centre (cx, cy), width sigma."""
    r2 = (x - cx) ** 2 + (y - cy) ** 2
    return float(T0.magnitude) * np.exp(-r2 / (2.0 * sigma ** 2))


def run(flavour):
    """Advect and diffuse the blob for `steps`, return the L2 error."""
    mesh = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0),
        cellSize=1.0 / CELLS, qdegree=3)
    T = uw.discretisation.MeshVariable("T", mesh, 1, degree=2)
    x, y = mesh.X

    # non-dimensional velocity on a unit box: the scaling is L for length and
    # L/V for time, so the wind is 1 and the diffusivity is 1/Peclet
    peclet = float((V * L / KAPPA).magnitude)
    v_fn = sympy.Matrix([[1.0, 0.0]])          # unit wind, +x

    sigma = WIDTH
    x0, y0 = 0.25, 0.5
    T.array[:, 0, 0] = gaussian(np.asarray(T.coords)[:, 0],
                                np.asarray(T.coords)[:, 1], x0, y0, sigma)

    if flavour == "supg":
        solver = uw.systems.AdvDiffusion(mesh, u_Field=T, V_fn=v_fn)
    elif flavour == "slcn":
        solver = uw.systems.AdvDiffusionSLCN(mesh, u_Field=T, V_fn=v_fn)
    elif flavour == "eulerian":
        DTdt = uw.systems.Eulerian_DDt(
            mesh, T, vtype=uw.VarType.SCALAR, degree=T.degree,
            continuous=True, order=1)
        solver = uw.systems.AdvDiffusion(mesh, u_Field=T, V_fn=v_fn,
                                         DuDt=DTdt, order=1)
    else:
        raise ValueError(flavour)

    solver.constitutive_model = uw.constitutive_models.DiffusionModel
    solver.constitutive_model.Parameters.diffusivity = 1.0 / peclet
    for wall in ("Bottom", "Top", "Left", "Right"):
        solver.add_dirichlet_bc(0.0, wall)

    dt_nd = float(params.courant) / CELLS      # |v|=1 on the unit box
    n = int(params.steps)
    for _step in range(n):
        solver.solve(timestep=dt_nd)

    # the exact blob: advected by v*t, spread by the diffusion it has seen
    t_end = n * dt_nd
    spread = np.sqrt(sigma ** 2 + 2.0 * t_end / peclet)
    amp = float(T0.magnitude) * sigma ** 2 / spread ** 2
    coords = np.asarray(T.coords)
    exact = amp * np.exp(
        -((coords[:, 0] - (x0 + t_end)) ** 2 + (coords[:, 1] - y0) ** 2)
        / (2.0 * spread ** 2))
    got = T.array[:, 0, 0]
    return float(np.sqrt(np.mean((got - exact) ** 2)) / float(T0.magnitude))


if __name__ == "__main__":
    uw.pprint(f"box {L}, wind {V}, diffusivity {KAPPA}")
    uw.pprint(f"{CELLS} cells, Courant {float(params.courant):g}, "
              f"dt {dt.to('year')}, {int(params.steps)} steps\n")
    have_supg = hasattr(uw.systems.ddt, "EulerianSUPG")
    uw.pprint(f"  {'manager':<24} {'relative L2 error':>18}")
    for flavour, name in (("supg", "Eulerian SUPG (default)"),
                          ("slcn", "Semi-Lagrangian"),
                          ("eulerian", "Eulerian")):
        if flavour == "supg" and not have_supg:
            uw.pprint(f"  {name:<24} {'needs the release that':>18}")
            uw.pprint(f"  {'':<24} {'ships EulerianSUPG':>18}")
            continue
        uw.pprint(f"  {name:<24} {run(flavour):>18.4f}")
