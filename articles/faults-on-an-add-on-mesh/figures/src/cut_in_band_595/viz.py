"""Shared rendering conventions for this directory.

Mesh grey on white, no lighting; weak material pale behind; slip carried
ON the trace in physical space with one shared colour scale across
compared panels. Line plots are matplotlib; nothing on a mesh is.
"""
import numpy as np

CMAP = "plasma"          # sequential, reads at every level against grey
EDGE = "#b8bfc6"
PALE = "#dfe4ea"         # the weak zone, behind everything


def pv_cells(mesh):
    """Points plus the mesh's OWN cell connectivity. Never Delaunay a
    fault mesh: coincident pairs and trace-crossing edges both paint
    lies."""
    import pyvista as pv
    dm = mesh.dm
    vS, vE = dm.getDepthStratum(0)
    cS, cE = dm.getHeightStratum(0)
    X = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, 2)
    faces = []
    for c in range(cS, cE):
        closure, _ = dm.getTransitiveClosure(c)
        faces.extend([3, *[int(p) - vS for p in closure
                           if vS <= int(p) < vE]])
    return pv.PolyData(np.column_stack([X, np.zeros(len(X))]),
                       faces=np.asarray(faces, dtype=np.int64))


def pv_subset(mesh, mask):
    """The cells where ``mask`` is true, as their own PolyData -- used to
    lay the weak zone in pale behind the mesh lines."""
    import pyvista as pv
    dm = mesh.dm
    vS, vE = dm.getDepthStratum(0)
    cS, cE = dm.getHeightStratum(0)
    X = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, 2)
    faces = []
    for c in range(cS, cE):
        if not mask[c - cS]:
            continue
        closure, _ = dm.getTransitiveClosure(c)
        faces.extend([3, *[int(p) - vS for p in closure
                           if vS <= int(p) < vE]])
    return pv.PolyData(np.column_stack([X, np.zeros(len(X))]),
                       faces=np.asarray(faces, dtype=np.int64))


def slip_line(pts, vals, name="slip"):
    import pyvista as pv
    ln = pv.lines_from_points(
        np.column_stack([np.asarray(pts)[:, :2], np.zeros(len(pts))]))
    ln.point_data[name] = np.abs(np.asarray(vals))
    return ln


def frame(plotter, box=(1.0, 1.0), scale=0.55):
    plotter.view_xy()
    plotter.camera.parallel_projection = True
    plotter.camera.focal_point = (0.5 * box[0], 0.5 * box[1], 0.0)
    plotter.camera.position = (0.5 * box[0], 0.5 * box[1], 1.0)
    plotter.camera.parallel_scale = scale
    plotter.set_background("white")
