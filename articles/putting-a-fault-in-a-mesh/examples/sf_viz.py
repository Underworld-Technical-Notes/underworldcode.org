"""The S-fault rig's standard figures (Louis's spec, 2026-08-24).

Two panels over a very fine grey mesh:
  A — ΔCFF, slip vs NO-SLIP: the locked reference is a WELDED solve
      (same placement, split=False; at contrast=1 it reproduces uniform
      shear — the built-in validation), receiver planes at the local
      fault-line orientation, μ_f = 0.4.
  B — principal-stress TRAJECTORIES of the slipping state (PR #601
      integrator: mod-180 continuity, Jobard–Lehmann spacing), blue
      compressive / red tensile per the standing glyph ruling;
      demeaned-p gauge.

    ../run sf_viz.py [-uw_res coarse|fine] [-uw_contrast C] [-uw_sense S]
        →  sf_dcff_trajectories_<res>_c<C>.png
"""
import os
import numpy as np
import pyvista as pv
from scipy.interpolate import RegularGridInterpolator

import underworld3 as uw
import underworld3.visualisation as vis
from underworld3.utilities import fault_contact
from underworld3.utilities.custom_mg import set_custom_fmg
from underworld3.utilities.place_surface import place_fault_ribbon_2d
from underworld3.visualisation.glyphs import (direction_trajectories,
                                              trajectories_to_pv_lines)

pv.OFF_SCREEN = True
OUT = os.environ.get("SF_OUT", ".")   # where the figures are written

params = uw.Params(
    res=uw.Param("coarse", "coarse | fine (the two-resolution protocol)"),
    contrast=uw.Param(1.0, "strong-terrane viscosity factor"),
    sense=uw.Param(1.0, "+1 restraining, -1 releasing"),
    mu_f=uw.Param(0.4, "CFF friction coefficient"),
)

THETA = np.deg2rad(40.0)
C = np.array([0.5, 0.5])
A, LAM = 0.05, 0.10
S_MAIN, S_BRANCH = (-0.42, 0.42), (0.06, 0.42)
ES = np.array([np.cos(THETA), np.sin(THETA)])
ET = np.array([-np.sin(THETA), np.cos(THETA)])
RES = {"coarse": (0.03, 0.01), "fine": (0.01, 0.005)}
W, S_F = RES[str(params.res)]
CONTRAST, SENSE, MU = (float(params.contrast), float(params.sense),
                       float(params.mu_f))

NX, NY = 260, 260
xs = np.linspace(0.02, 0.98, NX)
ys = np.linspace(0.02, 0.98, NY)
pts = np.column_stack([q.ravel() for q in
                       np.meshgrid(xs, ys, indexing="xy")])


def resample_arclength(P, spacing):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(round(arc[-1] / spacing)))
    n += n % 2
    s = np.linspace(0.0, arc[-1], n + 1)
    return np.column_stack([np.interp(s, arc, P[:, 0]),
                            np.interp(s, arc, P[:, 1])])


sm = np.linspace(*S_MAIN, 2000)
trace_main = resample_arclength(
    C + sm[:, None] * ES + (A * np.tanh(sm / LAM))[:, None] * ET, S_F)
sb = np.linspace(*S_BRANCH, 2000)
trace_branch = resample_arclength(C + sb[:, None] * ES - A * ET, S_F)
TRACES = [("Main", trace_main), ("Branch", trace_branch)]


