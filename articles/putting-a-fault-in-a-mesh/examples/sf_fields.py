"""Shared IN-SESSION solve + nodal recovery for the rig's field renders
(in-session because of #640: split-mesh checkpoint reload mixes the
cut DOFs). One solver copy for every render script.

Recovery follows the standing rulings (reference_stress_recovery_across
_a_material_jump; fault-teaching handoff):
  * project the stress COMPONENTS to continuous P1 — never an
    invariant, never evaluate() a composite sqrt;
  * strain rate across a viscosity jump = recovered stress divided by
    each material's OWN viscosity (the jump re-enters through eta, not
    through a smeared gradient). For TI, in the (n, t) frame:
    e_nn, e_tt = tau/(2 eta0); e_nt = tau_nt/(2 eta1).
  * invariants in numpy.
Nodal eta / director are taken from the NEAREST cell centroid (the
honoured paint, cell-based; the one-ring at the band edge is the only
ambiguity).
"""
import numpy as np
import sympy
from scipy.spatial import cKDTree

import underworld3 as uw
from underworld3.utilities import fault_contact

import rig_geometry as G


def solve_rep(rep, contrast=1.0, res="coarse", cont_gap=0.004,
              eta1_val=1e-3, sense=1.0, tol=1e-5, tag="", yield_stress=0.0,
              eta1_frac=0.1, uncut=(), uncut_eta1=-1.0):
    """Solve the rig for one representation; returns the live state.
    ``yield_stress > 0`` confines a von Mises yield to the Band label
    (split: cuts + yielding band; ``rep="vp"``: the isotropic yielding
    band IS the fault — no cuts, no director). ``rep="hybrid"`` = the
    recipe (fault_interface_equivalence/HYBRID_RECIPE.md): frictionless
    cuts PLUS a mild TI band, eta_1 = eta1_frac x eta_0 on the
    footprints."""
    G.CONT_GAP_RUNGS = None            # the absolute dial
    G.CONT_GAP = float(cont_gap)
    W, S_F = G.RES[res]
    TRACES = G.traces(S_F)
    base = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), cellSize=1 / 8,
        regular=False, qdegree=2, refinement=1)
    mesh, pinfo = G.place_rig(base, S_F, W,
                              split=(rep in ("split", "hybrid")),
                              uncut=tuple(uncut))
    x, y = mesh.X
    t = f"{rep[0]}{tag}"
    v = uw.discretisation.MeshVariable(f"v{t}", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable(f"p{t}", mesh, 1, degree=1,
                                       continuous=True)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    eta0 = uw.discretisation.MeshVariable(f"eta0{t}", mesh, 1, degree=0)
    cen = np.asarray(eta0.coords)
    strong = G.strong_mask(cen)
    eta0_vals = np.where(strong, float(contrast), 1.0)
    eta0.array[:, 0, 0] = eta0_vals
    st = dict(rep=rep, contrast=float(contrast), mesh=mesh, v=v, p=p,
              stokes=stokes, eta0=eta0, eta0_vals=eta0_vals, pinfo=pinfo,
              traces=TRACES, W=W, s_f=S_F, eta1=None, ndir=None,
              foot=None)
    if rep in ("ti", "hybrid") or uncut:
        eta1, ndir, foot = G.ti_fields(mesh, pinfo["footprints"],
                                       float(eta1_val), eta0_vals, t)
        if rep == "hybrid":
            eta1.array[:, 0, 0] = np.where(foot, float(eta1_frac) * eta0_vals,
                                           eta0_vals)
        elif rep == "split":
            eta1.array[:, 0, 0] = eta0_vals
        if uncut and float(uncut_eta1) >= 0.0:
            ufoot = np.zeros_like(foot)
            for u in uncut:
                ufoot |= pinfo["footprints"][u]
            eta1.array[:, 0, 0] = np.where(ufoot, float(uncut_eta1) * eta0_vals,
                                           eta1.array[:, 0, 0])
        st["uncut"] = tuple(uncut)
        stokes.constitutive_model = \
            uw.constitutive_models.TransverseIsotropicFlowModel
        P = stokes.constitutive_model.Parameters
        P.shear_viscosity_0 = eta0.sym[0]
        P.shear_viscosity_1 = eta1.sym[0]
        P.director = ndir.sym
        st.update(eta1=eta1, ndir=ndir, foot=foot)
    elif yield_stress > 0.0:
        ybar = uw.discretisation.MeshVariable(f"y{t}", mesh, 1, degree=0)
        ybar.array[:, 0, 0] = np.where(pinfo["band"], float(yield_stress),
                                       1e8)
        stokes.constitutive_model = \
            uw.constitutive_models.ViscoPlasticFlowModel
        stokes.constitutive_model.Parameters.shear_viscosity_0 = eta0.sym[0]
        stokes.constitutive_model.Parameters.yield_stress = ybar.sym[0]
        # Newton on a FIXED rounded yield surface (Louis, 2026-08-26): the
        # hard-Min perfect-plastic tangent is 0 along the flow in every
        # yielded cell (symmetric, semi-definite) and stalls Newton when
        # many cells yield; delta=0.1 (yield_anchor "yield": exact yield
        # point, rounded corner) restores it. Not the retired in-solve
        # delta-march.
        cm_ = stokes.constitutive_model
        cm_.yield_mode = "softmin"
        cm_.yield_smoother = "powermean"
        cm_.yield_anchor = "yield"
        cm_.yield_softness = 0.1
        stokes.consistent_jacobian = True
        stokes.petsc_options["snes_max_it"] = 60
        st["tau_y"] = float(yield_stress)
    else:
        if rep == "vp":
            raise ValueError("rep='vp' needs yield_stress > 0")
        stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
        stokes.constitutive_model.Parameters.shear_viscosity_0 = eta0.sym[0]
    stokes.bodyforce = [0.0, 0.0]
    ES, ET = G.ES, G.ET
    t_sym = (x - 0.5) * float(ET[0]) + (y - 0.5) * float(ET[1])
    for wall in ("Bottom", "Top", "Left", "Right"):
        stokes.add_dirichlet_bc((sense * 2.0 * t_sym * float(ES[0]),
                                 sense * 2.0 * t_sym * float(ES[1])), wall)
    stokes.petsc_use_pressure_nullspace = True
    stokes.tolerance = float(tol)
    if rep in ("split", "hybrid"):
        for lbl, _tr in TRACES:
            if lbl in uncut:
                continue
            stokes.add_fault_bc(0, boundary=lbl)
        info = fault_contact.solve_with_fault(stokes)
        st["converged"] = bool(info.get("converged"))
    else:
        stokes.solve()
        st["converged"] = stokes.snes.getConvergedReason() > 0
    return st


def stress_expression(st):
    """Deviatoric stress components (sympy 2x2) for this rep's law."""
    E = st["stokes"].strainrate
    E = E - sympy.eye(2) * (E[0, 0] + E[1, 1]) / 2
    eta0 = st["eta0"].sym[0]
    if st["rep"] in ("ti", "hybrid"):
        nd = st["ndir"].sym
        nv = sympy.Matrix([nd[0], nd[1]])
        tv = sympy.Matrix([-nd[1], nd[0]])
        e_nt = (nv.T * E * tv)[0, 0]
        return (2 * eta0 * E
                - 2 * (eta0 - st["eta1"].sym[0]) * e_nt
                * (nv * tv.T + tv * nv.T))
    return 2 * eta0 * E


def nodal_stress(st, name="tP1"):
    """Project the stress COMPONENTS to continuous P1; returns
    (P1 variable, txx, tyy, txy) — deviatoric, nodal."""
    mesh = st["mesh"]
    S = uw.discretisation.MeshVariable(f"{name}{st['rep'][0]}", mesh, 1,
                                       degree=1)
    proj = uw.systems.Projection(mesh, S)
    tau = stress_expression(st)
    comps = {}
    for key, expr in (("xx", tau[0, 0]), ("yy", tau[1, 1]),
                      ("xy", tau[0, 1])):
        proj.uw_function = expr
        proj.solve(zero_init_guess=True)
        comps[key] = np.asarray(S.data[:, 0]).copy()
    d = 0.5 * (comps["xx"] + comps["yy"])
    return S, comps["xx"] - d, comps["yy"] - d, comps["xy"]


def nodal_material(st, S):
    """eta0, eta1, director at the P1 nodes from the NEAREST cell
    centroid (the honoured, cell-based paint)."""
    cen = np.asarray(st["eta0"].coords)
    idx = cKDTree(cen).query(np.asarray(S.coords))[1]
    eta0 = st["eta0_vals"][idx]
    if st["rep"] in ("ti", "hybrid"):
        eta1 = np.asarray(st["eta1"].array).reshape(len(cen))[idx]
        nv = np.asarray(st["ndir"].array).reshape(len(cen), 2)[idx]
    else:
        eta1 = eta0.copy()
        nv = np.tile(G.ET, (len(idx), 1))
    return eta0, eta1, nv


def nodal_strainrate(st, name="eP1"):
    """THE reliable strain-rate map (measured 2026-08-25, TI band, coarse,
    eta ratio 1e3): project the strain-rate COMPONENTS to continuous P1
    and form the invariant in numpy. In-band median 5.3 / p90 10.2 /
    max 15.9 against the direct in-cell truth 5.6 / 9.7 / 13; far field
    0.98 = the drive. The one-ring smear at the band edge is the only
    cost. Returns (P1 variable, edot_II)."""
    S, exx, eyy, exy = nodal_strainrate_components(st, name=name)
    return S, np.sqrt(0.5 * (exx ** 2 + eyy ** 2) + exy ** 2)


def nodal_strainrate_components(st, name="eP1"):
    """The deviatoric strain-rate COMPONENTS projected to continuous P1;
    returns (P1 variable, exx, eyy, exy) in the variable's DOF order —
    the recipe of :func:`nodal_strainrate`, components kept."""
    mesh = st["mesh"]
    S = uw.discretisation.MeshVariable(f"{name}{st['rep'][0]}", mesh, 1,
                                       degree=1)
    proj = uw.systems.Projection(mesh, S)
    E = st["stokes"].strainrate
    comps = {}
    for key, expr in (("xx", E[0, 0]), ("yy", E[1, 1]), ("xy", E[0, 1])):
        proj.uw_function = expr
        proj.solve(zero_init_guess=True)
        comps[key] = np.asarray(S.data[:, 0]).copy()
    d = 0.5 * (comps["xx"] + comps["yy"])
    return S, comps["xx"] - d, comps["yy"] - d, comps["xy"]


def nodal_strainrate_from_stress(st, S, txx, tyy, txy):
    """The material-jump recipe (recovered stress / own eta; TI in the
    (n, t) frame, e_nt = tau_nt / (2 eta1)). CAVEAT (measured): only
    reliable when the recovered interface stress is accurate to better
    than eta0/eta1 — at coarse w with a 1e3 ratio it is NOT (in-band
    p90 33, max 1037 vs truth 9.7 / 13): the band-edge recovery error is
    amplified 1000x. Kept for the single-cell-layer case it was measured
    on; use nodal_strainrate for a multi-cell band."""
    eta0, eta1, nv = nodal_material(st, S)
    tv = np.column_stack([-nv[:, 1], nv[:, 0]])
    # rotate tau into (n, t)
    tnn = (nv[:, 0] ** 2 * txx + 2 * nv[:, 0] * nv[:, 1] * txy
           + nv[:, 1] ** 2 * tyy)
    ttt = (tv[:, 0] ** 2 * txx + 2 * tv[:, 0] * tv[:, 1] * txy
           + tv[:, 1] ** 2 * tyy)
    tnt = (nv[:, 0] * tv[:, 0] * txx
           + (nv[:, 0] * tv[:, 1] + nv[:, 1] * tv[:, 0]) * txy
           + nv[:, 1] * tv[:, 1] * tyy)
    enn, ett, ent = tnn / (2 * eta0), ttt / (2 * eta0), tnt / (2 * eta1)
    return np.sqrt(0.5 * (enn ** 2 + ett ** 2) + ent ** 2)


def stress_invariant(txx, tyy, txy):
    return np.sqrt(0.5 * (txx ** 2 + tyy ** 2) + txy ** 2)


def native_slip_profile(st, label, mask=True):
    """The NATIVE slip gauge (Louis's ruling, 2026-08-25) on a live
    state: split = tangential pair jump along the cut; TI = band
    integral of the director-plane shear strain rate along the
    mid-line (5 stations across the band). Samples inside another
    strand's band are dropped when ``mask``. Returns (points, slip)
    with points ON the trace (for a coloured-trace overlay)."""
    from underworld3.utilities import fault_contact
    from scipy.spatial import cKDTree
    TR = dict(st["traces"])
    trace = np.asarray(TR[label])
    W = st["W"]
    others = (np.vstack([q for l2, q in st["traces"] if l2 != label])
              if mask else None)

    def own(X):
        if others is None:
            return np.ones(len(X), dtype=bool)
        k = cKDTree(others).query(X)[0] > W
        return k if k.sum() >= 3 else np.ones(len(X), dtype=bool)

    if st["rep"] in ("split", "hybrid") and label not in st.get("uncut", ()):
        coords, jumps, normals = fault_contact.fault_pair_jumps(
            st["stokes"], label, st["stokes"]._rotated_freeslip_info)
        jn = np.einsum("ij,ij->i", jumps, normals)
        tang = np.linalg.norm(jumps - jn[:, None] * normals, axis=1)
        keep = own(coords)
        return coords[keep], tang[keep]
    P = trace[::2]
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.column_stack([-t[:, 1], t[:, 0]])
    E = st["stokes"].strainrate
    # stations strictly INSIDE the band, off the mid-line and rail
    # edges (points ON an edge locate into either neighbour, host
    # cells included): the band-integral is w x the mean of 2 e_nt
    offs = W * np.array([-0.45, -0.3, -0.1, 0.1, 0.3, 0.45])
    ent = np.zeros((len(offs), len(P)))
    for k, o in enumerate(offs):
        Q = P + o * n
        exx = np.asarray(uw.function.evaluate(E[0, 0], Q)).ravel()
        eyy = np.asarray(uw.function.evaluate(E[1, 1], Q)).ravel()
        exy = np.asarray(uw.function.evaluate(E[0, 1], Q)).ravel()
        ent[k] = (n[:, 0] * t[:, 0] * exx
                  + (n[:, 0] * t[:, 1] + n[:, 1] * t[:, 0]) * exy
                  + n[:, 1] * t[:, 1] * eyy)
    # band slip = v_t difference across the band + one-cell skirt
    # (continuous field -> robust; in-cell gradient integrals are
    # vertex-phase sensitive at fine w)
    skirt = W / 2 + st["s_f"]
    v = st["v"]
    vp = np.asarray(uw.function.evaluate(v.sym, P + skirt * n)
                    ).reshape(len(P), -1)[:, :2]
    vm = np.asarray(uw.function.evaluate(v.sym, P - skirt * n)
                    ).reshape(len(P), -1)[:, :2]
    slip = np.abs(np.einsum("ij,ij->i", vp - vm, t))
    keep = own(P)
    return P[keep], slip[keep]


def midline_shear_rate(st, trace, eps=0.02):
    """The TI band's slip measure of record (Louis, 2026-08-25, reaffirmed
    2026-09-05): the shear strain rate resolved on the director plane
    ALONG THE MID-LINE, 2 e_nt = 2 n.E.t at the spine vertices.

    Computed as the NODAL RECOVERY of the P2 velocity's own gradient: in
    every cell of the vertex's fan the strain rate is evaluated at the
    vertex (a point stepped ``eps`` of the way toward the cell's
    centroid, so the locator lands in THAT cell — the P2 gradient is
    linear within a cell, so the step costs O(eps)) and the fan is
    averaged with the cells' angles at the vertex as weights. No span,
    so a neighbouring band cannot enter; no L2 projection, so no
    overshoot at the peak (the P1 projection read 91 on the fine Main
    where the in-cell truth is ~55); defined through a junction. The
    fan is summed over ranks (a shared vertex's fan is split).
    Returns (points, 2 e_nt) for the trace vertices that are mesh
    vertices (every placed trace vertex is a spine vertex).
    """
    from mpi4py import MPI
    from scipy.spatial import cKDTree
    from underworld3.utilities.reconnect import _coords
    mesh = st["mesh"]
    dm = mesh.dm
    comm = uw.mpi.comm
    vS, vE = dm.getDepthStratum(0)
    cS, cE = dm.getHeightStratum(0)
    X = _coords(dm)[: vE - vS]
    P = np.asarray(trace, dtype=float)
    d, idx = cKDTree(X).query(P)
    on = d < 1e-6
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.column_stack([-t[:, 1], t[:, 0]])
    E = st["stokes"].strainrate
    # one batch of evaluation points: every (vertex, fan cell) pair
    pts, owner, weight = [], [], []
    for k in np.flatnonzero(on):
        iv = int(idx[k])
        for c in dm.getTransitiveClosure(iv + vS, useCone=False)[0]:
            c = int(c)
            if not (cS <= c < cE):
                continue
            verts = [int(q) - vS for q in dm.getTransitiveClosure(c)[0]
                     if vS <= int(q) < vE]
            cen = X[verts].mean(axis=0)
            others = [q for q in verts if q != iv]
            a, b = X[others[0]] - X[iv], X[others[1]] - X[iv]
            ang = abs(np.arctan2(a[0] * b[1] - a[1] * b[0], a @ b))
            pts.append(X[iv] + eps * (cen - X[iv]))
            owner.append(k)
            weight.append(ang)
    num = np.zeros(len(P))
    den = np.zeros(len(P))
    if pts:
        Q = np.asarray(pts, dtype=float)
        exx = np.asarray(uw.function.evaluate(E[0, 0], Q)).ravel()
        eyy = np.asarray(uw.function.evaluate(E[1, 1], Q)).ravel()
        exy = np.asarray(uw.function.evaluate(E[0, 1], Q)).ravel()
        owner = np.asarray(owner)
        weight = np.asarray(weight)
        ent = (n[owner, 0] * t[owner, 0] * exx
               + (n[owner, 0] * t[owner, 1] + n[owner, 1] * t[owner, 0]) * exy
               + n[owner, 1] * t[owner, 1] * eyy)
        np.add.at(num, owner, weight * ent)
        np.add.at(den, owner, weight)
    if comm.size > 1:
        for arr in (num, den):
            comm.Allreduce(MPI.IN_PLACE, arr, op=MPI.SUM)
    rate = np.full(len(P), np.nan)
    have = den > 0
    rate[have] = 2.0 * np.abs(num[have] / den[have])
    return P, rate


def coloured_trace(points, values, z=0.003):
    """A pv polyline through ``points`` carrying ``values`` as point
    scalars — the coloured-trace overlay (sorted along the trace by
    the order given)."""
    import pyvista as pv
    line = pv.lines_from_points(
        np.column_stack([points, np.full(len(points), z)]))
    line.point_data["slip"] = np.asarray(values)
    return line


def yielded_cells(st):
    """Band cells on the plastic branch (2 eta0 edot_II > tau_y) from the
    in-cell strain rate at the band centroids. Returns (band_mask,
    yielded_within_band) — both over ALL cells for cell-data rendering."""
    band = st["pinfo"]["band"]
    cen = np.asarray(st["eta0"].coords)[band]
    E = st["stokes"].strainrate
    c = [np.asarray(uw.function.evaluate(E[i, j], cen)).ravel()
         for i, j in ((0, 0), (1, 1), (0, 1))]
    d = 0.5 * (c[0] + c[1])
    e2 = np.sqrt(0.5 * ((c[0] - d) ** 2 + (c[1] - d) ** 2) + c[2] ** 2)
    yielded = np.zeros(len(band), dtype=bool)
    yielded[np.flatnonzero(band)] = (2.0 * st["eta0_vals"][band] * e2
                                     > st["tau_y"])
    return band, yielded
