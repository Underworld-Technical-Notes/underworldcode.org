"""The S-fault rig's geometry of record — ONE source for every script.

Adjust the dials here; geometry_preview.py renders them, s_fault.py
solves them, sf_viz.py / sf_compare_viz.py draw them.

Strands:
  Main   — the tanh S on the 40° diagonal (the San Andreas analogue);
           also the TERRANE boundary (strong above/left of its line).
  Branch — the through-line alternative in the WEAK block (tip-to-tip
           near-join with the bend; the San Jacinto analogue).
  Splay  — the Y near-join in the TOUGH layer: a short strand leaving
           the outgoing limb's side at SPLAY_PHI into the strong block,
           stopped short (tip-to-SIDE junction). The trace gap is the
           junction physics (the intact-gap linkage); it KISSES the main
           (gap w/2) so the mesh surround must interact — placed as one
           fused network with the main line (see SPLAY_GAP note). In TI
           the two weak zones merge at the Y (one director per cell:
           paint order decides — the #544 caveat); split keeps two cuts
           and an intact sliver.
  Cont   — a near-touching SEGMENT of the main fault along its
           continuation line beyond the upper tip (tip-to-tip stepover,
           the California fault-database segmentation pattern). Same
           near-touching gap as the Y; same test from the other
           direction: collinear instead of oblique.
"""
import numpy as np

# ----------------------------------------------------------------- dials
THETA = np.deg2rad(40.0)     # strike of the diagonal baseline
C = np.array([0.5, 0.5])     # baseline centre
A = 0.05                     # S half-step
LAM = 0.10                   # bend length scale (tanh)
S_MAIN = (-0.42, 0.42)       # main-trace arc range (blind tips)
S_BRANCH = (0.06, 0.42)      # branch: through-line at t = -A
SPLAY_S0 = 0.06              # splay leaves the main line near this s —
                             # just past the bend's centre, so at +22 deg it
                             # CONTINUES the bend's turning (Louis, final
                             # pass 2026-08-26: "more of a continuation of
                             # the curved segment; shift it left")
SPLAY_GAP_RUNGS = 1.0        # trace-to-trace gap at the Y in RUNGS (s_f):
                             # KISSING = one rung at any resolution
                             # (a fixed 0.015 was w/2 at coarse but 1.5 w
                             # at fine). traces(s_f) sets SPLAY_GAP.
SPLAY_GAP = 0.010            # (derived; the coarse value) KISSING (w/2
                             # at coarse; Louis's geometry of record).
                             # Any gap: the whole rig is ONE network
                             # placement (fused ribbons + embedded
                             # spines, place_thin_volume mesher=
                             # "network"); junctions are free and the
                             # cuts walk exact vertices.
SPLAY_PHI = np.deg2rad(22.0) # splay divergence from local strike, +t side
SPLAY_LEN = 0.18             # splay length
EE_N = 3                     # EN-ECHELON: the splay + 2 more parallel
EE_LATERAL = 0.08            #   segments: in the SPLAY's own frame, each
EE_ALONG = 0.05              #   start = previous + EE_LATERAL n_sp (across
                             #   the strands, up-left into the strong block)
                             #   + EE_ALONG d_sp (forward along the strand).
                             #   Louis 2026-08-26 (3rd pass): the array
                             #   climbs UP as it goes LEFT; spacing 0.058;
                             #   only #1 kisses the main
STEP_S = (-0.53, -0.37)      # STEPOVER at the main's LOWER (clean) tip: a
STEP_OFF = 0.035             #   segment parallel to the lower limb, offset
                             #   STEP_OFF (ABSOLUTE — the same geometry at
                             #   both resolutions; Louis: "close, hard to
                             #   separate") into the WEAK block, overlapping
                             #   the tip (s=-0.42) by 0.05 and running 0.11
                             #   toward the wall (wall clearance limits it)
CONT_GAP_RUNGS = 1.0         # tip-to-tip stepover gap beyond the main's
                             # upper tip, in RUNGS (s_f), as the splay's:
                             # 1 = the split's floor (chains must be
                             # disjoint, so one uncut edge is the least
                             # it can leave); 0 = the CONTINUOUS control,
                             # one cut the whole line. traces(s_f) sets
                             # CONT_GAP. It was an absolute 0.015, which
                             # refinement walked AWAY from the floor (2
                             # edges coarse, 6 superfine) — the test the
                             # segment exists for is that the band closes
                             # a gap the cut cannot. None = leave CONT_GAP
                             # as set (the absolute dial of older probes).
