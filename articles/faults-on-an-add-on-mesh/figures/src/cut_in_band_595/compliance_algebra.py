"""What IS the rheology where two weak planes overlap? (#544, the algebra)

Before any solve: the additive-compliance construction the issue names is
computable in closed form in 2-D, and the closed form makes a prediction
about WHICH crossing angle discriminates.

Plane strain, incompressible: the deviatoric strain-rate space is
2-DIMENSIONAL, spanned by

    e_1 = pure shear on the axes   (eps_xx = -eps_yy)
    e_2 = simple shear             (eps_xy)

and a rotation of the material by theta rotates a state by 2 theta in that
plane. The on-plane shear mode of a weak plane whose normal is at angle phi
is therefore a single UNIT VECTOR in that 2-D space, at angle 2 phi + 90.

Two weak planes separated by Delta in physical space are separated by
2 Delta in the deviatoric plane. So:

  * Delta = 0    -- the same mode; the planes are the same plane.
  * Delta = 90   -- 2 Delta = 180: the SAME LINE again. Shear on a plane
                   with normal x-hat IS shear on a plane with normal y-hat.
                   Two orthogonal weak planes in 2-D are DEGENERATE and the
                   overlap question is empty there.
  * Delta = 45   -- 2 Delta = 90: the two weak modes are ORTHOGONAL, the two
                   compliances span the whole deviatoric space, and the sum
                   is ISOTROPIC. This is the discriminating angle.

That last line is the prediction this file checks against the shipped
Muehlhaus-Moresi tensor, and it is the reason the crossing sweep in
`crossing_sweep.py` is run against Delta rather than against a single
"high angle": the 90-degree X that the words "high angle" suggest is
exactly where nothing can be learned.
"""
import numpy as np
import sympy
import underworld3 as uw


# ----------------------------------------------------------------------
# the shipped tensor, made numeric


def mandel_C(eta_0, eta_1, phi, dim=2):
    """The TI Mandel matrix from the shipped model, for a director at
    angle ``phi`` (the plane's NORMAL, measured from +x)."""
    mesh = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), cellSize=0.5,
        regular=False, qdegree=2)
    v = uw.discretisation.MeshVariable("Vc", mesh, dim, degree=2)
    p = uw.discretisation.MeshVariable("Pc", mesh, 1, degree=1)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = \
        uw.constitutive_models.TransverseIsotropicFlowModel
    stokes.constitutive_model.Parameters.shear_viscosity_0 = eta_0
    stokes.constitutive_model.Parameters.shear_viscosity_1 = eta_1
    stokes.constitutive_model.Parameters.director = sympy.Matrix(
        [[sympy.cos(phi)], [sympy.sin(phi)]])
    C = sympy.Matrix(stokes.constitutive_model.C)
    # the Parameter descriptors keep eta_0 / eta_1 as named UWexpressions;
    # substitute their values so the matrix is numeric.
    from underworld3.function.expressions import UWexpression
    for _ in range(8):
        atoms = C.atoms(UWexpression)
        if not atoms:
            break
        C = C.subs({a: a.sym for a in atoms})
    return np.array(C.evalf(), dtype=float)


# ----------------------------------------------------------------------
# the deviatoric plane, by hand


def mod90(deg):
    """A 2-D director angle, folded into (-45, 45]."""
    d = (float(deg) + 45.0) % 90.0 - 45.0
    return d


def dev_basis():
    """Orthonormal basis of the 2-D deviatoric strain-rate space, as
    2x2 tensors with <A, B> = A_ij B_ij."""
    e1 = np.array([[1.0, 0.0], [0.0, -1.0]]) / np.sqrt(2.0)
    e2 = np.array([[0.0, 1.0], [1.0, 0.0]]) / np.sqrt(2.0)
    return e1, e2


def weak_mode(phi):
    """Unit vector in the deviatoric plane for on-plane shear of a weak
    plane whose normal is at angle ``phi``."""
    n = np.array([np.cos(phi), np.sin(phi)])
    t = np.array([-np.sin(phi), np.cos(phi)])
    m = 0.5 * (np.outer(n, t) + np.outer(t, n))
    e1, e2 = dev_basis()
    u = np.array([np.tensordot(m, e1), np.tensordot(m, e2)])
    return u / np.linalg.norm(u)


def C_in_dev_plane(C_mandel):
    """Restrict the Mandel matrix to the deviatoric plane, in the
    (e_1, e_2) basis. Mandel order in 2-D is (xx, yy, xy) with the shear
    row/column carrying the sqrt(2)."""
    e1, e2 = dev_basis()

    def to_mandel(a):
        return np.array([a[0, 0], a[1, 1], np.sqrt(2.0) * a[0, 1]])

    def from_mandel(m):
        return np.array([[m[0], m[2] / np.sqrt(2.0)],
                         [m[2] / np.sqrt(2.0), m[1]]])

    out = np.zeros((2, 2))
    for i, a in enumerate((e1, e2)):
        r = from_mandel(C_mandel @ to_mandel(a))
        out[0, i] = np.tensordot(r, e1)
        out[1, i] = np.tensordot(r, e2)
    return out


# ----------------------------------------------------------------------
# the construction: sum the compliances, invert


