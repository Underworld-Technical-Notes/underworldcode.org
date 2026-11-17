"""Band-ratio sweep of the multigrid hierarchy under the finest ladder, problem B: the
yielding-lid box on the faults-in-convection guide's hard state.

Non-dimensional, as box_fault.py (uw3-campaigns zg95_lid_regimes/drivers): a 4 x 1
box, Ra on the basal viscosity, viscoplastic lid, free-slip walls; the fault dips 45
degrees from the trench at x 2.0 to depth 0.35, split and frictionless from three rung
spacings below the surface, with a weak isotropic bridge (x 1e-3) to the surface. The
state is the guide's: the fixed-trench fault run's checkpoint 2000 (t 0.2316, mobility
0.70; probe hierarchy_a_vs_c.py in ~/+Simulations/zg95/box_faults/probes), one Stokes
solve from rest, the probe's solver settings. Base: box_mesh(4, 0.125, refinement 2),
so h_b = 1/32.

The solver mesh is the S ladder in a copy of the base's finest level; the hierarchies
under it are those of tail_sweep_linear.py (H0, H1, H2, H1c, H3). Every kS ladder is
2kS wide except in H1c; the spine count is a multiple of max(4, 2^J) for every
arm at a spacing, so the finest mesh is the same within a spacing (132 intervals at
S 0.004, the guide's lean-chain count).

    mpirun -np 4 python tail_sweep_box.py -uw_spacing 0.002 -uw_hier H1 -uw_out records/B_s0.002_H1_np4.json
"""
import json
import os
import sys
import time

import numpy as np
import sympy
import underworld3 as uw
from petsc4py import PETSc
from underworld3.utilities import rotated_bc
from underworld3.utilities.custom_mg import set_custom_fmg
from underworld3.utilities.fault_contact import fault_slip
from underworld3.utilities.place_surface import place_fault_ribbon_2d

params = uw.Params(
    uw_drivers="~/+Simulations/uw3-campaigns/zg95_lid_regimes/drivers",   # box_model.py
    uw_run="~/+Simulations/zg95/box_faults/runs/stagnant_tau1x1.00_fault_x2.0_dip45",
    uw_index=2000,            # the guide's hard state
    uw_spacing=0.004,         # rung spacing S: 0.004, 0.002, 0.00125
    uw_hier="H1",             # H0, H1, H2, H1c or H3
    uw_block=0,               # the spine count is a multiple of this (0: max(4, 2^J))
    uw_out="records/B.json",  # the JSON record
    uw_probe=0,               # 1: stop after the first Newton increment (records the set-up)
    uw_fac_lu=0,              # 1: the FAC patch blocks solved by LU, as custom_mg intends
)
sys.path.insert(0, os.path.expanduser(params.uw_drivers))
from box_model import box_mesh, free_slip_walls, set_viscoplastic  # noqa: E402

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

run = os.path.expanduser(params.uw_run)
with open(os.path.join(run, f"state_{params.uw_index:05d}.json")) as f:
    state = json.load(f)
p = state["params"]
H_B = float(p["uw_cell"]) / 2 ** int(p["uw_refinement"])

wall = time.perf_counter()
base = box_mesh(p["uw_width"], p["uw_cell"], p["uw_refinement"])
base_levels = base._coarse_level_meshes()[:-1] + [base]           # h = 1/8, 1/16, 1/32
T_b = uw.discretisation.MeshVariable("T", base, 1, degree=2)
T_b.read_timestep("box", "T", params.uw_index, outputPath=run)
t_base = time.perf_counter() - wall

# the fault: spine from just above the surface down past the tip; the split trace is
# the spine below three finest rung spacings under the surface
dip = np.deg2rad(float(p["uw_dip"]))
down_dip = np.array([np.cos(dip), -np.sin(dip)])
x_t = float(p["uw_trench_x"])
top = np.array([x_t, 1.02])
length = (float(p["uw_fault_depth"]) + 0.02) / np.sin(dip)

def depth_for(spacing):
    """The smallest j with h_b / (2^j S) <= 4 (the graded chain's depth J)."""
    j = 1
    while H_B / (2 ** j * spacing) > 4.0:
        j += 1
    return j


block = int(params.uw_block) or max(4, 2 ** depth_for(float(params.uw_spacing)))
n_fine = block * max(1, int(round(length / (block * float(params.uw_spacing)))))
S = length / n_fine
fine_spine = np.array([top + down_dip * (length * i / n_fine) for i in range(n_fine + 1)])


def ladder(host, k, widen=True):
    """The fault's ladder at 2^k S (every 2^k-th spine point) placed in ``host``, split."""
    c = 2 ** k
    sp = fine_spine[::c]
    tr = sp[sp[:, 1] <= 1.0 - 3.0 * S]
    width = 2 * S * (c if widen else 1)
    mesh, info = place_fault_ribbon_2d(host, [("Trench", tr)], width, spines=[("Trench", sp)],
                                       margin_rings=1, clearance=0.7, split=True, mesher="ladder")
    return mesh, tr


hier = params.uw_hier
wall = time.perf_counter()
if hier == "H0":
    levels, names = list(base_levels), ["1/8", "1/16", "1/32"]
elif hier in ("H1", "H1c"):
    widen = hier == "H1"
    levels = base_levels[:-2] + [ladder(base_levels[-2], 2, widen)[0],
                                 ladder(base_levels[-1], 1, widen)[0]]
    names = ["1/8", "4S in 1/16", "2S in 1/32"]
elif hier == "H2":
    J = depth_for(S)
    levels = list(base_levels) + [ladder(base_levels[-1], j)[0] for j in range(J, 0, -1)]
    names = ["1/8", "1/16", "1/32"] + [f"{2 ** j}S in 1/32" for j in range(J, 0, -1)]
