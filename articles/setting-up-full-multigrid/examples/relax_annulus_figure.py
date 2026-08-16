"""Figure: what the coarse mesh leaves in the fine one, and what relax() does.

Run from the repository root:

    python3 articles/setting-up-full-multigrid/examples/relax_annulus_figure.py

The annulus is the clearer subject than a box: its base mesh is coarse relative
to the curvature, so the coarse cells' edges survive as visible seams across the
refined mesh. It also shows that the boundary snapping holds -- every node that
starts on a bounding circle is still exactly on it afterwards, because relax()
moves interior coordinates only.

Run against underworld3 `development` at commit `0addec15`
(0addec1595f8d7a59b99e15b42455267a73dab86, 2026-08-15). `uw.__version__`
reports 0.0.0 for every build, so the commit is the only thing that
identifies what these numbers came from.
"""
import numpy as np
import underworld3 as uw
import pyvista as pv

RADIUS_INNER, RADIUS_OUTER = 0.5, 1.0
CELL_SIZE = 0.25          # the BASE mesh; refinement takes it from there
REFINEMENT = 2
OUT = "articles/setting-up-full-multigrid/figures/relax-annulus.png"

pv.global_theme.allow_empty_mesh = True
pv.global_theme.background = "white"

mesh = uw.meshing.Annulus(radiusInner=RADIUS_INNER, radiusOuter=RADIUS_OUTER,
                          cellSize=CELL_SIZE, qdegree=2, refinement=REFINEMENT)
before = uw.visualisation.mesh_to_pv_mesh(mesh)
print("cells %d, hierarchy levels %d" % (before.n_cells, len(mesh.dm_hierarchy)))


def report(pvm, tag):
    """Element quality, and whether the bounding circles are still exact."""
    cells = pvm.cells.reshape(-1, 4)[:, 1:]
    p = pvm.points[:, :2]
    a = np.linalg.norm(p[cells[:, 1]] - p[cells[:, 2]], axis=1)
    b = np.linalg.norm(p[cells[:, 2]] - p[cells[:, 0]], axis=1)
    c = np.linalg.norm(p[cells[:, 0]] - p[cells[:, 1]], axis=1)
    s = 0.5 * (a + b + c)
    area = np.sqrt(np.maximum(s * (s - a) * (s - b) * (s - c), 0.0))
    q = 2.0 * (area / np.maximum(s, 1e-30)) / np.maximum(
        a * b * c / np.maximum(4.0 * area, 1e-30), 1e-30)
    r = np.linalg.norm(p, axis=1)
    near = (np.abs(r - RADIUS_OUTER) < 2e-3) | (np.abs(r - RADIUS_INNER) < 2e-3)
    exact = (np.abs(r - RADIUS_OUTER) < 1e-6) | (np.abs(r - RADIUS_INNER) < 1e-6)
    print("%-7s q median %.3f  10th pct %.3f  min %.3f | on the circle: %d/%d"
          % (tag, np.median(q), np.percentile(q, 10), q.min(),
             exact.sum(), near.sum()))


report(before, "before")
mesh.relax()
after = uw.visualisation.mesh_to_pv_mesh(mesh)
report(after, "after")

pl = pv.Plotter(shape=(1, 2), window_size=(1900, 950), off_screen=True, border=False)
for col, (m, title) in enumerate(((before, "Annulus, refinement=2"),
                                  (after, "after relax()"))):
    pl.subplot(0, col)
    pl.set_background("white")
    pl.add_mesh(m, color="white", show_edges=True, edge_color="#1a1a1a",
                line_width=1.1, lighting=False)
    pl.add_text(title, position="upper_edge", font_size=14, color="black")
    pl.enable_parallel_projection()
    pl.view_xy()
    pl.reset_camera(bounds=(-1.05, 1.05, -1.05, 1.12, -0.05, 0.05))
pl.screenshot(OUT)
print("wrote", OUT)
