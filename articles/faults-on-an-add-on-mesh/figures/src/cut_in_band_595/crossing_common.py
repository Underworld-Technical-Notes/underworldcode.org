"""A conjugate pair of finite-width faults crossing at a controlled angle.

Shared geometry, mesh, rheology and measurement for the #544 experiment:
where two fused fault zones overlap, does the NEAREST-FAULT director the
toolkit uses today reproduce the additive-compliance answer?

`compliance_algebra.py` says where to look. In plane strain the deviatoric
strain-rate space is two-dimensional and a weak plane occupies ONE line in
it, at twice the physical angle. So two planes separated by Delta in the
rock are separated by 2 Delta there, and:

  * Delta = 0 and Delta = 90 are the same case -- one line, so both rules
    give the same weak DIRECTION and only the magnitude can differ;
  * Delta = 45 is the extreme -- the two compliances are orthogonal, they
    span the space, and the true overlap is ISOTROPIC while the
    nearest-fault rule stays fully anisotropic.

The three rheologies compared, all on ONE mesh per angle:

  ``nearest``    TI with the director of the nearest trace (what ships)
  ``ortho``      TI with the additive-compliance tensor, which in 2-D is
                 itself exactly a TI tensor -- effective director,
                 effective eta_0 and eta_1 (see `compliance_algebra`)
  ``isotropic``  weak in every mode; the over-compliant control, and the
                 case the arms of the cross must NOT reproduce
"""
import numpy as np
import sympy
import underworld3 as uw

from compliance_algebra import orthotropic_C, as_equivalent_TI, weak_mode

BOX = (1.0, 1.0)
CENTRE = np.array([0.5, 0.5])
HALF_LENGTH = 0.30       # tips well inside the box: no outcrop, no
                         # boundary interaction to confound the crossing
CELL = 0.030             # the host mesh
WIDTH = 0.020            # the zones' constitutive width
ZONE_SIZE = WIDTH / 4.0  # the zone's OWN mesh size. The default 0.9*width
                         # puts about two elements across the band, which
                         # cannot resolve which half of the overlap each
                         # rule owns -- and that ownership split is the
                         # whole question here.
ETA_0 = 1.0
ETA_1 = 1.0e-2           # deliberately NOT 1e-3: the campaign measured
                         # sensitivity falling as 1/(1+1/eta_f)^2, so at
                         # 1e-3 nothing about the fault's constitutive
                         # detail can register. This experiment needs the
                         # medium and the fault comparably compliant.
CASES = ("none", "isotropic", "nearest", "ortho_sum", "ortho_avg", "iso_overlap")
# `none` is the no-fault reference on the SAME mesh: uniform eta_0. It is
# what turns total dissipation into a fault metric. Slip at the crossing
# is a fine picture but a poor number here -- the two planes are symmetric
# about the loading axes, so changing Delta necessarily changes how well
# each plane is oriented for slip (at Delta = 10 both are nearly vertical,
# nearly principal planes, and barely slip at all). The dissipation
# WEAKENING, 1 - D/D_none, is referenced to its own control at each angle
# and carries no probe geometry.


# ---------------------------------------------------------------- geometry


def normals(delta_deg):
    """Unit normals of the two planes, symmetric about +x.

    Plane k runs at 90 -/+ Delta/2 from the x axis, so its normal sits at
    -/+ Delta/2 -- the convention `compliance_algebra` reports in."""
    h = np.radians(0.5 * float(delta_deg))
    return np.array([[np.cos(-h), np.sin(-h)],
                     [np.cos(+h), np.sin(+h)]])


def traces(delta_deg, half_length=HALF_LENGTH):
    """The two straight traces through the box centre. Sampled at three
    points: the ends and the crossing, which is all a straight ribbon
    needs and keeps the OCC assembly minimal."""
    out = []
    for n in normals(delta_deg):
        t = np.array([-n[1], n[0]])
        out.append(np.array([CENTRE - half_length * t,
                             CENTRE,
                             CENTRE + half_length * t]))
    return out


