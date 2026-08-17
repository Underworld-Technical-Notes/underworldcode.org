"""Banner: three of the viscosity structures the exact solutions cover.

Run from the repository root:

    python3 articles/testing-a-solver-against-exact-solutions/examples/banner.py

The note says the family covers "a viscosity jump, an exponentially varying
viscosity, a laterally oscillating one". This is that sentence: SolCx's step,
SolKz's exponential gradient, SolM's lateral oscillation, each evaluated from
the solution's own symbolic `fn_viscosity` onto a mesh variable and rendered.

Run against underworld3 `development` at commit `0addec15`
(0addec1595f8d7a59b99e15b42455267a73dab86, 2026-08-15). `uw.__version__`
reports 0.0.0 for every build, so the commit is the only thing that identifies
what this came from.
"""
import numpy as np
import underworld3 as uw
import pyvista as pv

OUT = "articles/testing-a-solver-against-exact-solutions/figures/banner.png"
RES = 64

pv.global_theme.allow_empty_mesh = True
pv.global_theme.background = "white"

panels = []
for name, build in (
        ("SolCx",  lambda m: uw.analytic.SolCx(m, eta_B=1.0e4)),
        ("SolKz",  lambda m: uw.analytic.SolKz(m)),
        ("SolM",   lambda m: uw.analytic.SolM(m)),
):
    mesh = uw.meshing.StructuredQuadBox(elementRes=(RES, RES))
    solution = build(mesh)
    pvm = uw.visualisation.mesh_to_pv_mesh(mesh)
    # Evaluate the solution's own symbolic viscosity straight onto the render
    # points. No MeshVariable in between: nothing here is being solved, so
    # there is nothing to project.
    values = np.asarray(
        uw.function.evaluate(solution.fn_viscosity, pvm.points[:, :mesh.dim]),
        dtype=float).reshape(-1)
    # log10, because these span four orders and a linear map shows one band.
    pvm.point_data["log10_eta"] = np.log10(np.maximum(values, 1e-30))
    print("%-6s log10 eta in [%.2f, %.2f]"
          % (name, pvm.point_data["log10_eta"].min(),
             pvm.point_data["log10_eta"].max()))
    panels.append((name, pvm))

pl = pv.Plotter(shape=(1, 3), window_size=(2100, 700), off_screen=True,
                border=False)
for col, (name, pvm) in enumerate(panels):
    pl.subplot(0, col)
    pl.set_background("white")
    pl.add_mesh(pvm, scalars="log10_eta", cmap="RdBu_r", show_edges=False,
                show_scalar_bar=False, lighting=False)
    pl.enable_parallel_projection()
    pl.view_xy()
    pl.reset_camera(bounds=(0.0, 1.0, 0.0, 1.0, -0.05, 0.05))
    pl.camera.zoom(1.30)
pl.screenshot(OUT)
print("wrote", OUT)
