"""The isotropic reference cases, measured through the STRESS.

Louis, 2026-08-16: before the isotropic zone can serve as the reference
for the overlap question, its own slip and strain rate have to be
believable — and measured properly. Differentiating the velocity gives a
field that JUMPS at the band edge and recovers badly; the sound route
across a material jump is:

  1. recover the deviatoric stress tau = 2 eta edot by L2 projection of
     COMPONENTS onto continuous P1 (traction is continuous across the
     edge, so tau is the field that projects cleanly);
  2. form invariants in NUMPY from the nodal components;
  3. divide by the CELL viscosity (P0, never interpolated) to get the
     strain rate: edot_II = tau_II / (2 eta), and the shear rate on
     fault A's plane gamma_A = tau_nt / eta.

Everything the renderer needs is cached to `iso_stress_<delta>.npz` on
the first run; renders and measurements after that are instant.

Field maps are PyVista on the mesh's own cells. The slip is carried ON
the traces in physical space (band-integrated gamma, per fault).
"""
import os

import numpy as np

OUT = "/Users/lmoresi/+Simulations/ribbon_network_2d"


# ---------------------------------------------------------------- solve


def vertex_ordered(mesh, var):
    """P1 nodal values reindexed to the dm's vertex order (the order
    `viz.pv_cells` builds its points in)."""
    dm = mesh.dm
    sec = dm.getLocalSection()
    vS, vE = dm.getDepthStratum(0)
    offs = np.array([sec.getFieldOffset(v, var.field_id)
                     for v in range(vS, vE)])
    row = np.empty(len(offs), dtype=np.int64)
    row[np.argsort(offs)] = np.arange(len(offs))
    X = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, 2)
    assert np.allclose(np.asarray(var.coords)[row], X), \
        "variable DOF order does not match the offset ranking"
    return np.asarray(var.data[:, 0])[row].copy()


def solve_and_cache(delta, eta_1, path):
    import underworld3 as uw
    import crossing_common as CC
    import viz

    mesh, tr, inzone, info = CC.build(delta)
    e0, e1, dirn, both = CC.rheology_fields(mesh, tr, inzone, "isotropic",
                                            delta, eta_1=eta_1)
    stokes, _v, _p = CC.solve(mesh, e0, e1, dirn, "isotropic", tag="ref")
    print("  solve done", flush=True)

    # 1. component-wise recovery of tau onto continuous P1
    tau = stokes.stress_deviator
    comps = {}
    for name, expr in (("xx", tau[0, 0]), ("yy", tau[1, 1]),
                       ("xy", tau[0, 1])):
        var = uw.discretisation.MeshVariable(f"tau_{name}", mesh, 1,
                                             degree=1)
        proj = uw.systems.Projection(mesh, var)
        proj.uw_function = expr
        proj.smoothing = 0.0
        proj.solve()
        comps[name] = vertex_ordered(mesh, var)
        print(f"  tau_{name} projected", flush=True)

    surf = viz.pv_cells(mesh)
    cen = CC.centroids(mesh)
    d = np.column_stack([CC.distance_to_trace(cen, t) for t in tr])
    np.savez(path,
             points=np.asarray(surf.points), faces=np.asarray(surf.faces),
             tau_xx=comps["xx"], tau_yy=comps["yy"], tau_xy=comps["xy"],
             eta_cell=e1,               # isotropic: e1 IS the viscosity
             inzone=inzone, dist=d,
             trace_a=np.asarray(tr[0]), trace_b=np.asarray(tr[1]),
             delta=float(delta), eta_1=float(eta_1), width=float(CC.WIDTH))
    print(f"cached -> {path}", flush=True)


# ---------------------------------------------- numpy invariants (step 2/3)


def cell_fields(z):
    """Cell-centred tau, strain-rate invariant and per-fault shear rate,
    from the P1 nodal stress and the P0 viscosity."""
    f = np.asarray(z["faces"]).reshape(-1, 4)[:, 1:]
    txx = z["tau_xx"][f].mean(axis=1)
    tyy = z["tau_yy"][f].mean(axis=1)
    txy = z["tau_xy"][f].mean(axis=1)
    eta = z["eta_cell"]

    tau_II = np.sqrt(0.5 * (txx ** 2 + tyy ** 2) + txy ** 2)
    edot_II = tau_II / (2.0 * eta)

    delta = float(z["delta"])
    gammas = {}
    h = np.radians(0.5 * delta)
    for key, phi in (("a", -h), ("b", +h)):
        n = np.array([np.cos(phi), np.sin(phi)])
        t = np.array([-np.sin(phi), np.cos(phi)])
        # tau_nt = n . tau . t, with tau symmetric
        tau_nt = (n[0] * t[0] * txx + n[1] * t[1] * tyy
                  + (n[0] * t[1] + n[1] * t[0]) * txy)
        gammas[key] = np.abs(tau_nt) / eta        # 2 edot_nt
    return edot_II, gammas


def band_slip(z, gamma, trace, nbins=25):
    """Int gamma dn across the ribbon of ``trace``, binned along it."""
    pts = np.asarray(z["points"])[:, :2]
    f = np.asarray(z["faces"]).reshape(-1, 4)[:, 1:]
    tri = pts[f]
    cen = tri.mean(axis=1)
    a2 = tri[:, 1] - tri[:, 0]
    b2 = tri[:, 2] - tri[:, 0]
    area = 0.5 * np.abs(a2[:, 0] * b2[:, 1] - a2[:, 1] * b2[:, 0])

    a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
    t = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-t[1], t[0]])
    r = cen - 0.5 * (a + b)
    s, n = r @ t, r @ nrm

    w = float(z["width"])
    half = 0.5 * np.linalg.norm(b - a)
    inband = np.abs(n) <= 0.5 * w
    edges = np.linspace(-half, half, nbins + 1)
    num = np.histogram(s[inband], bins=edges,
                       weights=(gamma * area)[inband])[0]
    return 0.5 * (edges[1:] + edges[:-1]), num / (edges[1] - edges[0])


