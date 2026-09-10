"""The S-fault 2-D rig: San Andreas bend + through-line branch (#629).

Geometry of record (see geometry_preview.py / the plan file): tanh S on
the 40° diagonal, the branch as the stop-short through-line alternative
in the weak block, the fault line as the TERRANE boundary (strong η ×
contrast above/left, painted by the same implicit rule), plate-motion
shear drive. Split-node (thin-fault reference) representation.

Two-resolution protocol: -uw_res coarse (w=0.03, s_f=0.01) |
fine (w=0.01, s_f=0.005). Every finite-w (volumetric) result must run
both and compare to THIS split reference.

    ../run s_fault.py -uw_fmg 1                  # FMG [L0, L1] + finest
    ../run s_fault.py -uw_fmg 0                  # GAMG control
    ../run s_fault.py -uw_contrast 1e3           # strong block dial
    ../run s_fault.py -uw_sense -1               # releasing-bend drive
"""
import time

import numpy as np

import underworld3 as uw
from underworld3.utilities import fault_contact
from underworld3.utilities.place_surface import place_fault_ribbon_2d

params = uw.Params(
    res=uw.Param("coarse", "coarse (w=0.03, s_f=0.01) | fine "
                           "(w=0.01, s_f=0.005) — the two-resolution "
                           "protocol"),
    contrast=uw.Param(1.0, "strong-block viscosity factor (the terrane "
                           "above/left of the fault line)"),
    sense=uw.Param(1.0, "drive sign: +1 restraining bend, -1 releasing"),
    fmg=uw.Param(1.0, "1 = FMG tail [L0, L1]; 0 = GAMG control"),
    h_bg=uw.Param(1 / 8, "L0 cell size (refinement=1 halves it for L1)"),
    margin=uw.Param(2.0, "tip margin rings (extrapolated band surround)"),
    tol=uw.Param(1e-5, "stokes tolerance"),
    strategy=uw.Param("robust", "fast | robust smoothers"),
    penalty=uw.Param(0.0, "AL penalty (gamma=1 is the sanctioned choice)"),
    rep=uw.Param("split", "split (thin-fault reference) | ti (volumetric "
                          "weak shear plane; w IS physics — run BOTH "
                          "resolutions, the protocol)"),
    eta1=uw.Param(1e-3, "TI shear viscosity in the fault footprint "
                        "(rep=ti; isotropic elsewhere)"),
)

# ---------------------------------------------------- geometry of record
THETA = np.deg2rad(40.0)
C = np.array([0.5, 0.5])
A, LAM = 0.05, 0.10
S_MAIN = (-0.42, 0.42)
S_BRANCH = (0.06, 0.42)
ES = np.array([np.cos(THETA), np.sin(THETA)])
ET = np.array([-np.sin(THETA), np.cos(THETA)])

RES = {"coarse": (0.03, 0.01), "fine": (0.01, 0.005)}
W, S_F = RES[str(params.res)]


def resample_arclength(P, spacing):
    """Equispaced-in-arclength samples of a dense polyline, ends kept,
    interval count EVEN (so a 2:1 subsample exists when wanted)."""
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(round(arc[-1] / spacing)))
    n += n % 2
    s = np.linspace(0.0, arc[-1], n + 1)
    return np.column_stack([np.interp(s, arc, P[:, 0]),
                            np.interp(s, arc, P[:, 1])])


def main_curve(s):
    return C + s[:, None] * ES + (A * np.tanh(s / LAM))[:, None] * ET


dense = main_curve(np.linspace(*S_MAIN, 2000))
trace_main = resample_arclength(dense, S_F)
sb = np.linspace(*S_BRANCH, 2000)
trace_branch = resample_arclength(C + sb[:, None] * ES - A * ET, S_F)

base = uw.meshing.UnstructuredSimplexBox(
    minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0),
    cellSize=float(params.h_bg), regular=False, qdegree=2, refinement=1)

rep = str(params.rep)
t0 = time.perf_counter()
mesh, pinfo = place_fault_ribbon_2d(
    base, [("Main", trace_main), ("Branch", trace_branch)], W,
    margin_rings=int(float(params.margin)), split=(rep == "split"))
uw.pprint(f"[{params.res}/{rep}] {pinfo['n_cells']} cells, rungs "
          f"{pinfo['n_rungs']}, build {time.perf_counter() - t0:.1f} s")

x, y = mesh.X
v = uw.discretisation.MeshVariable("vS", mesh, 2, degree=2)
p = uw.discretisation.MeshVariable("pS", mesh, 1, degree=1,
                                   continuous=True)
stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
contrast = float(params.contrast)