def distance_to_trace(pts, trace):
    """Perpendicular distance from each point to the (straight) trace,
    saturating past the tips so a point beyond the end is measured from
    the tip."""
    a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
    ab = b - a
    s = np.clip(((pts - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(pts - (a + s[:, None] * ab), axis=1)


# -------------------------------------------------------------------- mesh


CLEARANCE_LADDER = (1.0, 0.9, 1.1, 0.8, 1.2, 0.7, 1.3)


def build(delta_deg, width=WIDTH, cell=CELL, zone_size=ZONE_SIZE,
          verbose=False):
    """Host mesh with both ribbons embedded as ONE fused zone.

    `fuse` is what makes the crossing free of geometry: the two thickened
    ribbons become a single region and nothing downstream is told which
    branch a cell came from. That ignorance is exactly what #544 asks
    about.

    The carve's `clearance` is walked down a ladder because whether the
    deleted vertices leave ONE simple hole is a topological accident of
    the host mesh against a plus-shaped cavity, and it is not monotone in
    `clearance` (measured: 30 degrees builds only at 1.3, 45 degrees at
    1.0 but not 1.3). The chosen value is reported with the result.
    """
    from underworld3.utilities.place_surface import place_thin_volume

    tr = traces(delta_deg)
    for clearance in CLEARANCE_LADDER:
        m0 = uw.meshing.UnstructuredSimplexBox(
            minCoords=(0.0, 0.0), maxCoords=BOX, cellSize=cell,
            regular=False, qdegree=2)
        try:
            dm, info = place_thin_volume(
                m0.dm, tr, width=width, label="Zone", label_value=31,
                size=zone_size, clearance=clearance, assembly="fuse",
                verbose=verbose)
        except RuntimeError:
            continue
        info["clearance"] = clearance
        break
    else:
        raise RuntimeError(
            f"no clearance in {CLEARANCE_LADDER} carves a simple cavity "
            f"for a {delta_deg} degree crossing")

    mesh = uw.discretisation.Mesh(
        dm, simplex=True, qdegree=2, boundaries=m0.boundaries,
        coordinate_system_type=m0.CoordinateSystem.coordinate_type)

    cS, cE = mesh.dm.getHeightStratum(0)
    inzone = np.zeros(cE - cS, dtype=bool)
    for pt in mesh.dm.getLabel("Zone").getStratumIS(31).getIndices():
        inzone[int(pt) - cS] = True
    return mesh, tr, inzone, info


def centroids(mesh):
    """Cell centroids, in the cell order of a degree-0 variable."""
    dm = mesh.dm
    cS, cE = dm.getHeightStratum(0)
    vS, vE = dm.getDepthStratum(0)
    X = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, 2)
    out = np.empty((cE - cS, 2))
    for c in range(cS, cE):
        closure, _ = dm.getTransitiveClosure(c)
        vs = [int(p) - vS for p in closure if vS <= int(p) < vE]
        out[c - cS] = X[vs].mean(axis=0)
    return out


# --------------------------------------------------------------- rheology


def rheology_fields(mesh, tr, inzone, case, delta_deg,
                    eta_0=ETA_0, eta_1=ETA_1, width=WIDTH):
    """Per-cell (eta_0, eta_1, director) for one of the three rules.

    Returned as arrays in cell order; the caller loads them into degree-0
    variables. Everything is decided from the cell CENTROID's distance to
    each straight trace -- the zone's own membership, which the fused mesh
    does not record.
    """
    cen = centroids(mesh)
    d = np.column_stack([distance_to_trace(cen, t) for t in tr])
    nrm = normals(delta_deg)

    e0 = np.full(len(cen), eta_0)
    e1 = np.full(len(cen), eta_0)          # isotropic-strong off the zone
    dirn = np.zeros((len(cen), 2))
    dirn[:, 0] = 1.0

    # membership: inside a ribbon means within half its width of its own
    # trace. A cell the boolean left just outside both still belongs to
    # the zone label, so it falls back to its nearest trace.
    inA = d[:, 0] <= 0.5 * width
    inB = d[:, 1] <= 0.5 * width
    near = np.argmin(d, axis=1)
    lone = inzone & ~(inA | inB)
    inA = inA | (lone & (near == 0))
    inB = inB | (lone & (near == 1))
    inA &= inzone
    inB &= inzone
    both = inA & inB

    if case == "none":
        return e0, e1, dirn, both

    if case == "isotropic":
        e0[inzone] = eta_1
        e1[inzone] = eta_1
        return e0, e1, dirn, both

    # single-plane cells are the same under either rule
    e1[inzone] = eta_1
    dirn[inzone] = nrm[near[inzone]]

    if case == "iso_overlap":
        # Louis's junction ruling, applied to the fused overlap: a
        # junction must accommodate corner-turning, which no weak-plane
        # fabric can relax — the overlap is crushed rock, ISOTROPIC at
        # eta_1. Directors on the arms only; no ownership anywhere.
        e0[both] = eta_1
        e1[both] = eta_1
        return e0, e1, dirn, both

    if case in ("ortho_sum", "ortho_avg"):
        if both.any():
            weights = None if case == "ortho_sum" else (0.5, 0.5)
            C = orthotropic_C(eta_0, eta_1,
                              [-0.5 * np.radians(delta_deg),
                               +0.5 * np.radians(delta_deg)], weights)
            eff = as_equivalent_TI(C)
            e0[both] = eff["eta_0"]
            e1[both] = eff["eta_1"]
            dirn[both] = [np.cos(eff["phi"]), np.sin(eff["phi"])]
    elif case != "nearest":
        raise ValueError(f"unknown case {case!r}")

    return e0, e1, dirn, both


# ------------------------------------------------------------------ solve


def solve(mesh, e0, e1, dirn, case, tag=""):
    """Instantaneous Stokes, horizontal extension. The top is free, so
    the velocity is NOT all-Dirichlet and no pressure nullspace is
    needed."""
    v = uw.discretisation.MeshVariable(f"V{tag}", mesh, 2, degree=2)
    p = uw.discretisation.MeshVariable(f"P{tag}", mesh, 1, degree=1)
    eta0 = uw.discretisation.MeshVariable(f"e0{tag}", mesh, 1, degree=0,
                                          continuous=False)
    eta1 = uw.discretisation.MeshVariable(f"e1{tag}", mesh, 1, degree=0,
                                          continuous=False)
    eta0.array[:, 0, 0] = e0
    eta1.array[:, 0, 0] = e1

    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    if case in ("isotropic", "none"):
        stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
        stokes.constitutive_model.Parameters.shear_viscosity_0 = eta1.sym[0]
    else:
        nd = uw.discretisation.MeshVariable(f"n{tag}", mesh, 2, degree=0,
                                            continuous=False)
        nd.array[:, 0, :] = dirn
        stokes.constitutive_model = \
            uw.constitutive_models.TransverseIsotropicFlowModel
        stokes.constitutive_model.Parameters.shear_viscosity_0 = eta0.sym[0]
        stokes.constitutive_model.Parameters.shear_viscosity_1 = eta1.sym[0]
        stokes.constitutive_model.Parameters.director = nd.sym

    stokes.bodyforce = sympy.Matrix([0, 0])
    stokes.add_dirichlet_bc((-0.5, None), "Left")
    stokes.add_dirichlet_bc((+0.5, None), "Right")
    stokes.add_dirichlet_bc((None, 0.0), "Bottom")
    stokes.tolerance = 1e-8
    stokes.solve()

    reason = stokes.snes.getConvergedReason()
    if reason <= 0:
        raise RuntimeError(f"{case}: SNES did not converge ({reason})")
    return stokes, v, p


# ------------------------------------------------------------ measurement


def _outside_union(line, nhat, tr, width, margin=0.25):
    """Step each probe out along +nhat until it is clear of EVERY ribbon,
    then a further ``margin`` widths.

    A fixed standoff of a fraction of the width is wrong here. Near a
    shallow crossing the other ribbon reaches far along this one's
    normal, so a fixed probe sits INSIDE the weak union and reports
    almost no jump -- an artefact of the probe, not of the flow (it read
    0.006 against a peak of 0.18 at a 10 degree crossing). Walking out of
    the union makes the measurement the jump across the whole weak
    region, which is the quantity that means the same thing at every
    angle."""
    step = 0.1 * width
    out = line + 0.75 * width * nhat
    for _ in range(400):
        d = np.column_stack([distance_to_trace(out, t) for t in tr])
        inside = d.min(axis=1) <= 0.5 * width
        if not inside.any():
            break
        out[inside] += step * nhat
    return out + margin * width * nhat


def slip_profile(mesh, v, trace, tr=None, width=WIDTH, n=161):
    """Tangential velocity jump across a ribbon, sampled along it.

    ``tr`` is the whole network -- the probes are placed outside ALL of
    it (see `_outside_union`); pass ``[trace]`` to measure a lone ribbon.
    """
    tr = [trace] if tr is None else tr
    a, b = np.asarray(trace)[0], np.asarray(trace)[-1]
    t = (b - a) / np.linalg.norm(b - a)
    nn = np.array([-t[1], t[0]])
    s = np.linspace(0.0, 1.0, n)
    line = a + s[:, None] * (b - a)
    lo, hi = np.full(2, 1e-4), np.array(BOX) - 1e-4
    pa = np.clip(_outside_union(line.copy(), nn, tr, width), lo, hi)
    pb = np.clip(_outside_union(line.copy(), -nn, tr, width), lo, hi)
    va = np.asarray(uw.function.evaluate(v.sym, pa)).reshape(len(pa), -1)
    vb = np.asarray(uw.function.evaluate(v.sym, pb)).reshape(len(pb), -1)
    jump = (va[:, :2] - vb[:, :2]) @ t
    arc = s * np.linalg.norm(b - a)
    return arc - 0.5 * arc[-1], jump      # arc length measured FROM the
                                          # crossing, so 0 is the overlap


def dissipation(mesh, stokes):
    """Total viscous dissipation, integrated over the domain.

    One scalar, with no probe geometry in it at all -- the check that the
    slip numbers are not an artefact of where the probes were put."""
    tau, edot = stokes.stress_deviator, stokes.strainrate
    phi = sum(tau[i, j] * edot[i, j] for i in range(2) for j in range(2))
    return float(uw.maths.Integral(mesh, phi).evaluate())