CONT_GAP = 0.015             # (derived; the coarse value) tip-to-tip
                             # stepover, near-touching, California-DB
                             # style. Placeable at ANY value: the
                             # Main-line family shares ONE band
                             # (main_line_union), so the gap lives only
                             # in the cuts + paint.
CONT_LEN = 0.10              # continuation-segment length along the line
                             # (0.18 put the extended band's cavity into
                             # the top-right wall — interior clearance)
# -----------------------------------------------------------------------

ES = np.array([np.cos(THETA), np.sin(THETA)])
ET = np.array([-np.sin(THETA), np.cos(THETA)])
RES = {"coarse": (0.03, 0.01), "fine": (0.01, 0.005),
       "superfine": (0.005, 0.0025)}                    # (w, s_f)
W_OF_SF = {sf: w for w, sf in RES.values()}             # s_f -> w


def main_curve(s):
    s = np.atleast_1d(s)
    return C + s[:, None] * ES + (A * np.tanh(s / LAM))[:, None] * ET


def resample_arclength(P, spacing):
    """Equispaced-in-arclength, ends kept, interval count EVEN."""
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(round(arc[-1] / spacing)))
    n += n % 2
    si = np.linspace(0.0, arc[-1], n + 1)
    return np.column_stack([np.interp(si, arc, P[:, 0]),
                            np.interp(si, arc, P[:, 1])])


def splay_line(k=0):
    """En-echelon strand k (k=0 is THE splay, kissing the main): from a
    stop-short start beside the outgoing limb, diverging into the
    strong block; strand k starts EE_STEP back along strike and out."""
    t0 = float(A * np.tanh(SPLAY_S0 / LAM))
    # local strike of the main line at SPLAY_S0
    sech2 = 1.0 / np.cosh(SPLAY_S0 / LAM) ** 2
    tan_l = ES + (A / LAM) * sech2 * ET
    tan_l /= np.linalg.norm(tan_l)
    nrm_l = np.array([-tan_l[1], tan_l[0]])          # +t side
    if nrm_l @ ET < 0:
        nrm_l = -nrm_l
    d = np.cos(SPLAY_PHI) * tan_l + np.sin(SPLAY_PHI) * nrm_l
    n_sp = np.array([-d[1], d[0]])                    # up-left of the strand
    start = (C + SPLAY_S0 * ES + t0 * ET + SPLAY_GAP * nrm_l
             + k * (EE_LATERAL * n_sp + EE_ALONG * d))
    return np.array([start, start + SPLAY_LEN * d])


def stepover_line(w=None):
    """The stepover at the main's lower tip: parallel to the lower limb
    (t = -A there), offset STEP_OFF (absolute) into the weak block."""
    ss = np.linspace(*STEP_S, 500)
    return C + ss[:, None] * ES - (A + STEP_OFF) * ET


def main_line_union(s_f):
    """The Main-line family as ONE parametrisation — the library's rule
    for close pairs ('surfaces must be separated by at least a cell;
    place close pairs as one thin volume instead'): one ladder polyline
    over the WHOLE line, with the Main and Cont cut chains as vertex
    SUBCHAINS of it (#595: nothing snaps — cuts consume the spine's own
    vertices, so chains and band must share them). The stepover gap
    therefore lives only in the cuts and the paint, and can close below
    the placement floor. Returns (union, main_chain, cont_chain);
    chain ends are vertex-quantised, so the realised gap is the nearest
    ≥ CONT_GAP the sampling allows."""
    s_end = S_MAIN[1] + CONT_GAP + CONT_LEN
    sm = np.linspace(S_MAIN[0], s_end, 4000)
    union = resample_arclength(main_curve(sm), s_f)
    if CONT_GAP <= 0.0:
        # the CONTINUOUS control: no stepover — one cut, the whole line
        return union, union, union[:0]
    s_along = (union - C) @ ES
    # the gap in SPINE EDGES (distance thresholds are at the mercy of
    # vertex phase): n_edges=1 -> abutting chains, one uncut edge;
    # n_edges=2 -> one free bridge vertex; realised gap = n_edges rungs
    i_tip = int(np.searchsorted(s_along, S_MAIN[1] + 1e-9)) - 1
    rung = float(np.linalg.norm(np.diff(union, axis=0), axis=1).mean())
    n_edges = max(1, int(round(CONT_GAP / rung)))
    return union, union[:i_tip + 1], union[i_tip + n_edges:]


