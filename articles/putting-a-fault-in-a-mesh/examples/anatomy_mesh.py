"""The one mesh behind the anatomy figures (band-anatomy, split-anatomy).

A structured triangulation of [0,3] x [0,1], twelve cells by four, and a
gently curved fault trace across its middle from x = 0.5 to x = 2.5. The
CONFORMING mesh is the grid bent so that the trace runs along its edges
(the row y = 0.5 lifted onto the curve, the displacement tapering to
nothing at the top and bottom walls) — the remeshing, in miniature. The
non-conforming panel keeps the grid flat and lets the same curve cross it.
"""
import math

H = 0.25
NX, NY = 12, 4
AMP = 0.12                    # the curve's rise at mid-span
X0, X1 = 0.5, 2.5             # the trace's span
W = 0.5                       # the band width: one cell either side


def rise(x):
    """The trace's offset from y = 0.5: a half sine over its span, zero
    at both tips and beyond them."""
    if x <= X0 or x >= X1:
        return 0.0
    return AMP * math.sin(math.pi * (x - X0) / (X1 - X0))


def curve(x):
    return [x, 0.5 + rise(x)]


def normal(x):
    """Unit normal to the trace at x (pointing +y)."""
    if x <= X0 or x >= X1:
        return [0.0, 1.0]
    dy = AMP * math.pi / (X1 - X0) * math.cos(math.pi * (x - X0) / (X1 - X0))
    n = math.hypot(1.0, dy)
    return [-dy / n, 1.0 / n]


def grid():
    """The flat grid: (coords, tris, vid) with tris as vertex triples."""
    verts, coords = {}, []

    def vid(i, j):
        if (i, j) not in verts:
            verts[(i, j)] = len(coords)
            coords.append([i * H, j * H])
        return verts[(i, j)]

    tris = []
    for i in range(NX):
        for j in range(NY):
            a, b = vid(i, j), vid(i + 1, j)
            c, d = vid(i + 1, j + 1), vid(i, j + 1)
            tris.append([a, b, c])
            tris.append([a, c, d])
    return coords, tris, vid


def conforming(coords):
    """Bend the grid onto the curve: each vertex rises by the trace's
    offset at its x, scaled by (1 - |y - 0.5| / 0.5) so the walls stay
    put. The row y = 0.5 lands exactly on the curve."""
    out = []
    for x, y in coords:
        out.append([x, y + rise(x) * (1.0 - abs(y - 0.5) / 0.5)])
    return out


def centroids(coords, tris):
    return [[sum(coords[v][0] for v in t) / 3.0,
             sum(coords[v][1] for v in t) / 3.0] for t in tris]


def chain(vid):
    """The trace's vertices on the conforming mesh: the middle row over
    the span, first tip to second."""
    return [vid(i, NY // 2) for i in range(int(X0 / H), int(X1 / H) + 1)]


def distance_to_curve(p, n_samp=400):
    """Distance from p to the trace, and the x of the nearest sample."""
    best, bx = float("inf"), X0
    for k in range(n_samp + 1):
        x = X0 + (X1 - X0) * k / n_samp
        c = curve(x)
        d = math.hypot(p[0] - c[0], p[1] - c[1])
        if d < best:
            best, bx = d, x
    return best, bx
