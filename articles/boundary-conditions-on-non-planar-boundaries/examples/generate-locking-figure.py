"""The figure for "A constraint that is satisfied, and wrong".

Three solves of the same annulus problem, rendered with the same colour scale:
the exact solution, a direct penalty written against the facet normal, and the
same penalty written against the measure-weighted node normal. The coefficient
is 1e6 in both penalty panels, so the only difference between them is the
normal.

Writes:
    figures/locking.png   the three-panel figure
    figures/banner.png    a wide two-panel crop for the article banner

    python3 generate-locking-figure.py

Run against underworld3 `bugfix/multiplier-traction` (PR #617); the
constrained solver's `traction()` is the fix this note prompted.
"""
import pathlib

import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True

import underworld3 as uw
import underworld3.visualisation as vis

import stress as S

CELL = 0.075
PENALTY = 1.0e6
HERE = pathlib.Path(__file__).resolve().parent
FIGURES = HERE.parent / "figures"


def speed_mesh(mode):
    """(pyvista mesh carrying |u|, mesh edges, max speed) for one treatment."""
    mesh, stokes, v, exact = S.build(mode, cell=CELL, penalty=PENALTY)
    stokes.solve()
    assert S.converged(stokes), "%s did not converge" % mode
    pv_v = vis.meshVariable_to_pv_mesh_object(v)
    u = np.squeeze(np.asarray(v.array))
    pv_v.point_data["speed"] = np.linalg.norm(u, axis=1)
    edges = vis.mesh_to_pv_mesh(mesh).extract_all_edges()
    return pv_v, edges, exact, v


def exact_speed_mesh(reference):
    """The same object built from the exact velocity, for the first panel."""
    mesh, stokes, v, exact = reference
    field = uw.discretisation.MeshVariable("Uplot", v.mesh, v.mesh.dim, degree=2)
    field.data[:] = exact.evaluate("velocity", field.coords)
    pv_v = vis.meshVariable_to_pv_mesh_object(field)
    pv_v.point_data["speed"] = np.linalg.norm(
        np.squeeze(np.asarray(field.array)), axis=1)
    return pv_v


def panel(plotter, index, pv_mesh, edges, title, clim, zoom=1.3):
    plotter.subplot(0, index)
    plotter.set_background("white")
    plotter.add_mesh(pv_mesh, scalars="speed", cmap="RdBu_r", clim=clim,
                     show_edges=False, lighting=False, show_scalar_bar=False)
    plotter.add_mesh(edges, color="black", line_width=0.4, lighting=False)
    plotter.add_text(title, position="upper_left", font_size=12, color="black")
    plotter.view_xy()
    plotter.camera.zoom(zoom)


def main():
    facet_pv, facet_edges, exact, facet_v = speed_mesh("penalty")
    node_pv, node_edges, _exact, node_v = speed_mesh("penalty_node")

    # The exact field on the node-normal run's mesh, which is the same mesh.
    truth = uw.discretisation.MeshVariable("Utruth", node_v.mesh, node_v.mesh.dim,
                                           degree=2)
    truth.data[:] = _exact.evaluate("velocity", truth.coords)
    truth_pv = vis.meshVariable_to_pv_mesh_object(truth)
    truth_pv.point_data["speed"] = np.linalg.norm(
        np.squeeze(np.asarray(truth.array)), axis=1)

    top = float(truth_pv.point_data["speed"].max())
    clim = (0.0, top)
    print("colour scale 0 to %.4e" % top)
    for name, pv_mesh in (("exact", truth_pv), ("facet", facet_pv), ("node", node_pv)):
        print("%-6s max speed %.4e" % (name, float(pv_mesh.point_data["speed"].max())))

    FIGURES.mkdir(exist_ok=True)

    plotter = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(1650, 620))
    panel(plotter, 0, truth_pv, node_edges, "exact", clim)
    panel(plotter, 1, facet_pv, facet_edges, "penalty, facet normal", clim)
    panel(plotter, 2, node_pv, node_edges, "penalty, node normal", clim)
    plotter.screenshot(str(FIGURES / "locking.png"))
    plotter.close()

    banner = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1600, 560))
    panel(banner, 0, facet_pv, facet_edges, "", clim, zoom=1.9)
    panel(banner, 1, truth_pv, node_edges, "", clim, zoom=1.9)
    banner.screenshot(str(FIGURES / "banner.png"))
    banner.close()
    print("wrote", FIGURES / "locking.png", "and", FIGURES / "banner.png")


if __name__ == "__main__":
    main()
