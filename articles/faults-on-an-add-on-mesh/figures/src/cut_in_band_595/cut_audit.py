"""Does the centre-line cut work AS ADVERTISED? The audit.

Four claims, each checked directly on the mesh and the solution rather
than inherited from the listric study:

  1. The cut doubles vertices along the line: coincident pairs, exact to
     machine precision, ON the centreline, INSIDE the band.
  2. The sides are tangentially free: the deformed mesh (x + alpha v)
     shows a genuine sliding discontinuity along the slit.
  3. The sides stay joined normally: the no-opening constraint holds
     POINTWISE along the slit (profile, not just a max).
  4. The local re-triangulation is benign: cell quality and the zone
     label survive the surgery.

Solve once (free slit in the weak band, the winning configuration),
cache everything, render instantly thereafter.
"""
import os

import numpy as np

OUT = "/Users/lmoresi/+Simulations/ribbon_network_2d"


def solve_and_cache(path, cut_step=0.011):
    import sympy
    import underworld3 as uw
    import crossing_common as CC
    import viz
    from single_fault_resolution import build_single, DELTA_ORIENT, WIDTH
    from single_fault_cut import ZONE_SIZE, TIP_PULLBACK
    from isotropic_stress_reference import vertex_ordered

    mesh0, trace, inzone0, info = build_single(ZONE_SIZE)
    n_zone_before = int(inzone0.sum())

    a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
    t = (b - a) / np.linalg.norm(b - a)
    a2, b2 = a + TIP_PULLBACK * t, b - TIP_PULLBACK * t
    # Sample the cut at the ZONE's own node spacing, not the host cell
    # size. Each line point snaps its nearest vertex onto the line; at
    # 0.03 spacing one sample grabbed a RAIL vertex (only w/2 = 0.010
    # away) and pinched the band to zero width at that point. At ~0.011
    # the nearest vertex to every sample is a midline node (<= 0.004
    # off the line) and the rails are never touched.
    step = float(cut_step)
    npts = max(2, int(round(np.linalg.norm(b2 - a2) / step)) + 1)
    line = a2 + np.linspace(0, 1, npts)[:, None] * (b2 - a2)

    mesh = mesh0.add_fault(("Fault", line))
    cS, cE = mesh.dm.getHeightStratum(0)
    weak = np.zeros(cE - cS, dtype=bool)
    for pt in mesh.dm.getLabel("Zone").getStratumIS(31).getIndices():
        if cS <= int(pt) < cE:
            weak[int(pt) - cS] = True

    v = uw.discretisation.MeshVariable("V", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=0,
                                       continuous=False)
    e1 = uw.discretisation.MeshVariable("e1", mesh, 1, degree=0,
                                        continuous=False)
    e1.array[:, 0, 0] = np.where(weak, 1.0e-3, 1.0)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = e1.sym[0]
    stokes.bodyforce = sympy.Matrix([0, 0])
    stokes.add_dirichlet_bc((-0.5, None), "Left")
    stokes.add_dirichlet_bc((+0.5, None), "Right")
    stokes.add_dirichlet_bc((None, 0.0), "Bottom")
    nrm = CC.normals(DELTA_ORIENT)[0]
    stokes.add_fault_bc(1.0e-8, boundary="Fault",
                        normal=sympy.Matrix([[float(nrm[0]),
                                              float(nrm[1])]]))
    stokes._rotated_use_lu = True
    stokes.tolerance = 1e-8
    stokes.solve()

    # vertex velocities for the deformed-mesh view (P1 projection)
    comps = {}
    for i, name in enumerate(("vx", "vy")):
        var = uw.discretisation.MeshVariable(name, mesh, 1, degree=1)
        proj = uw.systems.Projection(mesh, var)
        proj.uw_function = v.sym[i]
        proj.smoothing = 0.0
        proj.solve()
        comps[name] = vertex_ordered(mesh, var)

    # the pairing, in full
    from underworld3.utilities import fault_contact
    coords, jumps, nvecs = fault_contact.fault_pair_jumps(
        stokes, "Fault", stokes._rotated_freeslip_info)

    surf = viz.pv_cells(mesh)
    np.savez(path,
             points=np.asarray(surf.points), faces=np.asarray(surf.faces),
             vx=comps["vx"], vy=comps["vy"], inzone=weak,
             pair_coords=coords, pair_jumps=jumps, pair_normals=nvecs,
             trace_a=np.asarray(trace), cut_line=line,
             n_zone_before=float(n_zone_before),
             width=float(WIDTH), delta=float(DELTA_ORIENT))
    print(f"cached -> {path}", flush=True)