# THE TERRANE: strong on the +t side of the fault LINE — the same
# implicit rule as the diagram, painted P0 by cell centroid.
eta0 = uw.discretisation.MeshVariable("etaS", mesh, 1, degree=0)
cen = np.asarray(eta0.coords) - C
s_co = cen @ ES
t_co = cen @ ET
strong = t_co > A * np.tanh(s_co / LAM)
eta0_vals = np.where(strong, contrast, 1.0)
eta0.array[:, 0, 0] = eta0_vals
if contrast != 1.0:
    uw.pprint(f"terrane: {int(strong.sum())} strong cells at "
              f"eta {contrast:g}")

if rep == "ti":
    # VOLUMETRIC representation: each band carries a TI weak shear
    # plane. The paint honours the FAULT FOOTPRINT (never the
    # extrapolated margin), per strand; the director follows each
    # strand's own orientation PER CELL (the main band is curved).
    eta1_val = float(params.eta1)
    band_main = mesh.cells_labelled("Band", 71)
    band_branch = mesh.cells_labelled("Band", 72)
    foot_main = band_main & (s_co >= S_MAIN[0]) & (s_co <= S_MAIN[1])
    foot_branch = band_branch & (s_co >= S_BRANCH[0]) \
        & (s_co <= S_BRANCH[1])
    foot = foot_main | foot_branch
    eta1 = uw.discretisation.MeshVariable("etaT", mesh, 1, degree=0)
    eta1.array[:, 0, 0] = np.where(foot, eta1_val, eta0_vals)
    ndir = uw.discretisation.MeshVariable("dirT", mesh, 2, degree=0,
                                          continuous=False)
    sech2 = 1.0 / np.cosh(s_co / LAM) ** 2
    n_main = ET[None, :] - (A / LAM) * sech2[:, None] * ES[None, :]
    n_main /= np.linalg.norm(n_main, axis=1, keepdims=True)
    dvals = np.tile(ET, (len(s_co), 1))          # branch/default: ê_t
    dvals[foot_main] = n_main[foot_main]         # main: curved normal
    ndir.array[...] = dvals.reshape(ndir.array.shape)
    uw.pprint(f"[ti] painted {int(foot.sum())} footprint cells "
              f"({int(band_main.sum())}+{int(band_branch.sum())} band) "
              f"at eta_1 {eta1_val:g}")
    stokes.constitutive_model = \
        uw.constitutive_models.TransverseIsotropicFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = eta0.sym[0]
    stokes.constitutive_model.Parameters.shear_viscosity_1 = eta1.sym[0]
    stokes.constitutive_model.Parameters.director = ndir.sym
else:
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = \
        (eta0.sym[0] if contrast != 1.0 else 1.0)
stokes.bodyforce = [0.0, 0.0]

# plate-motion-frame shear: v = 2 V t_coord ê_s (sense flips the bend
# between restraining and releasing)
sense = float(params.sense)
t_sym = (x - 0.5) * float(ET[0]) + (y - 0.5) * float(ET[1])
vx = sense * 2.0 * t_sym * float(ES[0])
vy = sense * 2.0 * t_sym * float(ES[1])
for wall in ("Bottom", "Top", "Left", "Right"):
    stokes.add_dirichlet_bc((vx, vy), wall)
if rep == "split":
    stokes.add_fault_bc(0, boundary="Main")
    stokes.add_fault_bc(0, boundary="Branch")
stokes.petsc_use_pressure_nullspace = True
stokes.tolerance = float(params.tol)
if float(params.penalty) > 0.0:
    stokes.penalty = float(params.penalty)

mode = "fmg" if float(params.fmg) > 0.5 else "gamg"
if mode == "fmg":
    from underworld3.utilities.custom_mg import set_custom_fmg

    tail = base._coarse_level_meshes()[:-1] + [base]
    uw.pprint(f"tail: {[m.dm.getHeightStratum(0)[1] for m in tail]} "
              f"cells + finest {pinfo['n_cells']}")
    stokes.strategy = str(params.strategy)
    # keying ruling: split = structural only; TI = the painted footprint
    set_custom_fmg(stokes, tail, field_id=0,
                   fac_zone=(foot if rep == "ti" else None))

if rep == "split":
    t0 = time.perf_counter()
    info = fault_contact.solve_with_fault(stokes)
    t1 = time.perf_counter() - t0
    if contrast != 1.0:
        eta0.array[:, 0, 0] = np.where(strong, 1.5 * contrast, 1.0)
    t0 = time.perf_counter()
    info2 = fault_contact.solve_with_fault(stokes)
    t2 = time.perf_counter() - t0
    cache = getattr(stokes, "_rotated_linear_cache", None) or {}
    ctx = cache.get("ctx") or {}
