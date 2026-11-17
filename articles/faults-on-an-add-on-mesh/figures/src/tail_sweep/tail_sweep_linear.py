"""Band-ratio sweep of the multigrid hierarchy under the finest ladder, problem A:
the note's linear fixture.

Non-dimensional: unit box, unit viscosity, simple shear v = (y - 1/2, 0) on every
wall, a straight frictionless fault (add_fault_bc) from (0.30, 0.45) to (0.70, 0.55).
The base is UnstructuredSimplexBox(cellSize=1/8, refinement=2), so h_b = 1/32. The
solver mesh is the S ladder placed in a copy of the base's finest level; only the
multigrid levels under it change between arms:

    H0   all base levels welded, then S
    H1   the lean chain (production): base_levels[:-2] + [4S in base_levels[-2],
         2S in base_levels[-1]]
    H2   graded chain in copies of the finest: all base levels welded, then 2^J S ...
         4S, 2S, all in base_levels[-1]; J is the smallest j with h_b / (2^j S) <= 4
    H1c  H1 with every band 2S wide (bands not widened)
    H3   hybrid: the lean chain, then graded levels in the finest copy down to a ratio
         of 4: base_levels[:-2] + [4S in base_levels[-2]] + [2^J S ... 2S in
         base_levels[-1]] (J >= 2)

Every kS ladder is 2kS wide (square cells) except in H1c, the coarser ladders take
every 2^j-th spine point, and the spine count is a multiple of 8.

    mpirun -np 4 python tail_sweep_linear.py -uw_n_rungs 160 -uw_hier H1 -uw_out records/A_r160_H1_np4.json
"""
import json
import os
import time

import numpy as np
import underworld3 as uw
from petsc4py import PETSc
from underworld3.utilities.custom_mg import set_custom_fmg
from underworld3.utilities.fault_contact import fault_slip
from underworld3.utilities.place_surface import place_fault_ribbon_2d

params = uw.Params(
    uw_n_rungs=80,            # spine intervals at S (a multiple of 8): 80, 160, 320
    uw_hier="H1",             # H0, H1, H2, H1c or H3
    uw_tol=1.0e-6,            # Stokes solver tolerance (the note's iterations.png)
    uw_out="records/A.json",  # the JSON record
    uw_fac_lu=0,              # 1: the FAC patch blocks solved by LU, as custom_mg intends
)

if int(params.uw_fac_lu):
    # The FAC block solver as custom_mg writes it (LU, shift nonzero). On the rotated
    # path the keys are dropped from the options DB after the level smoother's setUp,
    # but a composite smoother sets up its ASM child lazily, at first application, so
    # the blocks read no keys and run PCASM's default ILU(0). Keeping the block keys in
    # the DB (the per-solve prefix is unique, so nothing else reads them) lets them apply.
    from underworld3.utilities import custom_mg as _custom_mg
    _configure_pcmg = _custom_mg._configure_pcmg

    def _keep_block_keys(*args, **kwargs):
        return [key for key in _configure_pcmg(*args, **kwargs) if "_sub_1_sub_" not in key]

    _custom_mg._configure_pcmg = _keep_block_keys

FAULT = "Fault"
A, B = np.array([0.30, 0.45]), np.array([0.70, 0.55])
H_B = 1.0 / 32
n = int(params.uw_n_rungs)
assert n % 8 == 0, "the spine count must be a multiple of 8"
L = float(np.linalg.norm(B - A))
S = L / n
trace = A + (np.arange(n + 1) * S)[:, None] * (B - A) / L

wall = time.perf_counter()
base = uw.meshing.UnstructuredSimplexBox(minCoords=(0, 0), maxCoords=(1, 1), cellSize=1 / 8,
                                         regular=False, qdegree=2, refinement=2)
base_levels = base._coarse_level_meshes()[:-1] + [base]           # h = 1/8, 1/16, 1/32
t_base = time.perf_counter() - wall


