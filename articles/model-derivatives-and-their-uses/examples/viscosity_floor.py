# %% [markdown]
# # How low should the viscosity floor go?
#
# A viscoplastic layer is shortened between two walls, with a weakened seed at
# the middle of its base. Two shear bands rise from the seed to the free
# surface, and the wedge between them is pushed up. The viscosity of yielded
# material is the yield stress over twice the strain rate, which has no lower
# bound, so the solve carries a floor, $\eta_{\min}$: a parameter that is
# there for the solver, not the physics.
#
# The floor is lowered in steps, each solve warm-started from the one before.
# At each floor, one adjoint solve per prediction gives the derivative of that
# prediction with respect to $\eta_{\min}$, through
# `stokes.gradient(J, parameters=[eta_min])`. While the derivative is large,
# lowering the floor changes the answer; once it is small, the floor has
# stopped mattering and there is nothing to gain by lowering it further.
#
# The run writes `viscosity_floor_<cell size>.json`: for each floor, the
# Newton iterations, both predictions, and their derivatives.

# %%
import json
import time

import numpy as np
import sympy

import underworld3 as uw

# %% [markdown]
# ### Configurable parameters
#
# Override them with PETSc-style flags:
#
# ```bash
# python viscosity_floor.py -uw_cell_size 0.025
# python viscosity_floor.py -uw_floors 0.1,0.01,0.001
# ```
#
# The problem is stated in units of the layer's thickness, its viscosity, and
# the rate at which each wall closes, so the box is $4 \times 1$, the
# viscosity is one, and the viscous stress of the bulk shortening is about
# one. The yield stress is half that, so the layer must yield to shorten at
# all, and the seed decides where.

# %%
CELL_SIZE = 0.05             # base mesh; refined once, so half this
YIELD_STRESS = 0.5           # von Mises, against a viscous stress of about one
SEED_WEAKENING = 0.9         # the seed's yield stress is (1 - this) of the rest
SEED_WIDTH = 0.05            # Gaussian width of the seed
FLOORS = ("0.5,0.3,0.2,0.1,0.07,0.05,0.03,0.02,0.015,0.01,0.007,0.005,"
          "0.003,0.002,0.0015,0.001,0.0007,0.0005,0.0003,0.0002,0.0001")
FD_FLOOR = 0.01              # where the adjoint is checked against differences
TOLERANCE = 1e-6

params = uw.Params(
    uw_cell_size=uw.Param(CELL_SIZE, description="base mesh cell size"),
    uw_yield_stress=uw.Param(YIELD_STRESS, description="von Mises yield stress"),
    uw_seed_weakening=uw.Param(SEED_WEAKENING, description="fractional weakening at the seed"),
    uw_seed_width=uw.Param(SEED_WIDTH, description="Gaussian width of the seed"),
    uw_floors=uw.Param(FLOORS, description="viscosity floors, highest first"),
    uw_fd_floor=uw.Param(FD_FLOOR, description="floor for the finite-difference check; 0 for none"),
    uw_tolerance=uw.Param(TOLERANCE, description="nonlinear solver tolerance"),
)
floors = [float(f) for f in str(params.uw_floors).split(",")]

# %% [markdown]
# ## The layer
#
# Refined once from the base cell size, which gives the velocity block a
# multigrid hierarchy. The walls close at unit rate and are free to slip; the
# base is free-slip and the top is free, so the surface velocity is the uplift
# rate.

# %%
cell = float(params.uw_cell_size)
mesh = uw.meshing.UnstructuredSimplexBox(minCoords=(0.0, 0.0), maxCoords=(4.0, 1.0),
                                         cellSize=cell, refinement=1, qdegree=3)
x, y = mesh.X
v = uw.discretisation.MeshVariable("v", mesh, mesh.dim, degree=2)
p = uw.discretisation.MeshVariable("p", mesh, 1, degree=1, continuous=True)
eta_cell = uw.discretisation.MeshVariable("eta_cell", mesh, 1, degree=0, continuous=False)   # for the figure

stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
stokes.add_essential_bc((1.0, None), "Left")
stokes.add_essential_bc((-1.0, None), "Right")
stokes.add_essential_bc((None, 0.0), "Bottom")
stokes.bodyforce = sympy.Matrix([0.0, 0.0])

# %% [markdown]
# ## The rheology and its floor
#
# `ViscoPlasticFlowModel` combines the viscosity with the yield viscosity
# $\tau_y / 2\dot\varepsilon_{II}$ by a smooth minimum, and bounds the result
# below by `shear_viscosity_min`, rounded over a tenth of the floor. The floor
# is a named expression in the residual, so the solver can differentiate with
# respect to it. The yield stress is positive everywhere, so its own cutoff at
# zero is switched off.

# %%
seed = sympy.exp(-((x - 2.0) ** 2 + y ** 2) / (2 * float(params.uw_seed_width) ** 2))

