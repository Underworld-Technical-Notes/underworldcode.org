"""The SPLIT rig solved through the partition seam, against serial, the
fine grid and the TI model: stress and slip.

Two stages, as the other parallel figures. Under mpirun (or serial) the
rig is built in the realisation and seam mode asked for, solved (the
frictionless contact solve for the split, the weak plane for TI), the
stress COMPONENTS are recovered to continuous P1 (sf_fields' recipe,
invariant formed nodally) and every rank dumps its P1 mesh, the stress,
its seam vertices and the NATIVE slip along each strand: the tangential
pair jump on the cut (split), the tangential velocity jump across the
band (TI). In serial the dumps are rendered side by side.

    ../../uwrun sf_split_seam_viz.py -uw_rep split -uw_res coarse                  # serial
    ../../uwrun sf_split_seam_viz.py -uw_rep split -uw_res fine
    ../../uwrun -np 2 sf_split_seam_viz.py -uw_rep split -uw_res fine -uw_seams conform
    ../../uwrun sf_split_seam_viz.py -uw_rep ti -uw_res fine
    ../../uwrun sf_split_seam_viz.py -uw_render 1
        ->  sf_split_seam_logtau_slip.png   (fields, trace coloured by slip)
            sf_split_seam_slip_profiles.png (slip along the Main, four cases)
"""
import glob

import numpy as np
import underworld3 as uw

params = uw.Params(
    uw_rep=uw.Param("split", "split | ti"),
    uw_res=uw.Param("coarse", "coarse | fine | superfine"),
    uw_seams=uw.Param("gather", "gather | ligament | conform"),
    uw_render=uw.Param(0.0, "1 = render the dumps (serial)"),
    uw_np=uw.Param(2.0, "render: the np of the parallel split dump"),
    uw_carve_clearance=uw.Param(1.0, "build() carve_clearance (fine: 1.0)"),
    uw_eta1=uw.Param(1e-3, "TI weak shear viscosity in the footprints"),
    uw_tol=uw.Param(1e-5, "stokes tolerance"),
    uw_splay_gap_rungs=uw.Param(-1.0, "the Splay's stop-short gap from the "
                                "Main in rungs (rig default when < 0); 0 = "
                                "a genuine FORK, the band's own junction "
                                "(the cut cannot take touching strands)"),
    uw_cont_gap_rungs=uw.Param(-1.0, "the upper stepover's tip-to-tip gap "
                               "in rungs (rig default when < 0); 1 = the "
                               "split's floor, one uncut edge; 0 = the "
                               "CONTINUOUS control, one cut the whole "
                               "line, no Cont strand"),
    uw_strands=uw.Param("all", "all | main | main+splay (the Main alone: no "
                        "fork, so the band and the cut represent the SAME "
                        "structure; with the Splay: the junction and its "
                        "partition; sf_main_only_convergence.py and "
                        "sf_main_splay_junction.py draw those dumps)"),
)
import rig_geometry as G
import sf_fields as F

REP, RES, SEAMS = str(params.uw_rep), str(params.uw_res), str(params.uw_seams)
STRANDS = str(params.uw_strands)
GAP = float(params.uw_splay_gap_rungs)
if GAP >= 0.0:
    G.SPLAY_GAP_RUNGS = GAP
CONT = float(params.uw_cont_gap_rungs)
if CONT >= 0.0:
    G.CONT_GAP_RUNGS = CONT
H_BG = 1 / 8


def dump_name(rep, res, seams, np_, rank, eta1=None):
    """TI dumps carry the weak viscosity when it is not the default: the
    band's interface strength is eta_1 / w, so a width sweep at fixed
    eta_1 doubles the strength each halving — a convergence test holds
    the ratio."""
    tag = "" if (eta1 is None or rep != "ti" or abs(eta1 - 1e-3) < 1e-12) \
        else f"_eta{eta1:g}"
    if STRANDS == "main":
        tag += "_main"
    elif STRANDS == "main+splay":
        tag += "_mainsplay"
    if GAP >= 0.0:
        tag += f"_gap{GAP:g}"
    if CONT >= 0.0:
        tag += f"_cont{CONT:g}"
    return f"fields_{rep}_{res}_{seams}_np{np_}_rank{rank}{tag}.npz"