def traces(s_f, w=None):
    """The rig's strands, sampled at the rung scale — [(label, points)]:
    Main, Branch, Splay (+ Splay2, Splay3 en echelon), Step (the lower
    stepover), Cont (the upper stepover segment, if the gap is open).
    Main and Cont are subchains of the shared main_line_union spine."""
    global SPLAY_GAP, CONT_GAP
    SPLAY_GAP = SPLAY_GAP_RUNGS * s_f
    if CONT_GAP_RUNGS is not None:
        CONT_GAP = CONT_GAP_RUNGS * s_f
    w = W_OF_SF[s_f] if w is None else w
    _union, main, cont = main_line_union(s_f)
    sb = np.linspace(*S_BRANCH, 2000)
    branch = resample_arclength(C + sb[:, None] * ES - A * ET, s_f)
    out = [("Main", main), ("Branch", branch)]
    for k in range(EE_N):
        sp = splay_line(k)
        seg = resample_arclength(
            np.linspace(0, 1, 200)[:, None] * (sp[1] - sp[0]) + sp[0], s_f)
        out.append(("Splay" if k == 0 else f"Splay{k + 1}", seg))
    out.append(("Step", resample_arclength(stepover_line(w), s_f)))
    if len(cont):
        out.append(("Cont", cont))
    return out


def strong_mask(points):
    """The terrane rule: True on the +t (strong) side of the fault line."""
    rel = np.asarray(points) - C
    return (rel @ ET) > A * np.tanh((rel @ ES) / LAM)


def receiver_normals(points):
    """Local fault-line orientation, continued off the line (for dCFF)."""
    rel = np.asarray(points) - C
    s_co = rel @ ES
    sech2 = 1.0 / np.cosh(s_co / LAM) ** 2
    n = ET[None, :] - (A / LAM) * sech2[:, None] * ES[None, :]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def ti_fields(mesh, foots, eta1_val, eta0_vals, tag, w=None, traces_=None):
    """The TI representation's P0 fields, painted on the wrapper's
    HONOURED footprints (the review-1 API): eta_1 = weak inside the
    fault footprints only, background elsewhere; per-cell directors
    following each strand's own orientation (curved Main and its Cont
    segment, ET-normal Branch, splay-normal Splay). Returns
    (eta1_var, dir_var, foot).

    With ``w`` and ``traces_`` given, the stepover corridor between the
    Main's tip and the Cont's start is painted too: a footprint stops
    half a rung past its tip, so a one-edge gap leaves a plug of a few
    intact cells in the band (4 at superfine) and the TI still has a
    gap. Two collinear segments of ONE line closer than the band is
    wide are one weak zone — that is the band's whole claim on the
    stepover, and the paint has to say it."""
    import underworld3 as uw

    foot = np.zeros_like(next(iter(foots.values())))
    for m_ in foots.values():
        foot = foot | m_
    eta1 = uw.discretisation.MeshVariable(f"etaT{tag}", mesh, 1, degree=0)
    cen_abs = np.asarray(eta1.coords)
    if w is not None and traces_ is not None:
        tr = dict(traces_)
        if "Main" in tr and "Cont" in tr:
            a, b = np.asarray(tr["Main"][-1]), np.asarray(tr["Cont"][0])
            d = b - a
            L = float(np.linalg.norm(d))
            d = d / L
            rel = cen_abs - a
            along = rel @ d
            across = np.abs(rel @ np.array([-d[1], d[0]]))
            corridor = (along > -0.5 * L) & (along < 1.5 * L) & (across < 0.5 * w)
            n_new = int((corridor & ~foot).sum())
            foot = foot | corridor
            foots = dict(foots)
            foots["Main"] = foots["Main"] | corridor
            uw.pprint(f"[ti_fields] stepover corridor: {n_new} band cell(s) "
                      f"painted between the Main's tip and the Cont's start")
    eta1.array[:, 0, 0] = np.where(foot, eta1_val, eta0_vals)
    ndir = uw.discretisation.MeshVariable(f"dirT{tag}", mesh, 2, degree=0,
                                          continuous=False)
    cen = cen_abs - C
    s_co = cen @ ES
    dvals = np.tile(ET, (len(s_co), 1))
    sech2 = 1.0 / np.cosh(s_co / LAM) ** 2
    n_main = ET[None, :] - (A / LAM) * sech2[:, None] * ES[None, :]
    n_main /= np.linalg.norm(n_main, axis=1, keepdims=True)
    if "Main" in foots:
        dvals[foots["Main"]] = n_main[foots["Main"]]
    if "Cont" in foots:
        dvals[foots["Cont"]] = n_main[foots["Cont"]]
    sp = splay_line()
    d_sp = (sp[1] - sp[0]) / np.linalg.norm(sp[1] - sp[0])
    for lbl, m_ in foots.items():
        if lbl.startswith("Splay"):          # all en-echelon strands
            dvals[m_] = np.array([-d_sp[1], d_sp[0]])
    # "Step" and "Branch": strike-parallel -> the ET default
    ndir.array[...] = dvals.reshape(ndir.array.shape)
    return eta1, ndir, foot


