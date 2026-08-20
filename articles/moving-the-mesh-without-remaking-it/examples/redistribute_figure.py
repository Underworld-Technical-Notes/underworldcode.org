"""Figure for UWTN 2026-011: the same mesh, before and after redistribution.

The point the figure has to make is that nothing is added. Same node count,
same connectivity, same partition -- the nodes simply move to where the metric
asks for them. So both panels are one mesh object at two moments, and the
counts are printed to prove it.

The metric is built the idiomatic way, from the gradient of a field, which is
the code the note itself shows.
"""
import pathlib

import numpy as np
import sympy
import underworld3 as uw
import pyvista as pv

pv.global_theme.allow_empty_mesh = True
pv.global_theme.background = "white"

SLOPE, W = 0.45, 0.07

mesh = uw.meshing.UnstructuredSimplexBox(
    minCoords=(0.0, 0.0), maxCoords=(1.0, 1.0), cellSize=1.0 / 22, qdegree=2)

x, y = mesh.X.coords_sym if hasattr(mesh.X, "coords_sym") else mesh.X
d = (y - 0.30 - SLOPE * x) / np.sqrt(1 + SLOPE**2)

# An ANISOTROPIC metric: large across the band normal, so the mover is asked
# for cells that are thin ACROSS the feature and long ALONG it. A scalar
# metric can only ask for smaller cells; this asks for the right ones.
n = sympy.Matrix([-SLOPE, 1.0]) / np.sqrt(1 + SLOPE**2)
Rf = 6.0
M = sympy.eye(2) + (Rf**2 - 1.0) * sympy.exp(-((d / W) ** 2)) * (n * n.T)

pv_before = uw.visualisation.mesh_to_pv_mesh(mesh)
before = np.array(pv_before.points, copy=True)

uw.meshing.node_redistribution(
    mesh, M,
    method_kwargs=dict(step_frac=0.2, accel="none", momentum=0.0,
                       n_outer=400),
    slip_surfaces=True, skip_threshold=None)

pv_after = uw.visualisation.mesh_to_pv_mesh(mesh)
after = np.array(pv_after.points, copy=True)

print("cells  before/after:", pv_before.n_cells, pv_after.n_cells, flush=True)
print("points before/after:", pv_before.n_points, pv_after.n_points, flush=True)
print("max node displacement:", np.abs(after - before).max(), flush=True)


def stats(pvm, label):
    cells = pvm.cells.reshape(-1, 4)[:, 1:]
    p = pvm.points[:, :2]
    u, v = p[cells[:, 1]] - p[cells[:, 0]], p[cells[:, 2]] - p[cells[:, 0]]
    area = 0.5 * np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0])
    h = np.sqrt(area)
    cx = p[cells].mean(axis=1)
    dd = (cx[:, 1] - 0.30 - SLOPE * cx[:, 0]) / np.sqrt(1 + SLOPE**2)
    on, off = np.abs(dd) < 1.5 * W, np.abs(dd) > 6 * W
    r = float(np.median(h[on]) / np.median(h[off]))
    print("%-8s on-band/bulk h = %.3f   total area %.6f   min h %.4f"
          % (label, r, area.sum(), h.min()), flush=True)
    return r


r0 = stats(pv_before, "before")
r1 = stats(pv_after, "after")
print("=> %.2fx finer on the band" % (r0 / r1), flush=True)

pl = pv.Plotter(shape=(1, 2), window_size=(1900, 1000), off_screen=True,
                border=False)
for col, (pvm, title) in enumerate(
        ((pv_before, "uniform mesh"),
         (pv_after, "the same mesh, nodes redistributed"))):
    pl.subplot(0, col)
    pl.set_background("white")
    pl.add_mesh(pvm, color="white", show_edges=True, edge_color="#1a1a1a",
                line_width=1.0, lighting=False)
    pl.add_text(title, position="upper_edge", font_size=13, color="black")
    pl.enable_parallel_projection()
    pl.view_xy()
    pl.reset_camera(bounds=(-0.01, 1.01, -0.01, 1.08, -0.05, 0.05))
# Beside the article, not beside the author: an absolute path here breaks on any
# other machine and puts a home directory into a published repository.
out = pathlib.Path(__file__).resolve().parent.parent / "figures" / "redistribute-before-after.png"
out.parent.mkdir(exist_ok=True)
pl.screenshot(str(out))
print("wrote", out, flush=True)
