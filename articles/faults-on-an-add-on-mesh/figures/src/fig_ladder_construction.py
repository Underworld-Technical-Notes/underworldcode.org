"""The split-fault ladder for UWTN 2026-022: (a) the finest ladder, (b) its split,
(c) the multigrid hierarchy under it.

Built with the production construction, ``place_fault_ribbon_2d(..., mesher="ladder")``:
the spine is the fault's own sample points at rung spacing S, the two rails lie S
either side (band width 2S), a rung joins rail, spine and rail at every spine point,
one element on each side, and the band extends one margin rung beyond each tip. The
carve between the band and the base cells is refilled with graded triangles. The
split duplicates every interior spine vertex; the tip vertices stay single.

The hierarchy is the production one (Louis, 2026-11-01; underworld3 #892): the split
child above the base's own levels, welded, as ``set_custom_fmg(base.multigrid_levels)``
builds it. On the child, the cells that are not cells of the base's finest level (the
band and its graded fill) are tinted: their nodes, with one layer of base cells around
them, make the finest level's patch, which the smoother solves by LU.

Fault: the note's fixture, straight from (0.30, 0.45) to (0.70, 0.55). Base: three
levels, cell size 1/8, 1/16, 1/32 (h_b = 1/32 on the finest); S = L/80 = 0.0052, so
the band ratio is h_b/S = 6.1.

    cd figures/src && python fig_ladder_construction.py \\
        -uw_skills <underworld3>/.claude/skills/uw-line-diagrams
"""
import os
import sys

import numpy as np
from matplotlib.collections import LineCollection, PolyCollection

import underworld3 as uw
from underworld3.utilities.place_surface import place_fault_ribbon_2d

params = uw.Params(
    uw_out="../ladder-construction",  # output stem (pdf, svg, png); the note uses the png
    uw_skills="",                     # the uw-line-diagrams skill directory (holds uwfig.py)
)
sys.path.insert(0, str(params.uw_skills))
import uwfig as F  # noqa: E402

FAULT = "Fault"
A, B = np.array([0.30, 0.45]), np.array([0.70, 0.55])
N_FINE = 80                                   # spine intervals at S; a multiple of 4
L = float(np.linalg.norm(B - A))
T_HAT = (B - A) / L
N_HAT = np.array([-T_HAT[1], T_HAT[0]])
S = L / N_FINE
H_B = 1.0 / 32

base = uw.meshing.UnstructuredSimplexBox(minCoords=(0, 0), maxCoords=(1, 1), cellSize=0.125,
                                         regular=False, qdegree=2, refinement=2)
base_levels = base.multigrid_levels                              # h = 1/8, 1/16, 1/32


def trace_at(coarsening):
    """The fault sampled at coarsening x S: every coarsening-th fine spine point."""
    k = np.arange(0, N_FINE + 1, coarsening)
    return A + (k * S)[:, None] * T_HAT


def ladder(host, coarsening, split):
    for clearance in (0.7, 0.5, 0.3):
        try:
            return place_fault_ribbon_2d(host, [(FAULT, trace_at(coarsening))],
                                         2 * S * coarsening, margin_rings=1,
                                         clearance=clearance, split=split, mesher="ladder")
        except RuntimeError as err:
            last = err
    raise last


def cells_of(mesh):
    """Vertex coordinates of every cell, and the edges, from the DM."""
    dm = mesh.dm
    cS, cE = dm.getHeightStratum(0)
    eS, eE = dm.getDepthStratum(1)
    vS, _vE = dm.getDepthStratum(0)
    X = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, 2)
    tris = []
    for c in range(cS, cE):
        cl = dm.getTransitiveClosure(c)[0]
        tris.append(X[[int(p) - vS for p in cl if vS <= p < vS + len(X)]])
    edges = np.array([[X[int(p) - vS] for p in dm.getCone(e)] for e in range(eS, eE)])
    return tris, edges, X