if float(params.uw_render) < 0.5:
    from mpi4py import MPI
    import underworld3.visualisation as vis
    from underworld3.utilities import fault_contact
    from underworld3.utilities.place_surface import _shared_point_flags
    comm = MPI.COMM_WORLD
    W, S_F = G.RES[RES]
    traces = G.traces(S_F, W)
    keep = {"main": ("Main",), "main+splay": ("Main", "Splay")}.get(STRANDS)
    if keep is not None:
        traces = [tr for tr in traces if tr[0] in keep]
    base = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), cellSize=H_BG,
        regular=False, qdegree=2, refinement=1)
    net = uw.meshing.FaultNetwork(
        [(lbl, np.asarray(P, dtype=float)) for lbl, P in traces],
        hierarchy=[lbl for lbl, _ in traces])
    net.prepare(h=S_F, ligament=1.0, verbose=False)
    mesh = net.build(base=base, h_far=H_BG / 2, width=W, realisation=REP,
                     max_levels=1, margin_rings=2, seams=SEAMS,
                     carve_clearance=float(params.uw_carve_clearance))
    x, y = mesh.X
    tag = f"{REP[0]}{RES[0]}"
    v = uw.discretisation.MeshVariable(f"v{tag}", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable(f"p{tag}", mesh, 1, degree=1,
                                       continuous=True)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    eta0 = uw.discretisation.MeshVariable(f"eta0{tag}", mesh, 1, degree=0)
    eta0_vals = np.ones(len(np.asarray(eta0.coords)))
    eta0.array[:, 0, 0] = eta0_vals
    st = dict(rep=REP, mesh=mesh, stokes=stokes, v=v, eta0=eta0,
              eta0_vals=eta0_vals, eta1=None, ndir=None, foot=None,
              traces=traces, W=W, s_f=S_F)
    if REP == "ti":
        eta1, ndir, foot = G.ti_fields(mesh, net.info["footprints"],
                                       float(params.uw_eta1), eta0_vals, tag,
                                       w=W, traces_=traces)
        stokes.constitutive_model = \
            uw.constitutive_models.TransverseIsotropicFlowModel
        P = stokes.constitutive_model.Parameters
        P.shear_viscosity_0 = eta0.sym[0]
        P.shear_viscosity_1 = eta1.sym[0]
        P.director = ndir.sym
        st.update(eta1=eta1, ndir=ndir, foot=foot)
    else:
        stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
        stokes.constitutive_model.Parameters.shear_viscosity_0 = eta0.sym[0]
    stokes.bodyforce = [0.0, 0.0]
    ES, ET = G.ES, G.ET
    t_sym = (x - 0.5) * float(ET[0]) + (y - 0.5) * float(ET[1])
    for wall in ("Bottom", "Top", "Left", "Right"):
        stokes.add_dirichlet_bc((2.0 * t_sym * float(ES[0]),
                                 2.0 * t_sym * float(ES[1])), wall)
    stokes.petsc_use_pressure_nullspace = True
    stokes.tolerance = float(params.uw_tol)
    if REP == "split":
        for lbl, _tr in traces:
            stokes.add_fault_bc(0, boundary=lbl)
        info = fault_contact.solve_with_fault(stokes)
        converged = bool(info.get("converged"))
    else:
        stokes.solve()
        info = None
        converged = stokes.snes.getConvergedReason() > 0
    S_t, txx, tyy, txy = F.nodal_stress(st, name="tP1")
    tau = F.stress_invariant(txx, tyy, txy)

    # the NATIVE slip along each strand, made global. Split: every
    # coincident pair's tangential jump, all-gathered (rank-owned pairs
    # only, so the seam pair is counted once). TI: the tangential velocity
    # jump across band + one-cell skirt, counted where this rank owns both
    # probes (evaluate answers for unowned points by extrapolation).
    slip_profiles = {}
    if REP == "split":
        # SIGNED: the tangential jump v_plus - v_minus projected on the
        # trace's own direction at the nearest trace vertex; Plus is the
        # left of that direction (add_fault orients the chain by the
        # polyline), the same convention as the band's left-minus-right.
        # POSITIVE IS RIGHT-LATERAL (dextral), negative left-lateral, and
        # the sign does not depend on the way the trace is walked
        # (reversing it swaps left and right and flips t together).
        from scipy.spatial import cKDTree
        for lbl, tr in traces:
            coords, jumps, normals = fault_contact.fault_pair_jumps(
                stokes, lbl, stokes._rotated_freeslip_info, gather=True)
            if len(coords) == 0:
                continue
            P = np.asarray(tr, dtype=float)
            t = np.gradient(P, axis=0)
            t /= np.linalg.norm(t, axis=1)[:, None]
            near = cKDTree(P).query(coords)[1]
            tang = np.einsum("ij,ij->i", jumps, t[near])
            slip_profiles[lbl] = np.column_stack(
                [coords, tang, np.ones(len(tang))])
    else:
        from scipy.spatial import cKDTree
        # the TI record: the shear strain rate resolved on the director
        # plane along the mid-line, at the spine vertices (P1-recovered
        # components) — a strain rate, no span, continuous through a
        # junction. The velocity-jump gauge across band + skirt is kept
        # for the peak numbers only (a span one cell wide wanders in
        # location and, past a junction, into the neighbouring band).
        midline = {}
        for lbl, tr in traces:
            Pm, rate = F.midline_shear_rate(st, tr)       # collective
            midline[lbl] = np.column_stack([Pm, rate])

        def global_slip(P):
            t = np.gradient(P, axis=0)
            t /= np.linalg.norm(t, axis=1)[:, None]
            n = np.column_stack([-t[:, 1], t[:, 0]])
            # the band's OWN edges, no skirt: the layer's shear is a triangle
            # peaked at the mid-line that reaches the rails (the transect
            # probe, 2026-09-05: the jump across +-W/2 is within 3-6% of the
            # jump across +-(W/2 + s_f)), and a probe on the rail cannot
            # wander into a neighbouring band the mask keeps W away
            skirt = W / 2
            Qp, Qm = P + skirt * n, P - skirt * n
            vp = np.asarray(uw.function.evaluate(v.sym, Qp)).reshape(len(P), -1)[:, :2]
            vm = np.asarray(uw.function.evaluate(v.sym, Qm)).reshape(len(P), -1)[:, :2]
            slip = np.einsum("ij,ij->i", vp - vm, t)     # SIGNED: left - right
            own = ((mesh._robust_owning_cells(np.ascontiguousarray(Qp)) >= 0)
                   & (mesh._robust_owning_cells(np.ascontiguousarray(Qm)) >= 0))
            # gathered by the owning rank: the value where owned, and a
            # count, so the sign survives (a MAX would not keep it)
            val = np.where(own, slip, 0.0)
            cnt = own.astype(float)
            comm.Allreduce(MPI.IN_PLACE, val, op=MPI.SUM)
            comm.Allreduce(MPI.IN_PLACE, cnt, op=MPI.SUM)
            out = np.where(cnt > 0, val / np.maximum(cnt, 1.0), np.nan)
            return out

        from scipy.spatial import cKDTree
        all_traces = [np.asarray(tr, dtype=float) for _l, tr in traces]
        # the Main and its Cont segment are ONE line: the gauge must not
        # mask the Main's samples as "inside the Cont's band" at a closed
        # stepover, or the tube shows a nick where the band has none
        ONE_LINE = {"Main", "Cont"}
        for k, (lbl, tr) in enumerate(traces):
            P = np.asarray(tr, dtype=float)[::2]
            others = [q for j, (l2, q) in enumerate(zip([l for l, _ in traces],
                                                        all_traces))
                      if j != k and not (lbl in ONE_LINE and l2 in ONE_LINE)]
            clear = (cKDTree(np.vstack(others)).query(P)[0] > W if others
                     else np.ones(len(P), dtype=bool))
            # the raw jump everywhere, and whether the trace point is
            # clear of every other strand's band (column 3): the render
            # masks with it, the junction studies show it
            slip = global_slip(P)
            slip_profiles[lbl] = np.column_stack([P, slip, clear.astype(float)])

    # the P1 stress on the mesh's OWN cells (a split mesh must never be
    # re-triangulated through its DOF cloud: the slit would close)
    pvm = vis.mesh_to_pv_mesh(mesh).cast_to_unstructured_grid()
    dm = mesh.dm
    vS, vE = dm.getDepthStratum(0)
    pStart, _ = dm.getChart()
    shared = _shared_point_flags(dm).astype(bool)[vS - pStart: vE - pStart]
    from underworld3.utilities.reconnect import _coords
    Xv = _coords(dm)[: vE - vS]
    # S_t is P1: one DOF per vertex in the DM's vertex order, which is
    # also the pv mesh's point order — the split's coincident vertices
    # keep their own DOFs, one per side
    tau = np.asarray(tau).ravel()
    if len(tau) != vE - vS:
        raise RuntimeError("the P1 stress does not have one DOF per vertex")
    logtau = np.log10(tau + 1e-12)
    slips = np.vstack([np.vstack([sp, [np.nan] * 4])
                       for sp in slip_profiles.values()]) \
        if slip_profiles else np.zeros((0, 4))
    labels = list(slip_profiles)
    if REP == "ti":
        midline_arr = np.vstack([np.vstack([mp, [np.nan] * 3])
                                 for mp in midline.values()])
        midline_labels = list(midline)
    else:
        midline_arr, midline_labels = np.zeros((0, 3)), []
    np.savez(dump_name(REP, RES, SEAMS, comm.size, comm.rank,
                       eta1=float(params.uw_eta1)),
             points=np.asarray(pvm.points),
             cells=np.asarray(pvm.cells, dtype=np.int64),
             celltypes=np.asarray(pvm.celltypes, dtype=np.uint8),
             logtau=logtau,
             shared_xy=Xv[shared],
             traces=np.vstack([np.vstack([tr, [np.nan, np.nan]])
                               for _l, tr in traces]),
             slips=slips, slip_labels=np.asarray(labels),
             midline=midline_arr, midline_labels=np.asarray(midline_labels))
    peaks = {lbl: float(np.nanmax(np.where(sp[:, 3] > 0, np.abs(sp[:, 2]), np.nan)))
             for lbl, sp in slip_profiles.items()}
    if REP == "ti":
        uw.pprint("mid-line 2 e_nt peaks: " + ", ".join(
            f"{lbl}: {float(np.nanmax(mp[:, 2])):.2f}" for lbl, mp in midline.items()))
    uw.pprint(f"[{REP} {RES} {SEAMS} np{comm.size}] converged {converged}; "
              f"cells {comm.gather(int(dm.getHeightStratum(0)[1]))}; "
              f"peak slip {{ {', '.join(f'{k}: {v_:.4f}' for k, v_ in peaks.items())} }}; dumped")
else:
    import pyvista as pv
    pv.OFF_SCREEN = True
    NP = int(float(params.uw_np))
    import re

    def ranks_of(pattern):
        # the rank wildcard must not pick up the Main-only / Main+Splay /
        # other-eta dumps, whose names carry a suffix after the rank and
        # whose MESHES differ (three meshes drawn over each other dappled
        # the zoomed field)
        return sorted(f for f in glob.glob(pattern)
                      if re.search(r"rank\d+\.npz$", f))

    cases = [("split, coarse, serial",
              ranks_of(dump_name("split", "coarse", "gather", 1, "*"))),
             ("split, fine, serial",
              ranks_of(dump_name("split", "fine", "gather", 1, "*"))),
             (f"split, fine, np={NP} through the seam",
              ranks_of(dump_name("split", "fine", "conform", NP, "*"))),
             ("TI weak plane, fine, serial",
              ranks_of(dump_name("ti", "fine", "gather", 1, "*")))]
    for title, files in cases:
        if not files:
            raise SystemExit(f"no dump for {title}: run the dump stage first")
    seam = np.vstack([np.load(f, allow_pickle=True)["shared_xy"]
                      for f in cases[2][1]])
    seam = seam[np.linalg.norm(seam - 0.5, axis=1) < 0.2]
    czoom = seam.mean(axis=0) if len(seam) else np.array([0.5, 0.5])
    VIEWS = [((0.5, 0.5), 0.54, ""),
             ((czoom[0], czoom[1]), 0.12, " — the Main's seam crossing")]
    allv = np.concatenate([np.load(f, allow_pickle=True)["logtau"]
                           for _t, fs in cases for f in fs])
    clim = (float(np.percentile(allv, 2)), float(np.percentile(allv, 99.5)))
    # the trace colour is the SIGNED slip (positive dextral) in the one
    # currency for both representations — the pair jump on the cut, the
    # jump across the band's own edges — on a diverging map, neutral grey
    # at zero, blue sinistral and green dextral (both stand off the magma
    # stress), symmetric about zero
    # two-slope: zero stays at the map's centre, each sense scaled to its
    # own extreme (a symmetric range left the sinistral lobes, a twentieth
    # of the Main's dextral slip, invisible)
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    SLIP_CMAP = LinearSegmentedColormap.from_list(
        "slip_sense", ["#1f4fbf", "#7aa6ff", "#d9d9d9", "#7fe07a", "#118a2e"])
    allslip = np.concatenate([np.load(fs[0], allow_pickle=True)["slips"][:, 2]
                              for _t, fs in cases])
    allslip = allslip[np.isfinite(allslip)]
    slip_lo = min(float(allslip.min()), -1e-6)
    slip_hi = max(float(allslip.max()), 1e-6)
    SLIP_NORM = TwoSlopeNorm(vcenter=0.0, vmin=slip_lo, vmax=slip_hi)
    slip_ticks = {0.0: f"{slip_lo:.3f}", 0.25: f"{slip_lo / 2:.3f}", 0.5: "0",
                  0.75: f"{slip_hi / 2:.2f}", 1.0: f"{slip_hi:.2f}"}
    pl = pv.Plotter(off_screen=True, shape=(len(VIEWS), len(cases)),
                    window_size=(1000 * len(cases), 1000 * len(VIEWS)),
                    border=False)
    for j, (title, files) in enumerate(cases):
        for i, ((cx, cy), scale, ztag) in enumerate(VIEWS):
            pl.subplot(i, j)
            pl.set_background("white")
            for f in files:
                d = np.load(f, allow_pickle=True)
                pvm = pv.UnstructuredGrid(d["cells"], d["celltypes"], d["points"])
                pvm.point_data["logtau"] = d["logtau"]
                pl.add_mesh(pvm, scalars="logtau", cmap="magma", clim=clim,
                            show_edges=False, lighting=False,
                            show_scalar_bar=(i == 0 and j == 0),
                            scalar_bar_args=dict(title="log10 tau_II", n_labels=4,
                                                 color="black", vertical=True,
                                                 position_x=0.86, position_y=0.05))
                if i > 0:
                    pl.add_mesh(pvm.extract_all_edges(), color="white",
                                line_width=0.4, opacity=0.35, lighting=False)
                if len(d["shared_xy"]):
                    pl.add_points(np.column_stack(
                        [d["shared_xy"], np.full(len(d["shared_xy"]), 0.003)]),
                        color="black", point_size=4 if i == 0 else 8,
                        render_points_as_spheres=True)
            # the trace colour is each representation's OWN currency: the
            # pair jump on the cut (split), the mid-line resolved shear
            # strain rate 2 e_nt (TI) — two scalar bars. Rank 0's dump
            # carries the profiles. Split pairs are unordered along the
            # cut: order each strand's samples by their projection onto
            # the trace's mean tangent.
            d0 = np.load(files[0], allow_pickle=True)
            sp_all = d0["slips"]
            for seg in np.split(sp_all, np.flatnonzero(np.isnan(sp_all[:, 0]))):
                seg = seg[~np.isnan(seg[:, 0])]
                if len(seg) < 2:
                    continue
                t = seg[:, :2] - seg[:, :2].mean(axis=0)
                _u, _s, vt = np.linalg.svd(t, full_matrices=False)
                order = np.argsort(t @ vt[0])
                seg = seg[order]
                vals = np.where(np.isfinite(seg[:, 2]), seg[:, 2], 0.0)
                if seg.shape[1] > 3:
                    vals = np.where(seg[:, 3] > 0, vals, 0.0)
                line = pv.lines_from_points(np.column_stack(
                    [seg[:, :2], np.full(len(seg), 0.004)]))
                key = "slip rate (signed; + dextral)"
                line.point_data[key] = np.asarray(SLIP_NORM(vals), dtype=float)
                pl.add_mesh(line, scalars=key, cmap=SLIP_CMAP, clim=(0.0, 1.0),
                            line_width=6, lighting=False,
                            render_lines_as_tubes=True,
                            show_scalar_bar=(i == 0 and j == 1),
                            annotations=slip_ticks,
                            scalar_bar_args=dict(title=key, n_labels=0,
                                                 color="black", vertical=True,
                                                 position_x=0.86,
                                                 position_y=0.45))
            pl.add_text(f"{title}{ztag}", font_size=11, color="black",
                        position="upper_left")
            pl.view_xy()
            pl.camera.parallel_projection = True
            pl.camera.focal_point = (cx, cy, 0.0)
            pl.camera.parallel_scale = scale
    out = "sf_split_seam_logtau_slip.png"
    pl.screenshot(out)
    pl.close()
    print(f"wrote {out}")

    # CONVERGENCE of the band to the cut, along the Main, in ONE
    # currency — the velocity jump across the band's own edges for TI,
    # the pair jump on the cut for the split (the integral of the
    # resolved strain rate across the layer, either way): every split
    # and TI dump on disk, by width.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def along(seg):
        t = seg[:, :2] - np.asarray(G.C)
        s_ = t @ G.ES
        o = np.argsort(s_)
        return s_[o], np.abs(seg[o, 2])

    def strand(d0, name):
        labels = list(d0["slip_labels"])
        arr = d0["slips"]
        segs = [q[~np.isnan(q[:, 0])] for q in
                np.split(arr, np.flatnonzero(np.isnan(arr[:, 0])))]
        segs = [q for q in segs if len(q)]
        return segs[labels.index(name)]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    widths = {"coarse": G.RES["coarse"][0], "fine": G.RES["fine"][0],
              "superfine": G.RES["superfine"][0]}
    conv = [("split", "coarse", None, "C0-", 1.2),
            ("split", "fine", None, "C0-", 1.8),
            ("split", "superfine", None, "k-", 2.4),
            ("ti", "fine", 1e-3, "C2--", 1.6),
            ("ti", "superfine", 1e-3, "C3--", 1.6),
            ("ti", "fine", 5e-4, "C2-.", 1.6),
            ("ti", "superfine", 5e-4, "C3-.", 2.2)]
    peaks = []
    for rep, res, eta1, sty, lw in conv:
        files = sorted(f for f in glob.glob(dump_name(rep, res, "gather", 1, "*",
                                                      eta1=eta1))
                       if re.search(r"rank\d+\.npz$", f))
        if not files:
            continue
        d0 = np.load(files[0], allow_pickle=True)
        s_, v_ = along(strand(d0, "Main"))
        if rep == "split":
            name = f"split, w = {widths[res]}"
        else:
            name = (f"TI band, w = {widths[res]}, eta_1 = {eta1:g} "
                    f"(eta_1/w = {eta1 / widths[res]:g})")
        ax.plot(s_, v_, sty, lw=lw, label=name)
        peaks.append((name, float(np.nanmax(v_))))
    files = sorted(glob.glob(dump_name("split", "fine", "conform", NP, "*")))
    if files:
        d0 = np.load(files[0], allow_pickle=True)
        s_, v_ = along(strand(d0, "Main"))
        ax.plot(s_, v_, "C0:", lw=1.4,
                label=f"split, w = {widths['fine']}, np={NP} through the seam")
    ax.set_xlabel("along the Main (from its centre)")
    ax.set_ylabel("slip rate: pair jump (split) / v_t jump across the band (TI)")
    ax.set_ylim(0, None)
    ax.set_title("The TI band against the split node along the Main: "
                 "the width halved at fixed eta_1 and at fixed eta_1/w",
                 fontsize=10)
    ax.legend(frameon=False, fontsize=7, loc="lower center")
    fig.tight_layout()
    for name, pk in peaks:
        print(f"peak on the Main  {name}: {pk:.4f}")
    out2 = "sf_split_seam_slip_profiles.png"
    fig.savefig(out2, dpi=160)
    print(f"wrote {out2}")
