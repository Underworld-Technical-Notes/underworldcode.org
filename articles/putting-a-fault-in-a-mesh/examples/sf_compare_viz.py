"""Three-way comparison figure: split(fine) / TI(coarse) / TI(fine).

Rows stacked, one per case; columns = dCFF (slip vs welded/isotropic
locked reference, SHARED clim across rows) and the principal-stress
trajectory net. Fine grey mesh under everything; nodal dCFF on each
mesh's own triangulation (the artefact rule).

    ../run sf_compare_viz.py    →  sf_compare_split_ti.png
"""
import numpy as np
import pyvista as pv
import sympy
from scipy.interpolate import RegularGridInterpolator

import underworld3 as uw
import underworld3.visualisation as vis
from underworld3.utilities import fault_contact
from underworld3.utilities.custom_mg import set_custom_fmg
from underworld3.utilities.place_surface import place_fault_ribbon_2d
from underworld3.visualisation.glyphs import (direction_trajectories,
                                              trajectories_to_pv_lines)

pv.OFF_SCREEN = True
OUT = "/Users/lmoresi/+Simulations/s_fault_rig"

THETA = np.deg2rad(40.0)
C = np.array([0.5, 0.5])
A, LAM = 0.05, 0.10
S_MAIN, S_BRANCH = (-0.42, 0.42), (0.06, 0.42)
ES = np.array([np.cos(THETA), np.sin(THETA)])
ET = np.array([-np.sin(THETA), np.cos(THETA)])
RES = {"coarse": (0.03, 0.01), "fine": (0.01, 0.005)}
SENSE, MU, ETA1 = 1.0, 0.4, 1e-3
CASES = [("split", "fine"), ("ti", "coarse"), ("ti", "fine")]

NX, NY = 260, 260
xs = np.linspace(0.02, 0.98, NX)
ys = np.linspace(0.02, 0.98, NY)
grid_pts = np.column_stack([q.ravel() for q in
                            np.meshgrid(xs, ys, indexing="xy")])


def resample_arclength(P, spacing):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(round(arc[-1] / spacing)))
    n += n % 2
    s = np.linspace(0.0, arc[-1], n + 1)
    return np.column_stack([np.interp(s, arc, P[:, 0]),
                            np.interp(s, arc, P[:, 1])])


def traces_at(s_f):
    sm = np.linspace(*S_MAIN, 2000)
    tm = resample_arclength(
        C + sm[:, None] * ES + (A * np.tanh(sm / LAM))[:, None] * ET, s_f)
    sb = np.linspace(*S_BRANCH, 2000)
    tb = resample_arclength(C + sb[:, None] * ES - A * ET, s_f)
    return [("Main", tm), ("Branch", tb)]