def fault_sides(mesh):
    """The Plus and Minus facets of the split fault, as segments."""
    dm = mesh.dm
    eS, eE = dm.getDepthStratum(1)
    vS, _vE = dm.getDepthStratum(0)
    X = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, 2)
    out = {}
    for side in ("Plus", "Minus"):
        lab = dm.getLabel(f"{FAULT}{side}")
        value = mesh.boundaries[f"{FAULT}{side}"].value
        ids = [int(e) for e in lab.getStratumIS(value).getIndices() if eS <= int(e) < eE]
        out[side] = np.array([[X[int(p) - vS] for p in dm.getCone(e)] for e in ids])
    return out


def draw_cells(ax, mesh, band):
    tris, _edges, _X = cells_of(mesh)
    ax.add_collection(PolyCollection([tris[i] for i in np.nonzero(band)[0]],
                                     facecolors=F.TINT_FLUID, edgecolors="none", zorder=0))
    ax.add_collection(PolyCollection(tris, facecolors="none", **{
        "edgecolors": F.MESH, "linewidths": F.LINE["mesh"]["lw"]}, zorder=1))


def draw_ladder(ax, spine, half_width, *, rungs_lw=0.8):
    """Rails, rungs and spine, from the spine points (the mesh's own vertices)."""
    upper, lower = spine + half_width * N_HAT, spine - half_width * N_HAT
    rail = dict(color=F.INK, lw=0.8, zorder=3)
    ax.plot(upper[:, 0], upper[:, 1], **rail)
    ax.plot(lower[:, 0], lower[:, 1], **rail)
    ax.add_collection(LineCollection(np.stack([upper, lower], axis=1), colors=F.INK,
                                     linewidths=rungs_lw, zorder=3))
    return upper, lower


def lead(ax, text_xy, target_xy, text, ha="left"):
    """A leader drawn over the band tint and the ladder but under the tip marker, so a
    leader to the tip ends at the circle; the label box sits over the leader."""
    ax.annotate("", xy=target_xy, xytext=text_xy, zorder=4.5,
                arrowprops=F.arrow_style("leader", shrinkA=0, shrinkB=0))
    F.label(ax, text_xy[0], text_xy[1], text, ha=ha, zorder=7)


def clear_direction(mesh, vertex, lo, hi):
    """The direction (degrees, in [lo, hi]) farthest in angle from every mesh edge at
    ``vertex``, so a leader into the vertex cannot be read as an edge."""
    _tris, edges, _X = cells_of(mesh)
    at_v = np.linalg.norm(edges - vertex, axis=2) < 1e-9
    k = np.nonzero(at_v.any(axis=1))[0]
    other = np.where(at_v[k, 0][:, None], edges[k, 1], edges[k, 0])
    ang = np.degrees(np.arctan2(other[:, 1] - vertex[1], other[:, 0] - vertex[0]))
    cand = np.arange(lo, hi + 0.5, 1.0)
    sep = np.min(np.abs((cand[:, None] - ang[None, :] + 180.0) % 360.0 - 180.0), axis=1)
    best = int(np.argmax(sep))
    uw.pprint(f"tip leader at {cand[best]:.0f} deg, {sep[best]:.0f} deg from the nearest "
              f"edge (edges at {np.sort(np.round(ang) % 360).astype(int).tolist()})")
    return np.radians(cand[best])