def solve_state(split):
    base = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), cellSize=1 / 8,
        regular=False, qdegree=2, refinement=1)
    mesh, _info = place_fault_ribbon_2d(base, TRACES, W, split=split)
    x, y = mesh.X
    v = uw.discretisation.MeshVariable("vV", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable("pV", mesh, 1, degree=1,
                                       continuous=True)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    if CONTRAST != 1.0:
        eta = uw.discretisation.MeshVariable("etaV", mesh, 1, degree=0)
        cen = np.asarray(eta.coords) - C
        strong = (cen @ ET) > A * np.tanh((cen @ ES) / LAM)
        eta.array[:, 0, 0] = np.where(strong, CONTRAST, 1.0)
        stokes.constitutive_model.Parameters.shear_viscosity_0 = eta.sym[0]
    else:
        stokes.constitutive_model.Parameters.shear_viscosity_0 = 1.0
    stokes.bodyforce = [0.0, 0.0]
    t_sym = (x - 0.5) * float(ET[0]) + (y - 0.5) * float(ET[1])
    for wall in ("Bottom", "Top", "Left", "Right"):
        stokes.add_dirichlet_bc((SENSE * 2.0 * t_sym * float(ES[0]),
                                 SENSE * 2.0 * t_sym * float(ES[1])), wall)
    stokes.petsc_use_pressure_nullspace = True
    stokes.tolerance = 1e-5
    stokes.strategy = "robust"
    set_custom_fmg(stokes, base._coarse_level_meshes()[:-1] + [base],
                   field_id=0)
    if split:
        stokes.add_fault_bc(0, boundary="Main")
        stokes.add_fault_bc(0, boundary="Branch")
        fault_contact.solve_with_fault(stokes)
    else:
        stokes.solve()

    # P1 recovery into PERSISTENT per-component fields; the sampler
    # closure assembles sigma at ANY points. At mesh VERTICES the P1
    # evaluation is exact whichever cell the locator picks — the
    # artefact-free way to render (off-lattice grid sampling dapples
    # at element boundaries; Louis's catch).
    tag = "s" if split else "l"
    tau = stokes.constitutive_model.flux
    fields = {}
    for key, expr in (("xx", tau[0, 0]), ("xy", tau[0, 1]),
                      ("yy", tau[1, 1]), ("p", p.sym[0])):
        wv = uw.discretisation.MeshVariable(f"w{key}{tag}", mesh, 1,
                                            degree=1)
        proj = uw.systems.Projection(mesh, wv)
        proj.smoothing = 0.0
        proj.uw_function = expr
        proj.solve()
        fields[key] = wv
    p_mean = float(fields["p"].data[:, 0].mean())   # demeaned-p gauge

    def sig_at(P):
        c = {k: np.asarray(uw.function.evaluate(wv.sym[0], P)).reshape(-1)
             for k, wv in fields.items()}
        pp = c["p"] - p_mean
        sig = np.zeros((len(P), 2, 2))
        sig[:, 0, 0] = c["xx"] - pp
        sig[:, 1, 1] = c["yy"] - pp
        sig[:, 0, 1] = sig[:, 1, 0] = c["xy"]
        return sig

    return sig_at, mesh


def receiver_normals(P):
    rel = P - C
    s_co = rel @ ES
    sech2 = 1.0 / np.cosh(s_co / LAM) ** 2
    # grad(t - A tanh(s/lam)) = et - (A/lam) sech^2 * es
    n = ET[None, :] - (A / LAM) * sech2[:, None] * ES[None, :]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def cff(sig, n):
    t = np.einsum("...ij,...j->...i", sig, n)
    sn = np.einsum("...i,...i->...", t, n)
    ts = np.linalg.norm(t - sn[..., None] * n, axis=-1)
    return ts + MU * sn


uw.pprint("--- slipping state ---")
sig_at_s, mesh_s = solve_state(split=True)
uw.pprint("--- locked (welded) state ---")
sig_at_l, _mesh_l = solve_state(split=False)

# NODAL dCFF on the slipping mesh's own triangulation (artefact-free)
pv_mesh = vis.mesh_to_pv_mesh(mesh_s)
verts = np.asarray(pv_mesh.points[:, :2])
sigv_s = sig_at_s(verts)
sigv_l = sig_at_l(verts)
if CONTRAST == 1.0:
    dev = np.abs(sigv_l[:, 0, 1] - sigv_l[:, 0, 1].mean()).max()
    uw.pprint(f"locked-state validation (contrast=1): sigma_xy spread "
              f"{dev:.2e} about uniform shear")
nrec_v = receiver_normals(verts)
dcff = cff(sigv_s, nrec_v) - cff(sigv_l, nrec_v)
pv_mesh.point_data["dCFF"] = dcff
uw.pprint(f"dCFF range {dcff.min():.3f} .. {dcff.max():.3f}")

# trajectory direction fields from grid-interpolated stress components
sig_s = sig_at_s(pts)
interp = {k: RegularGridInterpolator(
    (xs, ys), sig_s.reshape(NY, NX, 2, 2)[..., i, j].T,
    bounds_error=False, fill_value=None)
    for k, (i, j) in (("xx", (0, 0)), ("xy", (0, 1)), ("yy", (1, 1)))}


def direction_at_factory(family):
    def direction_at(p):
        if not (0.03 <= p[0] <= 0.97 and 0.03 <= p[1] <= 0.97):
            return None
        s = np.array([[interp["xx"](p)[0], interp["xy"](p)[0]],
                      [interp["xy"](p)[0], interp["yy"](p)[0]]])
        w_, v_ = np.linalg.eigh(s)
        if abs(w_[1] - w_[0]) < 1e-12:
            return None                      # isotropic point
        u = v_[:, 1] if family == "tensile" else v_[:, 0]
        return u / np.linalg.norm(u)
    return direction_at


seeds = np.column_stack([q.ravel() for q in np.meshgrid(
    np.linspace(0.06, 0.94, 30), np.linspace(0.06, 0.94, 30),
    indexing="xy")])
np.random.default_rng(3).shuffle(seeds)
inside = lambda p: 0.03 <= p[0] <= 0.97 and 0.03 <= p[1] <= 0.97
traj = {fam: direction_trajectories(
    direction_at_factory(fam), seeds, inside, step=0.004,
    separation=0.028) for fam in ("compressive", "tensile")}
uw.pprint(f"trajectories: {len(traj['compressive'])} compressive, "
          f"{len(traj['tensile'])} tensile")

# ------------------------------------------------------------------ plot
edges = vis.mesh_to_pv_mesh(mesh_s).extract_all_edges()
edges.points[:, 2] = 0.001


def add_common(pl):
    pl.set_background("white")
    pl.add_mesh(edges, color="grey", line_width=0.3, opacity=0.3,
                lighting=False)
    for _lbl, P in TRACES:
        pl.add_mesh(pv.lines_from_points(
            np.column_stack([P, np.full(len(P), 0.003)])),
            color="black", line_width=2.5, lighting=False)
    pl.view_xy()
    pl.camera.parallel_projection = True
    pl.camera.focal_point = (0.5, 0.5, 0.0)
    pl.camera.parallel_scale = 0.52


vmax = float(np.percentile(np.abs(dcff), 98))
pl = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(2200, 1150))
pl.subplot(0, 0)
pl.add_mesh(pv_mesh, scalars="dCFF", cmap="RdBu_r", clim=(-vmax, vmax),
            lighting=False, show_edges=False,
            scalar_bar_args={"title": "dCFF", "color": "black"})
add_common(pl)
pl.add_text(f"dCFF slip vs welded ({params.res}, contrast "
            f"{CONTRAST:g}, sense {SENSE:+.0f})", font_size=13,
            color="black")
pl.subplot(0, 1)
for fam, col in (("compressive", "#2166ac"), ("tensile", "#b2182b")):
    pl.add_mesh(trajectories_to_pv_lines(traj[fam]), color=col,
                line_width=1.6, lighting=False)
add_common(pl)
pl.add_text("principal-stress trajectories (slipping; demeaned-p)",
            font_size=13, color="black")
name = f"sf_dcff_trajectories_{params.res}_c{CONTRAST:g}.png"
pl.screenshot(f"{OUT}/{name}")
pl.close()
print(f"wrote {OUT}/{name}")