elif hier == "H3":
    J = max(2, depth_for(S))
    levels = base_levels[:-2] + [ladder(base_levels[-2], 2)[0]] + [ladder(base_levels[-1], j)[0]
                                                                  for j in range(J, 0, -1)]
    names = ["1/8", "4S in 1/16"] + [f"{2 ** j}S in 1/32" for j in range(J, 0, -1)]
else:
    raise ValueError(f"unknown hierarchy {hier}")
mesh, trace = ladder(base, 0)
names.append("S in 1/32 (solver mesh)")
t_place = time.perf_counter() - wall

T = uw.discretisation.MeshVariable("Tp", mesh, 1, degree=2)
v = uw.discretisation.MeshVariable("Vp", mesh, 2, degree=2)
pr = uw.discretisation.MeshVariable("Pp", mesh, 1, degree=1, continuous=True)
zone = uw.discretisation.MeshVariable("zone_p", mesh, 1, degree=0, continuous=False)
T.array[:, 0, 0] = np.asarray(uw.function.global_evaluate(T_b.sym[0], T.coords)).ravel()

# the weak bridge: cells within a band half-width of the spine between the split's
# upper tip and the surface (the probe's definition)
c = np.asarray(zone.coords)
a, b = np.array([x_t, 1.0]), trace[0]
ab = b - a
s = np.clip(((c - a) @ ab) / (ab @ ab), 0.0, 1.0)
d = np.linalg.norm(c - (a + s[:, None] * ab), axis=1)
zone.array[:, 0, 0] = ((d < S) & (c[:, 1] > trace[0, 1] - S)).astype(float)

stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=pr)
weak = 1 - (1 - float(p["uw_eta_w"])) * zone.sym[0]
set_viscoplastic(stokes, T.sym[0], float(p["uw_deta"]), float(p["uw_tau0"]), float(p["uw_tau1"]),
                 float(p["uw_yield_softness"]), weak)
# the yield stress (tau0 + tau1 depth) x weak stays positive (weak >= 1e-3): no floor, as
# in the guide's runs (the head refuses a field-dependent yield stress without one)
stokes.constitutive_model.Parameters.yield_stress_min = -sympy.oo
stokes.bodyforce = float(p["uw_ra"]) * T.sym[0] * mesh.CoordinateSystem.unit_e_1
free_slip_walls(stokes)
stokes.add_fault_bc(0, boundary="Trench")
stokes.petsc_use_pressure_nullspace = True
stokes.tolerance = float(p["uw_tol"])
stokes.consistent_jacobian = "continuation"
stokes.newton_switch_rtol = 1e-2
set_custom_fmg(stokes, levels, field_id=0)

# every application of the velocity sub-KSP prints its converged reason and count
# ('Linear rotfsN_fieldsplit_vel_ solve ...'); collect_records.py sums them from the log
opts = PETSc.Options()
n0 = rotated_bc._ROT_SOLVE_COUNT
for i in range(1, 4):
    opts[f"rotfs{n0 + i}_fieldsplit_vel_ksp_converged_reason"] = None

if int(params.uw_probe):
    # the set-up probe: the same solve, its rotated loop capped at one increment
    _rotated_solve = rotated_bc.solve_rotated_freeslip
    rotated_bc.solve_rotated_freeslip = lambda *a, **k: _rotated_solve(*a, **{**k, "max_it": 1})

wall = time.perf_counter()
stokes.solve(zero_init_guess=True, picard=0, verbose=True)
t_solve = time.perf_counter() - wall
info = stokes._rotated_freeslip_info
_, slip, leak = fault_slip(stokes, "Trench", info)
peak = uw.mpi.comm.allreduce(float(np.abs(slip).max()) if len(slip) else 0.0, op=max)
leak_max = uw.mpi.comm.allreduce(float(np.abs(leak).max()) if len(leak) else 0.0, op=max)

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

ctx = (getattr(stokes, "_rotated_linear_cache", None) or {}).get("ctx")
level_ops, smoothers = [], []
if ctx is not None:
    velpc = ctx["pc"].getFieldSplitSubKSP()[0].getPC()
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


vel = [int(x) for x in info.get("vel_its_last") or []]
sw = info.get("continuation_switch_iteration")
newton_phase = vel[sw:] if sw is not None else vel
record = {
    "problem": "B (yielding-lid box, the guide's hard state)",
    "state": f"{run} index {params.uw_index}",
    "hierarchy": hier,
    "levels": names,
    "level_cells": [n_cells(m) for m in levels] + [n_cells(mesh)],
    "level_ops_velocity": level_ops,
    "level_smoothers": smoothers, "mg_env": MG_ENV, "probe": int(params.uw_probe),
    "fac_lu": int(params.uw_fac_lu),
    "spacing_requested": float(params.uw_spacing), "S": S, "spine_intervals": n_fine,
    "h_b": H_B, "h_b_over_S": H_B / S,
    "tolerance": float(p["uw_tol"]),
    "converged": bool(info.get("converged")),
    "newton_iterations": info.get("nonlinear_iterations"),
    "continuation_switch_iteration": sw,
    "outer_its": info.get("ksp_its"),
    "vel_its_last": vel,
    "vel_its_last_total": int(sum(vel)),
    "vel_its_newton_phase_min_max": [min(newton_phase), max(newton_phase)] if newton_phase else None,
    "vel_caps_200": int(sum(1 for x in vel if x >= 200)),
    "pres_its_last": info.get("pres_its_last"),
    "peak_slip": peak, "leak_max": leak_max,
    "t_base_s": round(t_base, 2), "t_place_s": round(t_place, 2), "t_solve_s": round(t_solve, 2),
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
