"""One fault in isolation: how does slip change with elements ACROSS?

Louis, 2026-08-16: the ribbon is not cut by anything, so nothing forbids
running it at the default resolution (~2 elements across the band) or
even ~1. What does that do to the slip?

One straight fault — fault A of the Delta = 45 crossing geometry, 22.5
degrees off vertical, same box, same extension drive, same isotropic
weak material (eta_1 = 1e-3) — no junction anywhere. The zone's own mesh
size is swept:

    size = w/4    ~4 elements across   (what the crossing study used)
    size = 0.9 w  ~2 elements across   (the place_thin_volume DEFAULT)
    size = 1.8 w  ~1 element across

Everything is measured through the RECOVERED STRESS (tau -> continuous
P1, zero smoothing; invariants in numpy; divided by the P0 cell
viscosity), because the velocity gradient jumps at the band edge and has
already produced two artefacts this week.

Solve once per size, cache to `single_<tag>.npz`; renders are instant.
"""
import os

import numpy as np

OUT = "/Users/lmoresi/+Simulations/ribbon_network_2d"
DELTA_ORIENT = 45.0        # fault A of this crossing geometry
WIDTH = 0.02
SIZES = ((0.0050, "w4", "~4 elements across  (size = w/4)"),
         (0.0180, "w2", "~2 elements across  (the default, 0.9w)"),
         (0.0360, "w1", "~1 element across  (size = 1.8w)"))


# ---------------------------------------------------------------- solve


def build_single(zone_size, width=WIDTH, cell=None):
    """One ribbon, no crossing — CC.build minus the second trace."""
    import underworld3 as uw
    import crossing_common as CC
    from underworld3.utilities.place_surface import place_thin_volume

    cell = CC.CELL if cell is None else cell
    trace = CC.traces(DELTA_ORIENT)[0]
    for clearance in CC.CLEARANCE_LADDER:
        m0 = uw.meshing.UnstructuredSimplexBox(
            minCoords=(0.0, 0.0), maxCoords=CC.BOX, cellSize=cell,
            regular=False, qdegree=2)
        try:
            dm, info = place_thin_volume(
                m0.dm, [trace], width=width, label="Zone", label_value=31,
                size=zone_size, clearance=clearance, assembly="fuse")
        except RuntimeError:
            continue
        info["clearance"] = clearance
        break
    else:
        raise RuntimeError(f"no clearance builds at size {zone_size}")

    mesh = uw.discretisation.Mesh(
        dm, simplex=True, qdegree=2, boundaries=m0.boundaries,
        coordinate_system_type=m0.CoordinateSystem.coordinate_type)
    cS, cE = mesh.dm.getHeightStratum(0)
    inzone = np.zeros(cE - cS, dtype=bool)
    for pt in mesh.dm.getLabel("Zone").getStratumIS(31).getIndices():
        inzone[int(pt) - cS] = True
    return mesh, trace, inzone, info