# --------------------------------------------------------------- render


def render(z, png, zoom):
    import pyvista as pv
    import viz

    edot_II, gammas = cell_fields(z)
    delta = float(z["delta"])

    def surface():
        return pv.PolyData(z["points"], faces=z["faces"])

    inzone = z["inzone"].astype(bool)
    lo = np.percentile(edot_II, 5.0)
    hi = np.percentile(edot_II[inzone], 99.0)

    p = pv.Plotter(off_screen=True, shape=(1, 2),
                   window_size=(1500, 720), border=False)

    # ---- panel 1: the strain-rate invariant, log scale (spans ~eta ratio)
    p.subplot(0, 0)
    s = surface()
    s.cell_data["edot"] = edot_II
    p.add_mesh(s, scalars="edot", cmap="Oranges", log_scale=True,
               clim=(max(lo, 1e-3 * hi), hi), lighting=False,
               show_edges=True, line_width=0.4, edge_color="#d5dade",
               show_scalar_bar=True,
               scalar_bar_args=dict(
                   title="strain rate  (tau_II / 2 eta)   ",
                   vertical=False, position_x=0.10, position_y=0.02,
                   width=0.80, height=0.04, title_font_size=13,
                   label_font_size=12, color="black"))
    p.add_text(f"isotropic zone,  Delta = {delta:.0f} deg\n"
               "strain rate from RECOVERED STRESS\n"
               "(tau -> P1, invariant in numpy, / 2 eta)",
               font_size=10, color="black")
    viz.frame(p, scale=zoom)

    # ---- panel 2: slip carried ON the traces, physical space
    p.subplot(0, 1)
    zone = pv.PolyData(z["points"], faces=z["faces"])
    mask = np.zeros(len(edot_II))
    mask[inzone] = 1.0
    zone.cell_data["z"] = mask
    p.add_mesh(zone.threshold(0.5, scalars="z"), color=viz.PALE,
               lighting=False, show_scalar_bar=False)
    p.add_mesh(surface(), style="wireframe", line_width=0.4,
               color="#d5dade", lighting=False, show_scalar_bar=False)
    # The last ~2w at each end is the TIP: the crack-tip stress
    # concentration divided by the band's 1e-3 viscosity, with the P1
    # recovery oscillating near the singularity. Real physics, wrong
    # scale-setter — band slip there reads ~10x the arm value, which
    # would flatten the whole trace to one colour. Excluded from the
    # line and from the clim; the tip region is about the tips, not
    # about the junction this figure interrogates.
    w = float(z["width"])
    slips = {}
    for key, trace in (("a", z["trace_a"]), ("b", z["trace_b"])):
        l, val = band_slip(z, gammas[key], trace)
        a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
        half = 0.5 * np.linalg.norm(b - a)
        keep = np.abs(l) <= half - 2.0 * w
        slips[key] = (l[keep], val[keep])
    peak = max(v.max() for _l, v in slips.values())
    clim = (0.0, float(peak))
    for i, (key, trace) in enumerate((("a", z["trace_a"]),
                                      ("b", z["trace_b"]))):
        l, val = slips[key]
        a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
        t = (b - a) / np.linalg.norm(b - a)
        pts = 0.5 * (a + b) + l[:, None] * t
        p.add_mesh(viz.slip_line(pts, val), scalars="slip", cmap="plasma",
                   clim=clim, line_width=10, lighting=False,
                   show_scalar_bar=(i == 0),
                   scalar_bar_args=dict(
                       title="band slip  Int gamma dn   ",
                       vertical=False, position_x=0.10, position_y=0.02,
                       width=0.80, height=0.04, title_font_size=13,
                       label_font_size=12, color="black"))
    p.add_text("slip on each fault's own band\n"
               "(gamma = tau_nt / eta, integrated across w;\n"
               "tip regions excluded — see script)",
               font_size=10, color="black")
    viz.frame(p, scale=0.55)

    p.screenshot(png)
    print(png)


if __name__ == "__main__":
    import underworld3 as uw
    params = uw.Params(uw_delta=45.0, uw_eta_1=1.0e-3, uw_zoom=0.16,
                       uw_resolve=0)
    delta = float(params.uw_delta)
    cache = f"{OUT}/iso_stress_{int(round(delta))}.npz"
    if int(params.uw_resolve) or not os.path.exists(cache):
        solve_and_cache(delta, float(params.uw_eta_1), cache)
    else:
        print(f"using cached {cache}")

    z = {k: v for k, v in np.load(cache, allow_pickle=True).items()}
    render(z, f"{OUT}/iso_stress_{int(round(delta))}.png",
           float(params.uw_zoom))

    # the numbers, from the same stress-derived field
    _e, gammas = cell_fields(z)
    for key, trace in (("a", z["trace_a"]), ("b", z["trace_b"])):
        l, val = band_slip(z, gammas[key], trace)
        at0 = np.interp(0.0, l, val)
        arm = 0.5 * (np.interp(0.2, l, val) + np.interp(-0.2, l, val))
        print(f"fault {key.upper()}: centre {at0:.4f}  arm {arm:.4f}  "
              f"centre/arm {at0/arm:.2f}")