# The drive is built by callers from mesh coordinates:
#   t_sym = (x - 0.5) * ET[0] + (y - 0.5) * ET[1]
#   v = sense * 2 * t_sym * ES        (plate-motion-frame shear)


def place_rig(base_mesh, s_f, width, margin_rings=2, split=True, uncut=()):
    """ONE placement path for the whole rig (Louis, 2026-08-25: no more
    parallel paths): every strand's extended spine goes into a single
    ``place_thin_volume(..., mesher="network")`` call — the ribbons are
    fused in CAD (junctions free, so the Y may kiss and the stepover
    shares its band) and every spine is EMBEDDED in the fused face, so
    the cuts walk exact vertices (#595) at any resolution. Cuts: ONE
    network add_fault call. Honoured footprints per strand by nearest
    sample over the concatenated spines. Returns (mesh, info)."""
    import underworld3 as uw
    from underworld3.utilities.place_surface import (
        place_thin_volume, _extend_polyline_2d, _footprint_from_samples)

    tr = traces(s_f, width)
    union, chain_main, chain_cont = main_line_union(s_f)
    m = margin_rings
    spines = [("MainLine", union)] + [(lbl, P) for lbl, P in tr
                                      if lbl not in ("Main", "Cont")]
    ext = [_extend_polyline_2d(np.asarray(P, dtype=float), m)
           for _n, P in spines]
    spacing = float(np.linalg.norm(np.diff(union, axis=0), axis=1).mean())
    dm, _ = place_thin_volume(base_mesh.dm, ext, width, label="Band",
                              label_value=71, clearance=0.3, size=spacing,
                              mesher="network")
    mesh = uw.discretisation.Mesh(
        dm, simplex=True, qdegree=base_mesh.qdegree,
        coordinate_system_type=base_mesh.CoordinateSystem.coordinate_type,
        boundaries=base_mesh.boundaries, verbose=False)
    # the placed mesh OWNS the base's MG tail + the band as FAC zone: every
    # solver on it (Stokes, rotated, projections, probes, renders) drives
    # FMG/FAC automatically — no per-solver set_custom_fmg, no silent GAMG
    from underworld3.utilities.custom_mg import adopt_hierarchy
    adopt_hierarchy(mesh, base_mesh,
                    fac_zone=mesh.cells_labelled("Band", 71))
    if split:
        # ``uncut``: strands left WITHOUT a cut (band only — the fused
        # control: no jump, no weld, by construction)
        mesh = mesh.add_fault([(lbl, np.asarray(P, dtype=float))
                               for lbl, P in tr if lbl not in uncut])
        mesh._custom_mg_fac_zone = None      # a split fault needs no patch
    band = mesh.cells_labelled("Band", 71)
    S_all = np.vstack(ext)
    off = np.cumsum([0] + [len(S) for S in ext])     # spine offsets
    def user(k, lo, hi):
        u = np.zeros(len(S_all), dtype=bool)
        u[off[k] + lo:off[k] + hi] = True
        return u
    foots = {"Main": _footprint_from_samples(
        mesh.dm, band, S_all, user(0, m, m + len(chain_main)))}
    if len(chain_cont):
        foots["Cont"] = _footprint_from_samples(
            mesh.dm, band, S_all,
            user(0, m + len(union) - len(chain_cont), m + len(union)))
    for k, (lbl, _P) in enumerate(spines[1:], start=1):
        foots[lbl] = _footprint_from_samples(
            mesh.dm, band, S_all, user(k, m, len(ext[k]) - m))
    # the extended spines (what the RIBBON covers) and the cut chains on
    # each (what the SPLIT sliced): their difference along the spine is
    # where the surface representation cannot join (Louis, 2026-08-27)
    cut_chains = {"MainLine": [c for c in (chain_main, chain_cont) if len(c)]}
    for lbl, P in spines[1:]:
        cut_chains[lbl] = [np.asarray(P, dtype=float)]
    return mesh, {"n_cells": int(mesh.dm.getHeightStratum(0)[1]),
                  "n_rungs": [len(P) for _n, P in spines],
                  "footprints": foots, "band": band,
                  "spines_ext": [(n_, E) for (n_, _P), E in zip(spines, ext)],
                  "cut_chains": cut_chains}