def orthotropic_C(eta_0, eta_1, phis, weights=None):
    """The orthotropic tensor for weak planes at normals ``phis``,
    restricted to the deviatoric plane.

    ``weights`` decides WHAT the overlap is made of, and there are two
    defensible readings:

    ``None`` (weights all 1) -- the literal additive rule #544 names.
        The two fabrics are both fully present and their compliances add.
        Note what this does as the planes converge: two COINCIDENT weak
        planes come out twice as weak as one, which is right if they are
        two independent fabrics and wrong if they are one fault sampled
        twice. The effect is not confined to the coincident limit -- at
        a 10 degree crossing it still weakens the off-plane mode by
        seven-fold -- so it is not a corner case to be waved away.

    ``[0.5, 0.5]`` -- the Reuss (compliance) average, i.e. the overlap is
        a 50/50 MIXTURE of the two fabrics. This degenerates exactly to
        the single plane when the planes coincide, and is isotropic at 45
        degrees like the sum, but only half as weak.

    They are the two ends of the same one-parameter family and the data
    should be read against both.
    """
    phis = list(phis)
    weights = [1.0] * len(phis) if weights is None else list(weights)
    S = np.eye(2) / (2.0 * eta_0)
    s = 1.0 / (2.0 * eta_1) - 1.0 / (2.0 * eta_0)
    for phi, w in zip(phis, weights):
        u = weak_mode(phi)
        S = S + w * s * np.outer(u, u)
    return np.linalg.inv(S)


def as_equivalent_TI(C_dev):
    """Read an arbitrary 2-D deviatoric C back as a TI tensor: its two
    eigenvalues are 2*eta_1_eff (weak) and 2*eta_0_eff (strong), and the
    weak eigenvector at deviatoric angle alpha corresponds to a director
    at phi = (alpha - 90)/2.

    This is what makes the orthotropic treatment FREE in 2-D: the shipped
    TransverseIsotropicFlowModel can express it exactly, with an effective
    director and effective eta_0/eta_1."""
    w, V = np.linalg.eigh(C_dev)
    weak, strong = V[:, 0], V[:, 1]
    alpha = np.arctan2(weak[1], weak[0])
    return dict(eta_1=w[0] / 2.0, eta_0=w[1] / 2.0,
                phi=0.5 * (alpha - 0.5 * np.pi),
                strong_dir=strong)


if __name__ == "__main__":
    eta_0, eta_1 = 1.0, 1.0e-2

    print("1. the shipped tensor IS the two-eigenvalue form claimed in #539")
    print("   (in 2-D a director is only defined MOD 90 deg: n-hat and its")
    print("    perpendicular name the same on-plane shear mode)")
    for phi_deg in (0.0, 17.0, 45.0, 73.0):
        phi = np.radians(phi_deg)
        Cd = C_in_dev_plane(mandel_C(eta_0, eta_1, phi))
        got = as_equivalent_TI(Cd)
        du = mod90(np.degrees(got["phi"]) - phi_deg)
        print(f"   director {phi_deg:5.1f} deg -> eigenvalues "
              f"{2*got['eta_1']:.6e} (weak), {2*got['eta_0']:.6e} (strong); "
              f"recovered director off by {du:.2e} deg")

    print()
    print("2. the overlap tensor: the discriminating angle is 45, not 90")
    print("   two planes with normals at -Delta/2 and +Delta/2; the "
          "single-plane")
    print(f"   anisotropy is eta_0/eta_1 = {eta_0/eta_1:.0f}")
    print()
    print(f"   {'':5}   {'compliance SUM':^34}   "
          f"{'compliance AVERAGE (Reuss)':^34}")
    print(f"   {'Delta':>5}   {'e1/e1':>9} {'e0/e0':>9} {'n_eff':>6} "
          f"{'aniso':>6}   {'e1/e1':>9} {'e0/e0':>9} {'n_eff':>6} "
          f"{'aniso':>6}")
    for d_deg in (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0):
        d = np.radians(d_deg)
        phis = (-0.5 * d, +0.5 * d)          # symmetric about phi = 0
        line = f"   {d_deg:5.1f}  "
        for weights in (None, (0.5, 0.5)):
            got = as_equivalent_TI(orthotropic_C(eta_0, eta_1, phis,
                                                 weights))
            line += (f" {got['eta_1']/eta_1:9.4f} "
                     f"{got['eta_0']/eta_0:9.4f} "
                     f"{mod90(np.degrees(got['phi'])):+6.1f} "
                     f"{got['eta_0']/got['eta_1']:6.1f}  ")
        print(line)
    print()
    print("   Read the SUM column at Delta = 0: two coincident planes come")
    print("   out twice as weak as one, and the excess does not switch off")
    print("   away from coincidence -- at 15 degrees the off-plane mode is")
    print("   already 14x more compliant than the wall rock. The AVERAGE")
    print("   column degenerates to the single plane exactly. The two are")
    print("   the ends of one family, and the numerical experiment runs")
    print("   both rather than picking.")

    print()
    print("   Delta = 0 and Delta = 90 are the SAME case -- both")
    print("   compliances land on the SAME line. Under the average rule")
    print("   the overlap is then EXACTLY the single plane, so nearest and")
    print("   orthotropic coincide identically and the 90-degree X, the")
    print("   geometry 'high angle' suggests, can measure nothing at all.")
    print()
    print("   Delta = 45 is the extreme: the two compliances are")
    print("   ORTHOGONAL, they span the deviatoric plane, and the overlap")
    print("   is ISOTROPIC -- eta_1 under the sum, 2 eta_1 under the")
    print("   average. The nearest-fault rule is fully anisotropic there.")
    print("   (The n_eff column is meaningless at 45: the tensor is")
    print("   isotropic, so its eigenvectors are degenerate.)")
