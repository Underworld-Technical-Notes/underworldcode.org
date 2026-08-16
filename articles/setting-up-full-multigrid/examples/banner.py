"""Banner: the three levels a `refinement=2` mesh carries.

Run from the repository root:

    python3 articles/setting-up-full-multigrid/examples/banner.py

The subject of the note is that a mesh built with `refinement` keeps its coarser
ancestors, and that those are what the preconditioner works on. So the banner is
the hierarchy itself: the gmsh base mesh, and the two refinements built from it,
each one subdividing every cell of the one before and snapping the new boundary
nodes back onto the bounding circles.

Building three meshes at refinement 0, 1 and 2 gives exactly the three levels a
single `refinement=2` mesh holds in `dm_hierarchy` -- same base mesh, same
refinement callback -- and does it through the supported API rather than
reaching into the DMPlex objects.

Run against underworld3 `development` at commit `0addec15`
(0addec1595f8d7a59b99e15b42455267a73dab86, 2026-08-15). `uw.__version__`
reports 0.0.0 for every build, so the commit is the only thing that
identifies what these numbers came from.
"""
import underworld3 as uw
import pyvista as pv

RADIUS_INNER, RADIUS_OUTER = 0.5, 1.0
CELL_SIZE = 0.25          # the BASE mesh; refinement takes it from there
OUT = "articles/setting-up-full-multigrid/figures/banner.png"

pv.global_theme.allow_empty_mesh = True
pv.global_theme.background = "white"

levels = []
for refinement in (0, 1, 2):
    mesh = uw.meshing.Annulus(radiusInner=RADIUS_INNER, radiusOuter=RADIUS_OUTER,
                              cellSize=CELL_SIZE, qdegree=2,
                              refinement=refinement)
    pvm = uw.visualisation.mesh_to_pv_mesh(mesh)
    print("refinement %d: %6d cells, %d hierarchy level(s)"
          % (refinement, pvm.n_cells, len(mesh.dm_hierarchy)))
    levels.append(pvm)

# Wide and short: a banner is cropped hard on a narrow screen, so the three
# panels have to read at a glance and nothing may depend on fine detail.
pl = pv.Plotter(shape=(1, 3), window_size=(2100, 700), off_screen=True,
                border=False)
for col, pvm in enumerate(levels):
    pl.subplot(0, col)
    pl.set_background("white")
    # Line width drops as the cells get smaller, so the finest panel reads as a
    # texture rather than as a block of ink.
    pl.add_mesh(pvm, color="white", show_edges=True, edge_color="#1a1a1a",
                line_width=(1.6, 1.1, 0.7)[col], lighting=False)
    pl.enable_parallel_projection()
    pl.view_xy()
    pl.reset_camera(bounds=(-1.02, 1.02, -1.02, 1.02, -0.05, 0.05))
    # reset_camera leaves a wide margin; a banner is short and gets cropped, so
    # the meshes have to carry the strip rather than float in it.
    pl.camera.zoom(1.35)
pl.screenshot(OUT)
print("wrote", OUT)
