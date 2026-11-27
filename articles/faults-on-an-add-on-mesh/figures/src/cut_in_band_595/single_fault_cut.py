"""The default band CUT along its centre-line — Louis's "best one".

The workflow is the listric2 hybrid's, unchanged: place the ribbon
(default resolution, 0.9w), then `mesh.add_fault(trace)` cuts the placed
mesh along the trace — the cut machinery embeds the line conformingly
itself, so the union-jack's missing mid-to-mid edges are irrelevant.
Band stays weak (isotropic 1e-3, matching this week's reference cases),
the slit carries the matched interface law eta_I = eta_1 / w, and slip
is read EXACTLY from the contact pairing — no recovery, no averaging,
no probes.

Tips: the cut stops 2 cells short of the band's ends, so both tips
terminate INSIDE weak material — free crack tips, no pinning (the
campaign's 99% configuration).

Cache: `single_cut.npz` (slip profile + leak); solve once.
"""
import os

import numpy as np

OUT = "/Users/lmoresi/+Simulations/ribbon_network_2d"
ZONE_SIZE = 0.018            # the default, 0.9w
TIP_PULLBACK = 0.06          # 2 host cells inside the band ends


def solve_and_cache(eta_1, path, law="matched"):
    import sympy
    import underworld3 as uw
    import crossing_common as CC
    from single_fault_resolution import build_single, DELTA_ORIENT, WIDTH

    mesh, trace, inzone, info = build_single(ZONE_SIZE)

    # the cut line: the trace, pulled back so the tips stay in the band,
    # resampled at the host cell size (each point becomes a cut vertex)
    a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
    t = (b - a) / np.linalg.norm(b - a)
    a2, b2 = a + TIP_PULLBACK * t, b - TIP_PULLBACK * t
    npts = max(2, int(round(np.linalg.norm(b2 - a2) / CC.CELL)) + 1)
    line = a2 + np.linspace(0, 1, npts)[:, None] * (b2 - a2)

    mesh = mesh.add_fault(("Fault", line))
    cS, cE = mesh.dm.getHeightStratum(0)
    weak = np.zeros(cE - cS, dtype=bool)
    # after the cut the Zone label carries closure points too (the
    # split's plex surgery completes it); cells only — the listric2
    # hybrid guards identically
    for pt in mesh.dm.getLabel("Zone").getStratumIS(31).getIndices():
        if cS <= int(pt) < cE:
            weak[int(pt) - cS] = True
    print(f"  cut mesh: {cE - cS} cells, {int(weak.sum())} in the zone",
          flush=True)

    v = uw.discretisation.MeshVariable("V", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=0,
                                       continuous=False)
    e1 = uw.discretisation.MeshVariable("e1", mesh, 1, degree=0,
                                        continuous=False)
    e1.array[:, 0, 0] = np.where(weak, eta_1, 1.0)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = e1.sym[0]
    stokes.bodyforce = sympy.Matrix([0, 0])
    stokes.add_dirichlet_bc((-0.5, None), "Left")
    stokes.add_dirichlet_bc((+0.5, None), "Right")
    stokes.add_dirichlet_bc((None, 0.0), "Bottom")
    n = CC.normals(DELTA_ORIENT)[0]
    eta_f = eta_1 / WIDTH if law == "matched" else 1.0e-8
    stokes.add_fault_bc(eta_f, boundary="Fault",
                        normal=sympy.Matrix([[float(n[0]), float(n[1])]]))
    stokes._rotated_use_lu = True
    stokes.tolerance = 1e-8
    stokes.solve()

    from underworld3.utilities import fault_contact
    coords, jumps, nrm = fault_contact.fault_pair_jumps(
        stokes, "Fault", stokes._rotated_freeslip_info)
    jn = np.einsum("ij,ij->i", jumps, nrm)
    tang = jumps - jn[:, None] * nrm
    tvec = np.column_stack([-nrm[:, 1], nrm[:, 0]])
    signed = np.einsum("ij,ij->i", tang, tvec)
    leak = float(np.abs(jn).max()) if len(jn) else 0.0

    r = coords[:, :2] - 0.5 * (a + b)
    l = r @ t
    order = np.argsort(l)
    np.savez(path, l=l[order], slip=signed[order], leak=leak,
             n_zone=float(weak.sum()), eta_1=float(eta_1),
             width=float(WIDTH))
    print(f"  leak {leak:.2e}; cached -> {path}", flush=True)


if __name__ == "__main__":
    import underworld3 as uw
    params = uw.Params(uw_eta_1=1.0e-3, uw_resolve=0, uw_law="matched")
    law = str(params.uw_law)
    path = f"{OUT}/single_cut_{law}.npz"
    if int(params.uw_resolve) or not os.path.exists(path):
        solve_and_cache(float(params.uw_eta_1), path, law)
    else:
        print(f"using cached {path}")

    z = np.load(path)
    l, s = z["l"], np.abs(z["slip"])
    mid = np.abs(l) <= 0.15
    print(f"cut-in-band: pairing slip mid-fault {s[mid].mean():.4f} "
          f"(peak {s.max():.4f}), no-opening leak {float(z['leak']):.2e}")
    print("compare: band-only w2 0.394-0.413; w4 0.428-0.433; "
          "pure contact 0.449")