def measure(ax, p0, p1, text, offset, text_offset=0.0):
    """A dimension between p0 and p1 with extension lines, shifted ``offset`` along
    its own normal (data units); the label sits ``text_offset`` further out."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
    q0, q1 = p0 + offset * nrm, p1 + offset * nrm
    ext = dict(color=F.INK, lw=0.5, zorder=6)
    for p, q in ((p0, q0), (p1, q1)):
        r = q + 0.25 * np.sign(offset) * abs(offset) * nrm
        ax.plot([p[0], r[0]], [p[1], r[1]], **ext)
    ax.annotate("", xy=q1, xytext=q0, zorder=6, arrowprops=dict(
        arrowstyle="<|-|>,head_length=0.5,head_width=0.18", lw=0.5, color=F.INK,
        shrinkA=0, shrinkB=0))
    m = 0.5 * (q0 + q1) + np.sign(offset) * text_offset * nrm
    F.label(ax, m[0], m[1], text)


def window(ax, x0, x1, y0, y1):
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")


def base_edge_near(mesh, target, avoid, box):
    """A base-size cell edge near ``target``, at least ``avoid`` from the fault line
    and inside ``box`` = (x0, x1, y0, y1)."""
    _tris, edges, _X = cells_of(mesh)
    length = np.linalg.norm(edges[:, 1] - edges[:, 0], axis=1)
    mid = edges.mean(axis=1)
    off = np.abs((mid - A) @ N_HAT)
    x0, x1, y0, y1 = box
    inside = np.all((edges[:, :, 0] > x0) & (edges[:, :, 0] < x1)
                    & (edges[:, :, 1] > y0) & (edges[:, :, 1] < y1), axis=1)
    ok = (np.abs(length - H_B) < 0.2 * H_B) & (off > avoid) & inside
    k = np.argmin(np.where(ok, np.linalg.norm(mid - target, axis=1), np.inf))
    return edges[k]


# ---- the meshes -------------------------------------------------------------------
fine_open, info_open = ladder(base, 1, split=False)
fine_split, info_split = ladder(base, 1, split=True)


def new_cells(mesh, host):
    """Cells of mesh that are not cells of host: the band and its graded fill."""
    def key(tri):
        return tuple(sorted(map(tuple, np.round(tri, 10))))
    old = {key(t) for t in cells_of(host)[0]}
    return np.array([key(t) not in old for t in cells_of(mesh)[0]])

spine = np.asarray(info_open["extended"][0])[:, :2]   # user samples plus the margin points
tip, margin = A, spine[0]                               # the left tip and its margin point

# ---- the figure: (a) and (b) on top, (c) four panels below -------------------------
fig = F.plt.figure(figsize=(183 * F.MM, 102 * F.MM))
X0, X1 = A[0] - 4.5 * S, A[0] + 15.0 * S                # close-up at the left tip
Y0, Y1 = A[1] - 6.0 * S, A[1] + 7.5 * S
ax_a = fig.add_axes([0.00, 0.343, 0.495, 0.657])
ax_b = fig.add_axes([0.505, 0.343, 0.495, 0.657])
ax_c = [fig.add_axes([0.0 + k * 0.2513, 0.0, 0.2462, 0.307]) for k in range(4)]


def at(fx, fy, x0=None, x1=None, y0=None, y1=None):
    """A point at fractions of a panel's window."""
    x0, x1 = (X0, X1) if x0 is None else (x0, x1)
    y0, y1 = (Y0, Y1) if y0 is None else (y0, y1)
    return (x0 + fx * (x1 - x0), y0 + fy * (y1 - y0))


# (a) the finest ladder, unsplit
draw_cells(ax_a, fine_open, info_open["band"])
upper, lower = draw_ladder(ax_a, spine, S)
ax_a.plot(spine[1:, 0], spine[1:, 1], color=F.INK, lw=1.2, zorder=4)            # the fault
ax_a.plot(spine[:2, 0], spine[:2, 1], **F.line_style("hidden"), zorder=4)       # margin
ax_a.plot(*tip, marker="o", ms=4.5, mfc="white", mec=F.INK, mew=0.8, zorder=5)
mid_rung = 0.5 * (upper[0] + margin)                  # the middle of the rung's upper element
lead(ax_a, tuple(mid_rung + 4.2 * S * np.array([np.cos(np.radians(140)), np.sin(np.radians(140))])),
     tuple(mid_rung), "margin rung")
th = clear_direction(fine_open, tip, 200, 275)
lead(ax_a, tuple(tip + 5.0 * S * np.array([np.cos(th), np.sin(th)])), tuple(tip), "tip")
F.leader(ax_a, at(0.62, 0.95), tuple(upper[10]), "rail", ha="left")
F.leader(ax_a, at(0.36, 0.12), tuple(0.5 * (spine[6] + lower[6])), "rung", ha="left")
F.leader(ax_a, at(0.56, 0.12), tuple(spine[10]), "spine", ha="left")
measure(ax_a, upper[5], upper[6], "$S$", offset=1.2 * S, text_offset=0.7 * S)
measure(ax_a, lower[11], spine[11], "$S$", offset=-1.2 * S, text_offset=0.6 * S)
e = base_edge_near(fine_open, np.array(at(0.75, 0.80)), avoid=3 * S,
                   box=(X0 + S, X1 - S, Y0 + S, Y1 - S))
