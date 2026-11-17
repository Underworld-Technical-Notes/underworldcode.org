"""The cut-ready band: transfinite, 3 nodes across, cut down the spine.

The default band's cut works but SNAPS — the placement machinery pulls
the nearest vertex onto the line, and in a band whose half-width (0.010)
is inside the snap reach of the local cell size, that nearest vertex can
be a RAIL: measured, one rail vertex dragged to n=0, pinching the band
shut at that point (Louis spotted it in the shading). Sampling the cut
finer just trips the inversion guard (3 cells) — there is no snap
parameter that guarantees rail safety, because snap_frac is measured
along edges and is blind to a vertex's distance from the line.

Prevention instead of tuning: mesh the band TRANSFINITE with THREE nodes
across the ends. That builds rails plus an exact centreline row of
vertices, edge-connected, at the rail spacing. The cut polyline is then
sampled AT those vertices — every crossing lands on an existing vertex,
nothing is snapped, nothing is inserted, and the rails cannot be touched
because nothing needs to move.

Same audit as `cut_audit.py`, same free-slit solve, cached once.
"""
import os

import numpy as np

OUT = "/Users/lmoresi/+Simulations/ribbon_network_2d"
RAIL_SPACING = 0.018
TIP_RUNGS = 4               # cut stops this many rungs inside the band


def ladder3_assembly_2d(polylines, width, size, assembly="fuse", box=None):
    """Transfinite band, THREE nodes across: rails + exact centreline."""
    import gmsh

    if len(polylines) != 1:
        raise ValueError("the ladder mesher takes exactly one polyline")
    P = np.asarray(polylines[0], dtype=float)[:, :2]
    a, b = P[0], P[-1]
    t = b - a
    L = float(np.linalg.norm(t))
    t = t / L
    n = np.array([-t[1], t[0]])
    corners = [a + 0.5 * width * n, b + 0.5 * width * n,
               b - 0.5 * width * n, a - 0.5 * width * n]
    n_along = max(2, int(round(L / size)))

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("uw_ladder3")
        occ = gmsh.model.occ
        pts = [occ.addPoint(q[0], q[1], 0.0) for q in corners]
        lines = [occ.addLine(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        surf = occ.addPlaneSurface([occ.addCurveLoop(lines)])
        occ.synchronize()
        cad_area = occ.getMass(2, surf)
        gmsh.model.mesh.setTransfiniteCurve(lines[0], n_along + 1)
        gmsh.model.mesh.setTransfiniteCurve(lines[2], n_along + 1)
        gmsh.model.mesh.setTransfiniteCurve(lines[1], 3)   # 3 across:
        gmsh.model.mesh.setTransfiniteCurve(lines[3], 3)   # rails + spine
        gmsh.model.mesh.setTransfiniteSurface(surf, "AlternateLeft")
        gmsh.model.mesh.generate(2)

        tags, xyz, _ = gmsh.model.mesh.getNodes()
        xy = np.asarray(xyz).reshape(-1, 3)[:, :2]
        renum = {int(tg): i for i, tg in enumerate(tags)}
        et, _ei, en = gmsh.model.mesh.getElements(2, surf)
        tris = []
        for ty, nodes in zip(et, en):
            if ty == 2:
                tris.append(np.array([renum[int(x)] for x in nodes],
                                     dtype=np.int64).reshape(-1, 3))
        return xy, np.vstack(tris), float(cad_area)
    finally:
        gmsh.finalize()


def solve_and_cache(path):
    import sympy
    import underworld3 as uw
    from underworld3.utilities import place_surface
    import crossing_common as CC
    import viz
    from single_fault_resolution import build_single, DELTA_ORIENT, WIDTH
    from isotropic_stress_reference import vertex_ordered

    original = place_surface._occ_assembly_2d
    place_surface._occ_assembly_2d = ladder3_assembly_2d
    try:
        mesh0, trace, inzone0, info = build_single(RAIL_SPACING)
    finally:
        place_surface._occ_assembly_2d = original
    n_zone_before = int(inzone0.sum())
    print(f"  band: {n_zone_before} zone cells, min angle "
          f"{info['min_angle']:.1f}", flush=True)

    # the cut polyline: THROUGH the transfinite spine's own vertices
    a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
    t = (b - a) / np.linalg.norm(b - a)
    L = float(np.linalg.norm(b - a))
    n_along = max(2, int(round(L / RAIL_SPACING)))
    spacing = L / n_along
    ks = np.arange(TIP_RUNGS, n_along - TIP_RUNGS + 1)
    line = a + (ks * spacing)[:, None] * t

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

    comps = {}
    for i, name in enumerate(("vx", "vy")):
        var = uw.discretisation.MeshVariable(name, mesh, 1, degree=1)
        proj = uw.systems.Projection(mesh, var)
        proj.uw_function = v.sym[i]
        proj.smoothing = 0.0
        proj.solve()
        comps[name] = vertex_ordered(mesh, var)

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


if __name__ == "__main__":
    import underworld3 as uw
    from cut_audit import audit
    params = uw.Params(uw_resolve=0)
    path = f"{OUT}/cut_ladder.npz"
    if int(params.uw_resolve) or not os.path.exists(path):
        solve_and_cache(path)
    else:
        print(f"using cached {path}")
    z = {k: v for k, v in np.load(path, allow_pickle=True).items()}
    audit(z)

    # the rail check that caught the default band's snap
    from collections import defaultdict
    pts = np.asarray(z["points"])[:, :2]
    faces = np.asarray(z["faces"]).reshape(-1, 4)[:, 1:]
    inz = z["inzone"].astype(bool)
    w = float(z["width"])
    tr = np.asarray(z["trace_a"])
    a, b = tr[0], tr[-1]
    t = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-t[1], t[0]])
    edge_cells = defaultdict(list)
    for c, f in enumerate(faces):
        for i in range(3):
            e = (min(f[i], f[(i + 1) % 3]), max(f[i], f[(i + 1) % 3]))
            edge_cells[e].append(c)
    rail_verts = set()
    for e, cs in edge_cells.items():
        if len(cs) == 2 and inz[cs[0]] != inz[cs[1]]:
            rail_verts.update(e)
    rv = np.array(sorted(rail_verts))
    off = np.abs((pts[rv] - 0.5 * (a + b)) @ nrm)
    print(f"5. rails            : {len(rv)} vertices, min |n| = "
          f"{off.min():.4f}  (must be ~{0.5 * w:.3f}; snapped = 0)")