else:
    t0 = time.perf_counter()
    stokes.solve()
    t1 = time.perf_counter() - t0
    eta1.array[:, 0, 0] = np.where(foot, 1.5 * eta1_val, eta0_vals)
    t0 = time.perf_counter()
    stokes.solve(zero_init_guess=False)
    t2 = time.perf_counter() - t0
    ksp0 = stokes.snes.getKSP()
    sub = ksp0.getPC().getFieldSplitSubKSP()
    info = info2 = {"converged": stokes.snes.getConvergedReason() > 0}
    ctx = {"ksp": ksp0, "vel_its_last": sub[0].getIterationNumber(),
           "pres_its_last": sub[1].getIterationNumber()}
uw.pprint(f"[{mode}] solve {t1:.1f} s, repeat {t2:.1f} s; converged "
          f"{info.get('converged')}/{info2.get('converged')}")
uw.pprint(f"[{mode}] last apply: vel {ctx.get('vel_its_last')} its, "
          f"pres {ctx.get('pres_its_last')} its")
try:
    velpc = ctx["ksp"].getPC().getFieldSplitSubKSP()[0].getPC()
    if velpc.getType() == "mg":
        for l in range(velpc.getMGLevels()):
            sm = velpc.getMGSmoother(l)
            Aop = sm.getOperators()[0]
            n = Aop.getSize()[0]
            spc = sm.getPC()
            fac = ""
            if spc.getType() == "asm":
                sub = spc.getASMSubKSP()
                ssz = sum(k.getOperators()[0].getSize()[0] for k in sub)
                fac = f", asm {len(sub)} block(s) {ssz}/{n} rows"
            uw.pprint(f"[{mode}] level {l}: n={n}, nnz/row="
                      f"{Aop.getInfo()['nz_used'] / max(n, 1):.0f}{fac}")
except Exception as exc:
    uw.pprint(f"[{mode}] level probe failed: {exc}")

# -------------------- slip partitioning (the hook), two spellings:
# (a) the discrete pair slip (split only); (b) a FIXED-OFFSET
# across-band Delta v_t profile at +-0.03 from each trace — the
# representation-agnostic measure, comparable across w and rep.
OFF = 0.03


def across_profile(trace):
    P = trace[::2]
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.column_stack([-t[:, 1], t[:, 0]])
    vv_p = np.asarray(uw.function.evaluate(
        v.sym, P + OFF * n)).reshape(len(P), -1)
    vv_m = np.asarray(uw.function.evaluate(
        v.sym, P - OFF * n)).reshape(len(P), -1)
    dv = vv_p[:, :2] - vv_m[:, :2]
    dvt = np.einsum("ij,ij->i", dv, t)
    s_along = (P - C) @ ES
    return s_along, np.abs(dvt)


profiles = {}
for label, trace in (("Main", trace_main), ("Branch", trace_branch)):
    s_a, dvt = across_profile(trace)
    profiles[label] = (s_a, dvt)
    line = (f"[{mode}/{rep}] {label}: dv_t(+-{OFF}) peak {dvt.max():.4f}"
            f", mean {dvt.mean():.4f}")
    if rep == "split":
        coords, jumps, normals = fault_contact.fault_pair_jumps(
            stokes, label, stokes._rotated_freeslip_info)
        jn = np.einsum("ij,ij->i", jumps, normals)
        tang = np.linalg.norm(jumps - jn[:, None] * normals, axis=1)
        line += (f"; pair slip peak {tang.max():.4f}, leak "
                 f"{np.abs(jn).max():.2e}")
    uw.pprint(line)
ratio = profiles["Branch"][1].max() / max(profiles["Main"][1].max(), 1e-30)
uw.pprint(f"[{mode}/{rep}] PARTITION branch/main peak dv_t ratio: "
          f"{ratio:.3f}")
np.savez(f"slip_profiles_{params.res}_{rep}_{mode}_c{contrast:g}"
         f"_s{int(sense)}.npz",
         **{f"{k}_{q}": arr for k, (s_, t_) in profiles.items()
            for q, arr in (("s", s_), ("dvt", t_))})

# CHECKPOINT the solved state (Louis's rule: figures render from
# checkpoints, never by re-solving) — mesh + v + p (+ eta fields).
ckpt = f"ckpt_{params.res}_{rep}_c{contrast:g}_s{int(sense)}"
mvars = [v, p, eta0] + ([eta1] if rep == "ti" else [])
mesh.write_timestep(ckpt, index=0, outputPath="checkpoints",
                    meshVars=mvars, meshUpdates=True)
uw.pprint(f"checkpointed -> checkpoints/{ckpt} (mesh + "
          f"{[q.name for q in mvars]})")