measure(ax_a, e[0], e[1], "$h_b$", offset=0.8 * S, text_offset=0.8 * S)
F.label(ax_a, *at(0.01, 0.99), "(a)", ha="left", va="top", box=False)
window(ax_a, X0, X1, Y0, Y1)

# (b) the split: interior spine vertices duplicated, the sides drawn apart
draw_cells(ax_b, fine_split, info_split["band"])
draw_ladder(ax_b, spine, S, rungs_lw=0.5)
sides = fault_sides(fine_split)
gap = 0.22 * S
for side, sgn, ls in (("Plus", 1.0, "-"), ("Minus", -1.0, (0, (3, 1.5)))):
    segs = sides[side] + sgn * gap * N_HAT
    ax_b.add_collection(LineCollection(segs, colors=F.INK, linewidths=1.2, linestyles=[ls],
                                       zorder=4))
    verts = np.unique(np.round(sides[side].reshape(-1, 2), 12), axis=0)
    interior = np.linalg.norm(verts - tip, axis=1) > 1e-9
    ax_b.plot(*(verts[interior] + sgn * gap * N_HAT).T, ls="none", marker="o", ms=2.2,
              mfc=F.INK, mec="none", zorder=5)
ax_b.plot(*tip, marker="o", ms=4.5, mfc="white", mec=F.INK, mew=0.8, zorder=5)
F.label(ax_b, *(0.5 * (spine[12] + spine[13]) + 1.45 * S * N_HAT), "$+$")
F.label(ax_b, *(0.5 * (spine[12] + spine[13]) - 1.45 * S * N_HAT), "$-$")
th = clear_direction(fine_split, tip, 200, 275)
lead(ax_b, tuple(tip + 5.0 * S * np.array([np.cos(th), np.sin(th)])), tuple(tip), "tip, not split")
F.label(ax_b, *at(0.01, 0.99), "(b)", ha="left", va="top", box=False)
window(ax_b, X0, X1, Y0, Y1)

# (c) the hierarchy: the split child (S on h_b) above the base's own levels, welded;
# on the child the cells that are not base cells (band and fill) are tinted
CX0, CX1 = A[0] - 9.0 * S, A[0] + 40.0 * S
CY0, CY1 = A[1] - 12.0 * S, A[1] + 22.0 * S

ax = ax_c[0]
draw_cells(ax, fine_split, new_cells(fine_split, base_levels[-1]))
draw_ladder(ax, spine, S, rungs_lw=0.5)
ax.plot(spine[1:, 0], spine[1:, 1], color=F.INK, lw=1.2, zorder=4)
F.label(ax, *at(0.12, 0.97, CX0, CX1, CY0, CY1), "$S$ on $h_b$, split", ha="left", va="top")
window(ax, CX0, CX1, CY0, CY1)

# the base's levels: base cells only, the fault (hidden) is not in the mesh
for ax, level, h in zip(ax_c[1:], base_levels[::-1], ("h_b", "2h_b", "4h_b")):
    draw_cells(ax, level, np.zeros(level.dm.getHeightStratum(0)[1], dtype=bool))
    ax.plot([A[0], B[0]], [A[1], B[1]], **F.line_style("hidden"), zorder=4)
    F.label(ax, *at(0.12, 0.97, CX0, CX1, CY0, CY1), f"welded, ${h}$", ha="left", va="top")
    window(ax, CX0, CX1, CY0, CY1)
F.label(ax_c[0], *at(0.01, 0.99, CX0, CX1, CY0, CY1), "(c)", ha="left", va="top", box=False)

stem = str(params.uw_out)
F.save(fig, stem)
ncells = [m.dm.getHeightStratum(0)[1] for m in base_levels] + [
    fine_split.dm.getHeightStratum(0)[1]]
uw.pprint(f"wrote {stem}.pdf/.svg/.png; S = {S:.5f}, h_b/S = {H_B / S:.2f}, "
          f"spine points {len(spine)}; hierarchy cells (4h_b, 2h_b, h_b, child) {ncells}, "
          f"of which band and fill {int(new_cells(fine_split, base_levels[-1]).sum())}")