def ladder(host, k, widen=True):
    """The fault's ladder at 2^k S (every 2^k-th spine point) placed in ``host``, split."""
    c = 2 ** k
    width = 2 * S * (c if widen else 1)
    for clearance in (0.7, 0.5):
        try:
            return place_fault_ribbon_2d(host, [(FAULT, trace[::c])], width, margin_rings=1,
                                         clearance=clearance, split=True, mesher="ladder")[0]
        except RuntimeError as err:
            last = err
    raise last


def graded_depth():
    """The smallest j with h_b / (2^j S) <= 4."""
    j = 1
    while H_B / (2 ** j * S) > 4.0:
        j += 1
    return j


hier = params.uw_hier
wall = time.perf_counter()
if hier == "H0":
    levels, names = list(base_levels), ["1/8", "1/16", "1/32"]
elif hier in ("H1", "H1c"):
    widen = hier == "H1"
    levels = base_levels[:-2] + [ladder(base_levels[-2], 2, widen), ladder(base_levels[-1], 1, widen)]
    names = ["1/8", "4S in 1/16", "2S in 1/32"]
elif hier == "H2":
    J = graded_depth()
    levels = list(base_levels) + [ladder(base_levels[-1], j) for j in range(J, 0, -1)]
    names = ["1/8", "1/16", "1/32"] + [f"{2 ** j}S in 1/32" for j in range(J, 0, -1)]
elif hier == "H3":
    J = max(2, graded_depth())
    levels = base_levels[:-2] + [ladder(base_levels[-2], 2)] + [ladder(base_levels[-1], j)
                                                               for j in range(J, 0, -1)]
    names = ["1/8", "4S in 1/16"] + [f"{2 ** j}S in 1/32" for j in range(J, 0, -1)]
else:
    raise ValueError(f"unknown hierarchy {hier}")
mesh = ladder(base, 0)
names.append("S in 1/32 (solver mesh)")
t_place = time.perf_counter() - wall

x, y = mesh.X
v = uw.discretisation.MeshVariable("v", mesh, 2, degree=2)
p = uw.discretisation.MeshVariable("p", mesh, 1, degree=1, continuous=True)
stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
stokes.constitutive_model.Parameters.shear_viscosity_0 = 1.0
stokes.bodyforce = [0.0, 0.0]
for wall_name in ("Bottom", "Top", "Left", "Right"):
    stokes.add_dirichlet_bc((y - 0.5, 0.0), wall_name)
stokes.add_fault_bc(0, boundary=FAULT)
stokes.petsc_use_pressure_nullspace = True
stokes.tolerance = float(params.uw_tol)

wall = time.perf_counter()
set_custom_fmg(stokes, levels, field_id=0)
t_fmg = time.perf_counter() - wall


wall = time.perf_counter()
stokes.solve()
t_solve_first = time.perf_counter() - wall
info = stokes._rotated_freeslip_info
record_info = {k: info.get(k) for k in ("converged", "nonlinear_iterations", "ksp_its",
                                        "vel_its_last", "pres_its_last", "velocity_pc")}
_, slip, _ = fault_slip(stokes, FAULT, info)
peak = uw.mpi.comm.allreduce(float(np.abs(slip).max()) if len(slip) else 0.0, op=max)

