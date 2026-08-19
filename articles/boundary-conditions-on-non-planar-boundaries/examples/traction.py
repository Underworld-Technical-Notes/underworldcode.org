"""Do the two exact methods agree on the surface traction?

The leak measures the constraint. This measures the thing the constraint is
usually wanted FOR: the normal stress on the boundary, which is dynamic
topography once divided by the buoyancy scale.

Two of the four methods return it as an unknown rather than recovering it:

  * the multiplier method, where h on the boundary IS the traction holding the
    constraint;
  * the rotated constraint, where the reaction of the strong constraint is
    sigma_nn.

They are computed by completely different routes, so agreeing is evidence and
disagreeing localises a defect. The weak methods have no comparable object --
their traction has to be recovered from a velocity field that does not satisfy
the constraint exactly, which is the argument the note makes.

STATUS: the vertex comparison converges and the midpoint comparison does NOT,
which is backwards. Measured agreement in the degree-4 amplitude:

    cell     vertex     midpoint
    0.150    5.5e-02    3.6e-03
    0.100    2.0e-02    1.2e-02
    0.075    1.5e-02    3.8e-02
    0.050    8.5e-03    6.9e-02

Vertices converge at about h^1.4. Midpoints get steadily WORSE, which cannot be
right: the solver documents midpoint values of sigma_nn as superconvergent on a
curved boundary and vertex values as carrying the O(h) facet error, so if
anything the two columns should be the other way round.

The likely fault is in this script rather than in either method. The multiplier
carries screened INTERIOR degrees of freedom as well as its boundary trace, and
they are selected here by a radius band that narrows as the mesh refines
(`rad > 1 - 0.3 * cell`). A band that changes with resolution can quietly change
WHICH nodes it admits, and the node counts do drift apart between the two
methods under refinement -- 88 against 84 at cell 0.075 -- which is how the
earlier pairwise version failed outright.

So this is not yet evidence of anything and its numbers are deliberately not
quoted in the note. What is needed is to select the multiplier's boundary trace
from the mesh boundary LABEL rather than by geometry.

Run against underworld3 `development` at commit `0addec15`.
"""
import numpy as np
import sympy

import underworld3 as uw

import leak


def split_trace(coords, values):
    """Order a boundary trace by angle, and split P2 VERTEX nodes from EDGE
    MIDPOINTS.

    They are not interchangeable on a curved boundary. The solver's own warning:
    vertex values of sigma_nn converge only slowly, because the vertex basis has
    zero surface mean and the vertex reaction carries the O(h) facet-geometry
    error; midpoint values are superconvergent (underworld3#414).

    They are also easy to tell apart geometrically. A vertex of the annulus mesh
    sits exactly on the circle; the midpoint of a facet sits on the chord, which
    is inside it by the sagitta.
    """
    rad = np.linalg.norm(coords, axis=1)
    on_circle = np.abs(rad - 1.0) < 1.0e-9
    out = {}
    for name, m in (("vertex", on_circle), ("midpoint", ~on_circle)):
        ang = np.arctan2(coords[m, 1], coords[m, 0])
        order = np.argsort(ang)
        out[name] = (ang[order], np.asarray(values)[m][order])
    return out


def trace_of(field):
    """(coords, values) from either a MeshVariable or an already-extracted pair."""
    if isinstance(field, tuple):
        return field[0], np.squeeze(np.asarray(field[1]))
    return field.coords, np.squeeze(np.asarray(field.array))


def run(mode, cell=0.075):
    mesh, stokes, v = leak.build(mode, cell=cell)
    stokes.solve()
    assert leak.converged(stokes), "%s did not converge" % mode
    if mode == "constraint":
        c, val = trace_of(stokes.multiplier("Upper"))
        # The multiplier also has (screened) interior degrees of freedom, so
        # take its boundary trace. The tolerance has to scale with the mesh:
        # a facet midpoint sits inside the circle by the sagitta, about h^2/8,
        # which at h = 0.15 is 2.8e-3 -- a fixed 1e-3 window silently drops
        # every midpoint at coarse resolution and leaves an empty trace.
        rad = np.linalg.norm(c, axis=1)
        keep = rad > 1.0 - 0.3 * cell
        return split_trace(c[keep], val[keep])
    if mode == "rotated":
        c, val = trace_of(stokes.boundary_normal_traction("Upper"))
        return split_trace(c, val)
    raise ValueError(mode)


def harmonic(angles, values, degree=4):
    """Amplitude of the degree-n harmonic in a boundary trace.

    Comparing node by node is fragile -- the two methods do not return the same
    node set, and the counts drift apart under refinement. The forcing here is a
    single harmonic, so the traction is dominated by one too, and its amplitude
    is both resolution-independent and the quantity dynamic topography is built
    from. A least-squares projection onto cos(n.theta) and sin(n.theta) needs no
    correspondence between the two traces at all.
    """
    v = values - values.mean()
    c = 2.0 * np.mean(v * np.cos(degree * angles))
    s = 2.0 * np.mean(v * np.sin(degree * angles))
    return float(np.hypot(c, s))


def convergence(cells=(0.15, 0.10, 0.075, 0.05)):
    """Do the two routes converge to the SAME traction?

    Agreeing once could be a coincidence of scale. Agreeing better as the mesh
    refines is what says both are approximating one thing.
    """
    print("| cell size | vertex | edge midpoint |")
    print("|---|---|---|")
    for cell in cells:
        mult = run("constraint", cell=cell)
        rot = run("rotated", cell=cell)
        row = []
        for kind in ("vertex", "midpoint"):
            h1 = harmonic(*mult[kind])
            h2 = harmonic(*rot[kind])
            row.append("%.2e" % (abs(h1 - h2) / max(h1, h2)))
        print("| %.3f | %s |" % (cell, " | ".join(row)))


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["converge"]:
        convergence()
        raise SystemExit
    mult = run("constraint")
    rot = run("rotated")
    for kind in ("vertex", "midpoint"):
        a1, t1 = mult[kind]
        a2, t2 = rot[kind]
        # Both are determined only up to a constant on an enclosed boundary, so
        # the deviation is the part carrying the signal -- and the part dynamic
        # topography is built from.
        d1, d2 = t1 - t1.mean(), t2 - t2.mean()
        print("%-9s multiplier n=%3d amp=%.3e | reaction n=%3d amp=%.3e"
              % (kind, len(d1), np.abs(d1).max(), len(d2), np.abs(d2).max()))
        if len(d1) == len(d2) and np.allclose(a1, a2, atol=1e-9):
            scale = max(np.abs(d1).max(), np.abs(d2).max())
            print("%-9s   agreement: max|diff| / max|dev| = %.3e"
                  % ("", np.abs(d1 - d2).max() / scale))