def stokes_on(mesh, tag, ti_weak):
    """A drive-BC Stokes on ``mesh``; TI weak planes when ti_weak."""
    x, y = mesh.X
    v = uw.discretisation.MeshVariable(f"v{tag}", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable(f"p{tag}", mesh, 1, degree=1,
                                       continuous=True)
    st = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    foot = None
    if ti_weak:
        eta1 = uw.discretisation.MeshVariable(f"e{tag}", mesh, 1, degree=0)
        cen = np.asarray(eta1.coords) - C
        s_co, _t_co = cen @ ES, cen @ ET
        bm = mesh.cells_labelled("Band", 71)
        bb = mesh.cells_labelled("Band", 72)
        foot = (bm & (s_co >= S_MAIN[0]) & (s_co <= S_MAIN[1])) \
            | (bb & (s_co >= S_BRANCH[0]) & (s_co <= S_BRANCH[1]))
        eta1.array[:, 0, 0] = np.where(foot, ETA1, 1.0)
        ndir = uw.discretisation.MeshVariable(f"d{tag}", mesh, 2, degree=0,
                                              continuous=False)
        sech2 = 1.0 / np.cosh(s_co / LAM) ** 2
        nm = ET[None, :] - (A / LAM) * sech2[:, None] * ES[None, :]
        nm /= np.linalg.norm(nm, axis=1, keepdims=True)
        dvals = np.tile(ET, (len(s_co), 1))
        fm = bm & (s_co >= S_MAIN[0]) & (s_co <= S_MAIN[1])
        dvals[fm] = nm[fm]
        ndir.array[...] = dvals.reshape(ndir.array.shape)
        st.constitutive_model = \
            uw.constitutive_models.TransverseIsotropicFlowModel
        st.constitutive_model.Parameters.shear_viscosity_0 = 1.0
        st.constitutive_model.Parameters.shear_viscosity_1 = eta1.sym[0]
        st.constitutive_model.Parameters.director = ndir.sym
    else:
        st.constitutive_model = uw.constitutive_models.ViscousFlowModel
        st.constitutive_model.Parameters.shear_viscosity_0 = 1.0
    st.bodyforce = [0.0, 0.0]
    t_sym = (x - 0.5) * float(ET[0]) + (y - 0.5) * float(ET[1])
    for wall in ("Bottom", "Top", "Left", "Right"):
        st.add_dirichlet_bc((SENSE * 2.0 * t_sym * float(ES[0]),
                             SENSE * 2.0 * t_sym * float(ES[1])), wall)
    st.petsc_use_pressure_nullspace = True
    st.tolerance = 1e-5
    st.strategy = "robust"
    base = mesh._sf_base            # stashed by build_case
    set_custom_fmg(st, base._coarse_level_meshes()[:-1] + [base],
                   field_id=0, fac_zone=foot)
    return st, p


def sampler(st, p, tag):
    tau = st.constitutive_model.flux
    fields = {}
    for key, expr in (("xx", tau[0, 0]), ("xy", tau[0, 1]),
                      ("yy", tau[1, 1]), ("p", p.sym[0])):
        wv = uw.discretisation.MeshVariable(f"w{key}{tag}", st.mesh, 1,
                                            degree=1)
        proj = uw.systems.Projection(st.mesh, wv)
        proj.smoothing = 0.0
        proj.uw_function = expr
        proj.solve()
        fields[key] = wv
    p_mean = float(fields["p"].data[:, 0].mean())

    def sig_at(P):
        c = {k: np.asarray(uw.function.evaluate(wv.sym[0], P)).reshape(-1)
             for k, wv in fields.items()}
        pp = c["p"] - p_mean
        sig = np.zeros((len(P), 2, 2))
        sig[:, 0, 0] = c["xx"] - pp
        sig[:, 1, 1] = c["yy"] - pp
        sig[:, 0, 1] = sig[:, 1, 0] = c["xy"]
        return sig

    return sig_at


def receiver_normals(P):
    rel = P - C
    s_co = rel @ ES
    sech2 = 1.0 / np.cosh(s_co / LAM) ** 2
    n = ET[None, :] - (A / LAM) * sech2[:, None] * ES[None, :]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def cff(sig, n):
    t = np.einsum("...ij,...j->...i", sig, n)
    sn = np.einsum("...i,...i->...", t, n)
    ts = np.linalg.norm(t - sn[..., None] * n, axis=-1)
    return ts + MU * sn


def build_case(rep, res):
    w, s_f = RES[res]
    traces = traces_at(s_f)
    base = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), cellSize=1 / 8,
        regular=False, qdegree=2, refinement=1)
    tag = f"{rep[0]}{res[0]}"
    # slipping state
    mesh, _ = place_fault_ribbon_2d(base, traces, w,
                                    split=(rep == "split"))
    mesh._sf_base = base
    st_s, p_s = stokes_on(mesh, f"S{tag}", ti_weak=(rep == "ti"))
    if rep == "split":
        st_s.add_fault_bc(0, boundary="Main")
        st_s.add_fault_bc(0, boundary="Branch")
        fault_contact.solve_with_fault(st_s)
    else:
        st_s.solve()
    sig_at_s = sampler(st_s, p_s, f"S{tag}")
    # locked reference: welded (split) / isotropic (ti)
    if rep == "split":
        mesh_l, _ = place_fault_ribbon_2d(base, traces, w, split=False)
        mesh_l._sf_base = base
    else:
        mesh_l = mesh
    st_l, p_l = stokes_on(mesh_l, f"L{tag}", ti_weak=False)
    st_l.solve()
    sig_at_l = sampler(st_l, p_l, f"L{tag}")

    pvm = vis.mesh_to_pv_mesh(mesh)
    verts = np.asarray(pvm.points[:, :2])
    nrec = receiver_normals(verts)
    pvm.point_data["dCFF"] = cff(sig_at_s(verts), nrec) \
        - cff(sig_at_l(verts), nrec)
    return {"mesh": mesh, "pvm": pvm, "sig_grid": sig_at_s(grid_pts),
            "traces": traces}