def solve_and_cache(zone_size, tag, eta_1, path):
    import sympy
    import underworld3 as uw
    import crossing_common as CC
    import viz
    from isotropic_stress_reference import vertex_ordered

    mesh, trace, inzone, info = build_single(zone_size)
    e1 = np.where(inzone, eta_1, 1.0)

    v = uw.discretisation.MeshVariable("V", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    ev = uw.discretisation.MeshVariable("ev", mesh, 1, degree=0,
                                        continuous=False)
    ev.array[:, 0, 0] = e1
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = ev.sym[0]
    stokes.bodyforce = sympy.Matrix([0, 0])
    stokes.add_dirichlet_bc((-0.5, None), "Left")
    stokes.add_dirichlet_bc((+0.5, None), "Right")
    stokes.add_dirichlet_bc((None, 0.0), "Bottom")
    stokes.tolerance = 1e-8
    stokes.solve()
    if stokes.snes.getConvergedReason() <= 0:
        raise RuntimeError("did not converge")
    print(f"  [{tag}] solve done: {info['n_zone_cells']} zone cells, "
          f"min angle {info['min_angle']:.1f}, "
          f"clearance {info['clearance']}", flush=True)

    tau = stokes.stress_deviator
    comps = {}
    for name, expr in (("xx", tau[0, 0]), ("yy", tau[1, 1]),
                       ("xy", tau[0, 1])):
        var = uw.discretisation.MeshVariable(f"t{name}", mesh, 1, degree=1)
        proj = uw.systems.Projection(mesh, var)
        proj.uw_function = expr
        proj.smoothing = 0.0
        proj.solve()
        comps[name] = vertex_ordered(mesh, var)

    surf = viz.pv_cells(mesh)
    np.savez(path,
             points=np.asarray(surf.points), faces=np.asarray(surf.faces),
             tau_xx=comps["xx"], tau_yy=comps["yy"], tau_xy=comps["xy"],
             eta_cell=e1, inzone=inzone,
             trace_a=np.asarray(trace),
             zone_size=float(zone_size),
             n_zone_cells=float(info["n_zone_cells"]),
             delta=float(DELTA_ORIENT), eta_1=float(eta_1),
             width=float(WIDTH))
    print(f"  [{tag}] cached -> {path}", flush=True)


# ------------------------------------------------------------- measure


def gamma_A(z):
    """Shear rate on the fault's own plane, cell-centred, from the P1
    stress and the P0 viscosity."""
    f = np.asarray(z["faces"]).reshape(-1, 4)[:, 1:]
    txx = z["tau_xx"][f].mean(axis=1)
    tyy = z["tau_yy"][f].mean(axis=1)
    txy = z["tau_xy"][f].mean(axis=1)
    phi = -np.radians(0.5 * float(z["delta"]))
    n = np.array([np.cos(phi), np.sin(phi)])
    t = np.array([-np.sin(phi), np.cos(phi)])
    tau_nt = (n[0] * t[0] * txx + n[1] * t[1] * tyy
              + (n[0] * t[1] + n[1] * t[0]) * txy)
    return np.abs(tau_nt) / z["eta_cell"]


def cells_across(z):
    """Median in-band cells per along-strip of one zone-size length."""
    from isotropic_stress_reference import band_slip  # reuse geometry
    pts = np.asarray(z["points"])[:, :2]
    f = np.asarray(z["faces"]).reshape(-1, 4)[:, 1:]
    cen = pts[f].mean(axis=1)
    a, b = np.asarray(z["trace_a"])[0], np.asarray(z["trace_a"])[-1]
    t = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-t[1], t[0]])
    r = cen - 0.5 * (a + b)
    s, n = r @ t, r @ nrm
    inband = (np.abs(n) <= 0.5 * float(z["width"])) & z["inzone"]
    half = 0.5 * np.linalg.norm(b - a)
    size = float(z["zone_size"])
    edges = np.arange(-half + 2 * float(z["width"]),
                      half - 2 * float(z["width"]), size)
    counts = np.histogram(s[inband], bins=edges)[0]
    # a strip of length `size` holds `size/size = 1` column of cells,
    # two triangles per quad: cells-per-strip / 2 ~ elements across
    return float(np.median(counts)) / 2.0


if __name__ == "__main__":
    import underworld3 as uw
    from isotropic_stress_reference import band_slip
    params = uw.Params(uw_eta_1=1.0e-3, uw_resolve=0)

    for size, tag, _label in SIZES:
        path = f"{OUT}/single_{tag}.npz"
        if int(params.uw_resolve) or not os.path.exists(path):
            solve_and_cache(size, tag, float(params.uw_eta_1), path)
        else:
            print(f"using cached {path}")

    # ---- profiles, one axes, stress-derived throughout
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import os
    entries = list(SIZES)
    if os.path.exists(f"{OUT}/single_ladder.npz"):
        entries.append((0.018, "ladder",
                        "TRUE 1 element across (transfinite ladder)"))
    colours = ("#2c3e50", "#e08a1e", "#c0392b", "#3f8f5e")
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    print()
    for (size, tag, label), colour in zip(entries, colours):
        z = {k: v for k, v in
             np.load(f"{OUT}/single_{tag}.npz", allow_pickle=True).items()}
        w = float(z["width"])
        # Bin width matched to THIS case's zone cells: a strip must hold
        # several cells or the integral is binning noise, not slip — the
        # first render put ~3 cells per bin for the coarse zones and the
        # curves oscillated by +-60%.
        # ONE binning for every case (bin 0.06 = ~2 cells of the
        # coarsest zone) and one tip cut, so the curves are the same
        # length and comparable point by point.
        l, val = band_slip(z, gamma_A(z), z["trace_a"], nbins=10)
        keep = np.abs(l) <= 0.24
        ax.plot(l[keep], val[keep], "o-", ms=4, lw=2.0, color=colour,
                label=f"{label}   [{int(z['n_zone_cells'])} zone cells]")
        mid = np.abs(l) <= 0.15
        print(f"{label:44s} cells across ~{cells_across(z):.1f}   "
              f"mean mid-fault slip {val[mid].mean():.4f}")
    ax.set_xlabel("arc length along the fault, from its centre")
    ax.set_ylabel("band slip   $\\int (\\tau_{nt}/\\eta)\\,dn$")
    ax.set_title("One isolated fault, isotropic weak band "
                 "($\\eta_1 = 10^{-3}$, $w = 0.02$):\n"
                 "the zone's own resolution, swept — everything from "
                 "recovered stress", fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT}/single_fault_resolution.png", dpi=140)
    print(f"\n{OUT}/single_fault_resolution.png")