def audit(z):
    pts = np.asarray(z["points"])[:, :2]
    faces = np.asarray(z["faces"]).reshape(-1, 4)[:, 1:]
    w = float(z["width"])
    tr = np.asarray(z["trace_a"])
    a, b = tr[0], tr[-1]
    t = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-t[1], t[0]])

    # ---- claim 1: coincident pairs, on the line, in the band
    order = np.lexsort((pts[:, 1], pts[:, 0]))
    ps = pts[order]
    same = np.all(np.abs(np.diff(ps, axis=0)) < 1e-14, axis=1)
    n_pairs = int(same.sum())
    dup = ps[:-1][same]
    r = dup - 0.5 * (a + b)
    off_line = np.abs(r @ nrm)
    along = r @ t
    cut = np.asarray(z["cut_line"])
    print(f"1. doubled vertices : {n_pairs} coincident pairs")
    print(f"   off-centreline   : max |n| = {off_line.max():.2e}  "
          f"({100 * off_line.max() / w:.3f}% of w)")
    print(f"   arc range        : [{along.min():+.4f}, {along.max():+.4f}]"
          f"  (cut specified [{-0.5 * 0.48:+.4f}, {0.5 * 0.48:+.4f}])")

    # ---- claim 3: no-opening, pointwise
    jumps = np.asarray(z["pair_jumps"])
    nvecs = np.asarray(z["pair_normals"])
    jn = np.einsum("ij,ij->i", jumps, nvecs)
    tang = np.linalg.norm(jumps - jn[:, None] * nvecs, axis=1)
    print(f"3. no-opening       : |v_n jump| max {np.abs(jn).max():.2e}, "
          f"median {np.median(np.abs(jn)):.2e}")
    print(f"   tangential slip  : max {tang.max():.4f}, "
          f"mid-fault mean {tang[np.abs(np.asarray(z['pair_coords'])[:, :2] @ t - (0.5 * (a + b) @ t)) <= 0.15].mean():.4f}")

    # ---- claim 4: quality and label
    tri = pts[faces]
    e1v = tri[:, 1] - tri[:, 0]
    e2v = tri[:, 2] - tri[:, 1]
    e3v = tri[:, 0] - tri[:, 2]

    def angles(u, w2):
        c = -np.einsum("ij,ij->i", u, w2) / (
            np.linalg.norm(u, axis=1) * np.linalg.norm(w2, axis=1))
        return np.degrees(np.arccos(np.clip(c, -1, 1)))

    all_ang = np.column_stack([angles(e3v, e1v), angles(e1v, e2v),
                               angles(e2v, e3v)])
    inz = z["inzone"].astype(bool)
    print(f"4. quality          : min angle {all_ang.min():.1f} deg "
          f"(zone cells: {all_ang[inz].min():.1f} deg)")
    print(f"   zone label       : {int(z['n_zone_before'])} cells before "
          f"the cut -> {int(inz.sum())} after (children of split cells)")
    return n_pairs


def render(z, png, alpha=0.06, zoom=0.20):
    import pyvista as pv
    import viz

    pts = np.asarray(z["points"])
    vel = np.column_stack([z["vx"], z["vy"], np.zeros(len(pts))])
    inz = z["inzone"].astype(bool)

    p = pv.Plotter(off_screen=True, shape=(1, 2),
                   window_size=(1500, 760), border=False)

    # ---- undeformed: the slit in the band
    p.subplot(0, 0)
    s = pv.PolyData(pts, faces=z["faces"])
    mask = np.zeros(s.n_cells)
    mask[inz] = 1.0
    s.cell_data["z"] = mask
    p.add_mesh(s.threshold(0.5, scalars="z"), color=viz.PALE,
               lighting=False, show_scalar_bar=False)
    p.add_mesh(pv.PolyData(pts, faces=z["faces"]), style="wireframe",
               line_width=0.6, color="#aab4bc", lighting=False)
    dup = np.asarray(z["pair_coords"])
    p.add_mesh(pv.PolyData(np.column_stack(
        [dup[:, 0], dup[:, 1], np.zeros(len(dup))])),
        color="#c0392b", point_size=7, render_points_as_spheres=True)
    p.add_text("the slit: doubled vertices (red)\n"
               "down the band's centre-line", font_size=11, color="black")
    viz.frame(p, scale=zoom)

    # ---- deformed: x + alpha v — the sides genuinely slide
    p.subplot(0, 1)
    moved = pts + alpha * vel
    s2 = pv.PolyData(moved, faces=z["faces"])
    s2.cell_data["z"] = mask
    p.add_mesh(s2.threshold(0.5, scalars="z"), color="#f6c9a0",
               lighting=False, show_scalar_bar=False)
    p.add_mesh(pv.PolyData(moved, faces=z["faces"]), style="wireframe",
               line_width=0.6, color="#8a949c", lighting=False)
    p.add_text(f"the same mesh, deformed by {alpha} x velocity:\n"
               "the sides SLIDE (tangential, free) and do not\n"
               "OPEN (normal, constrained)", font_size=11, color="black")
    viz.frame(p, scale=zoom)

    p.screenshot(png)
    print(png)


if __name__ == "__main__":
    import underworld3 as uw
    params = uw.Params(uw_resolve=0, uw_alpha=0.06, uw_zoom=0.20,
                       uw_cut_step=0.011)
    path = f"{OUT}/cut_audit_fine.npz"
    if int(params.uw_resolve) or not os.path.exists(path):
        solve_and_cache(path, float(params.uw_cut_step))
    else:
        print(f"using cached {path}")
    z = {k: v for k, v in np.load(path, allow_pickle=True).items()}
    audit(z)
    render(z, f"{OUT}/cut_audit.png", float(params.uw_alpha),
           float(params.uw_zoom))