def level_smoothers(velpc):
    """The smoother each velocity multigrid level runs, as installed: KSP and PC type;
    for a FAC patch level (custom_mg, #629: PC composite = whole-level SOR, then ASM
    over the band blocks) the ASM blocks and their rows summed over the ranks, and the
    block solver. Level 0 is the coarse solve."""
    out = []
    for lev in range(velpc.getMGLevels()):
        ksp = velpc.getMGSmoother(lev)
        pc = ksp.getPC()
        entry = {"level": lev, "ksp": ksp.getType(), "pc": pc.getType()}
        asm = None
        if pc.getType() == "composite":
            subs = [pc.getCompositePC(i) for i in range(2)]     # custom_mg adds sor, asm
            entry["composite"] = [s.getType() for s in subs]
            asm = next((s for s in subs if s.getType() == "asm"), None)
        elif pc.getType() == "asm":
            asm = pc
        if asm is not None:
            sub_ksps = asm.getASMSubKSP()
            rows = sum(k.getOperators()[0].getSize()[0] for k in sub_ksps)
            entry["asm_blocks"] = int(uw.mpi.comm.allreduce(len(sub_ksps)))
            entry["asm_rows"] = int(uw.mpi.comm.allreduce(rows))
            entry["asm_sub_pc"] = sorted(set().union(*uw.mpi.comm.allgather(
                {k.getPC().getType() for k in sub_ksps})))
        out.append(entry)
    return out


# the custom-MG switches read from the environment (none set: the defaults)
MG_ENV = {k: v for k, v in os.environ.items() if k.startswith(("UW_FAC", "UW_CUSTOM_MG", "UW_MG"))}

# the velocity multigrid's levels: rows and nonzeros per row of each level operator
ctx = (getattr(stokes, "_rotated_linear_cache", None) or {}).get("ctx")
level_ops, smoothers = [], []
if ctx is not None:
    velpc = ctx["ksp"].getPC().getFieldSplitSubKSP()[0].getPC()
    if velpc.getType() == "mg":
        smoothers = level_smoothers(velpc)
        for lev in range(velpc.getMGLevels()):
            Amat = velpc.getMGSmoother(lev).getOperators()[0]
            rows = Amat.getSize()[0]
            nz = Amat.getInfo(PETSc.Mat.InfoType.GLOBAL_SUM)["nz_used"]
            level_ops.append({"rows": int(rows), "nnz_per_row": round(nz / max(rows, 1), 1)})


def n_cells(m):
    """Cells owned across the ranks (the plex numbering marks the others negative)."""
    n_own = int(np.count_nonzero(m.dm.getCellNumbering().getIndices() >= 0))
    return int(uw.mpi.comm.allreduce(n_own))


# the same solve again from zero on the cached operators: the solve alone, with every
# application of the velocity sub-KSP counted (vel_its_last is the last one only)
work = {"applications": 0, "iterations": 0}


def count_velocity_work(_ksp, its, _rnorm):
    if its == 0:
        work["applications"] += 1
    else:
        work["iterations"] += 1


if ctx is not None:
    ctx["pc"].getFieldSplitSubKSP()[0].setMonitor(count_velocity_work)
wall = time.perf_counter()
stokes.solve(zero_init_guess=True)
t_solve_again = time.perf_counter() - wall
info2 = stokes._rotated_freeslip_info

record = {
    "problem": "A (linear, the note's fixture)",
    "hierarchy": hier,
    "levels": names,
    "level_cells": [n_cells(m) for m in levels] + [n_cells(mesh)],
    "level_ops_velocity": level_ops,
    "level_smoothers": smoothers, "mg_env": MG_ENV, "fac_lu": int(params.uw_fac_lu),
    "n_rungs": n, "S": S, "h_b": H_B, "h_b_over_S": H_B / S,
    "tolerance": float(params.uw_tol),
    **record_info,
    "vel_its_last_again": info2.get("vel_its_last"),
    "vel_applications_again": work["applications"],
    "vel_its_all_applications_again": work["iterations"],
    "peak_slip": peak,
    "t_base_s": round(t_base, 2), "t_place_s": round(t_place, 2), "t_fmg_s": round(t_fmg, 2),
    "t_solve_first_s": round(t_solve_first, 2), "t_solve_again_s": round(t_solve_again, 2),
    "np": uw.mpi.size,
    "petsc": ".".join(str(i) for i in PETSc.Sys.getVersion()),
}
uw.pprint("RECORD " + json.dumps(record))
with uw.selective_ranks(0) as selected:
    if selected:
        out = os.path.expanduser(params.uw_out)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            json.dump(record, f, indent=1)