cases = {}
for rep, res in CASES:
    uw.pprint(f"--- {rep}/{res} ---")
    cases[(rep, res)] = build_case(rep, res)
    d = cases[(rep, res)]["pvm"].point_data["dCFF"]
    uw.pprint(f"[{rep}/{res}] dCFF range {d.min():.3f} .. {d.max():.3f}")

vmax = float(np.percentile(np.abs(np.concatenate(
    [np.asarray(c["pvm"].point_data["dCFF"]) for c in cases.values()])),
    98))


def trajectories_for(sig_grid):
    interp = {k: RegularGridInterpolator(
        (xs, ys), sig_grid.reshape(NY, NX, 2, 2)[..., i, j].T,
        bounds_error=False, fill_value=None)
        for k, (i, j) in (("xx", (0, 0)), ("xy", (0, 1)),
                          ("yy", (1, 1)))}

    def direction_at_factory(family):
        def direction_at(pt):
            if not (0.03 <= pt[0] <= 0.97 and 0.03 <= pt[1] <= 0.97):
                return None
            s = np.array([[interp["xx"](pt)[0], interp["xy"](pt)[0]],
                          [interp["xy"](pt)[0], interp["yy"](pt)[0]]])
            w_, v_ = np.linalg.eigh(s)
            if abs(w_[1] - w_[0]) < 1e-12:
                return None
            u = v_[:, 1] if family == "tensile" else v_[:, 0]
            return u / np.linalg.norm(u)
        return direction_at

    seeds = np.column_stack([q.ravel() for q in np.meshgrid(
        np.linspace(0.06, 0.94, 30), np.linspace(0.06, 0.94, 30),
        indexing="xy")])
    np.random.default_rng(3).shuffle(seeds)
    inside = lambda pt: 0.03 <= pt[0] <= 0.97 and 0.03 <= pt[1] <= 0.97
    return {fam: direction_trajectories(
        direction_at_factory(fam), seeds, inside, step=0.004,
        separation=0.028) for fam in ("compressive", "tensile")}


pl = pv.Plotter(shape=(3, 2), off_screen=True, window_size=(2100, 3100))
titles = {("split", "fine"): "split node, fine (w=0.01 convenience)",
          ("ti", "coarse"): "TI band, coarse (w=0.03, eta1=1e-3)",
          ("ti", "fine"): "TI band, fine (w=0.01, eta1=1e-3)"}
for row, key in enumerate(CASES):
    case = cases[key]
    edges = vis.mesh_to_pv_mesh(case["mesh"]).extract_all_edges()
    edges.points[:, 2] = 0.001

    def common(pl):
        pl.set_background("white")
        pl.add_mesh(edges.copy(), color="grey", line_width=0.3,
                    opacity=0.3, lighting=False)
        for _lbl, P in case["traces"]:
            pl.add_mesh(pv.lines_from_points(
                np.column_stack([P, np.full(len(P), 0.003)])),
                color="black", line_width=2.0, lighting=False)
        pl.view_xy()
        pl.camera.parallel_projection = True
        pl.camera.focal_point = (0.5, 0.5, 0.0)
        pl.camera.parallel_scale = 0.52

    pl.subplot(row, 0)
    pl.add_mesh(case["pvm"], scalars="dCFF", cmap="RdBu_r",
                clim=(-vmax, vmax), lighting=False,
                scalar_bar_args={"title": "dCFF", "color": "black"}
                if row == 0 else None,
                show_scalar_bar=(row == 0))
    common(pl)
    pl.add_text(f"dCFF: {titles[key]}", font_size=12, color="black")
    pl.subplot(row, 1)
    traj = trajectories_for(case["sig_grid"])
    for fam, col in (("compressive", "#2166ac"), ("tensile", "#b2182b")):
        pl.add_mesh(trajectories_to_pv_lines(traj[fam]), color=col,
                    line_width=1.5, lighting=False)
    common(pl)
    pl.add_text("stress trajectories", font_size=12, color="black")

pl.screenshot(f"{OUT}/sf_compare_split_ti.png")
pl.close()
print(f"wrote {OUT}/sf_compare_split_ti.png")