stokes.constitutive_model = uw.constitutive_models.ViscoPlasticFlowModel
model = stokes.constitutive_model
model.Parameters.shear_viscosity_0 = 1.0
model.Parameters.yield_stress = float(params.uw_yield_stress) * (1 - float(params.uw_seed_weakening) * seed)
model.Parameters.yield_stress_min = -sympy.oo
model.Parameters.shear_viscosity_min = floors[0]
eta_min = model.Parameters.shear_viscosity_min      # its symbol in the residual

stokes.preconditioner = "fmg"
stokes.tolerance = float(params.uw_tolerance)
stokes.petsc_options["snes_max_it"] = 120

# %% [markdown]
# ## Two predictions
#
# The rate of work the walls do, $\int \tau : \dot\varepsilon$, which is the
# layer's strength at this rate of shortening; and the uplift, through
# $\int v_y^2/2$ along the top, which grows as the uplift concentrates in the
# wedge (its plain integral is fixed by the shortening). Each is an integrand
# over the mesh, the form `gradient()` takes.

# %%
E = stokes.strainrate
work_rate = 2 * model.viscosity * (E * E.T).trace()
predictions = {
    "work": {None: work_rate},
    "uplift": {"Top": v.sym[1] ** 2 / 2},
}

# %% [markdown]
# ## Lowering the floor
#
# The first floor is solved from rest, and each lower one from the solution
# above it. At each floor the forward solve is followed by one adjoint solve
# per prediction. The logarithmic sensitivity
# $S = \mathrm d\ln J / \mathrm d\ln\eta_{\min}$ is the fractional change in the
# prediction for a fractional change in the floor.

# %%
rows = []
for i, floor in enumerate(floors):
    model.Parameters.shear_viscosity_min = floor
    t0 = time.time()
    stokes.solve(zero_init_guess=(i == 0))
    row = dict(floor=floor, newton=int(stokes.snes.getIterationNumber()),
               reason=int(stokes.snes.getConvergedReason()), seconds=round(time.time() - t0, 1))
    for name, J in predictions.items():
        out = stokes.gradient(J, parameters=[eta_min])
        dJ = out["parameters"][eta_min]
        row[name] = dict(J=out["J"], dJ=dJ, S=floor * dJ / out["J"])
    rows.append(row)
    print(f"floor {floor:8.2g}  Newton {row['newton']:3d}  "
          f"S(work) {row['work']['S']:9.2e}  S(uplift) {row['uplift']['S']:9.2e}", flush=True)

# %% [markdown]
# The state at the lowest floor, sampled on a grid for the figure: the
# effective viscosity, which shows the bands, and the velocity. The viscosity
# is projected onto one value per cell first, the cell's mean of the law at
# its quadrature points, so the sample stays between the floor and one.

# %%
to_cells = uw.systems.Projection(mesh, eta_cell)
to_cells.uw_function = model.viscosity
to_cells.smoothing = 0.0
to_cells.solve()
gx, gy = np.meshgrid(np.linspace(0, 4, 321), np.linspace(0, 1, 81))
grid = np.column_stack([gx.ravel(), gy.ravel()])
eta_grid = np.asarray(uw.function.evaluate(eta_cell.sym[0], grid)).reshape(gx.shape)
v_grid = np.asarray(uw.function.evaluate(v.sym, grid)).reshape(gx.shape + (2,))
np.savez_compressed(f"viscosity_floor_{cell:g}_fields.npz", x=gx[0], y=gy[:, 0],
                    eta=eta_grid.astype(np.float32), v=v_grid.astype(np.float32), floor=floors[-1])

# %% [markdown]
# ## The check
#
# Central differences in the floor, about the converged solution at
# `uw_fd_floor`, against the adjoint derivative there.

# %%
check = None
fd_floor = float(params.uw_fd_floor)
if fd_floor > 0:
    model.Parameters.shear_viscosity_min = fd_floor
    stokes.solve(zero_init_guess=False)
    base = (np.array(v.array), np.array(p.array))
    adjoint = stokes.gradient(predictions["work"], parameters=[eta_min])["parameters"][eta_min]
    h = 1e-3 * fd_floor
    values = []
    for sign in (+1, -1):
        v.array[...], p.array[...] = base
        model.Parameters.shear_viscosity_min = fd_floor + sign * h
        stokes.solve(zero_init_guess=False)
        values.append(uw.adjoint.integral(mesh, work_rate))
    difference = (values[0] - values[1]) / (2 * h)
    check = dict(floor=fd_floor, adjoint=adjoint, difference=difference)
    print(f"at floor {fd_floor:g}: adjoint {adjoint:.8e}  differences {difference:.8e}")

# %%
with open(f"viscosity_floor_{cell:g}.json", "w") as f:
    json.dump(dict(cell_size=cell, h=cell / 2, yield_stress=float(params.uw_yield_stress),
                   rows=rows, check=check), f, indent=1)
