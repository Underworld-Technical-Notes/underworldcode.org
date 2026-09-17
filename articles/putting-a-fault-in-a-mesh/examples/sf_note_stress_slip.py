"""Figure for UWTN 2026-017: the cut and the band on the same network,
stress and slip, at the width where they agree.

Both columns are the rig at w = 0.005 (superfine): the split node, and
the TI band at eta_1/w = 0.1, the ratio the convergence test holds
fixed. Background is log10 tau_II on one scale; every trace is drawn as
a tube coloured by the SIGNED slip rate in each representation's own
currency -- the pair jump on the cut, the velocity jump across the
band's own edges -- on one two-slope map with grey at zero. The lower
row zooms the Y junction, which is the one place the two disagree.

Dumps come from sf_split_seam_viz.py:

    ../../uwrun sf_split_seam_viz.py -uw_rep split -uw_res superfine
    ../../uwrun sf_split_seam_viz.py -uw_rep ti -uw_res superfine -uw_eta1 5e-4

    ../../uwrun sf_note_stress_slip.py   -> sf_note_stress_slip.png
"""
import numpy as np
import pyvista as pv
from matplotlib.colors import (LinearSegmentedColormap, Normalize,
                               TwoSlopeNorm)

import rig_geometry as G

pv.OFF_SCREEN = True
W, S_F = G.RES["superfine"]
ETA1 = 5e-4

# the upper stepover closed to the split's floor (one uncut edge):
#   ../../uwrun sf_split_seam_viz.py -uw_rep split -uw_res superfine -uw_cont_gap_rungs 1
#   ../../uwrun sf_split_seam_viz.py -uw_rep ti -uw_res superfine -uw_eta1 5e-4 -uw_cont_gap_rungs 1
CASES = [("split node", "fields_split_superfine_gather_np1_rank0_cont1.npz"),
         (f"TI band, eta_1/w = {ETA1 / W:g}",
          "fields_ti_superfine_gather_np1_rank0_eta0.0005_cont1.npz")]

G.CONT_GAP_RUNGS = 1.0
TR = dict(G.traces(S_F, W))
# the Y: the Splay's stop-short tip beside the Main's outgoing limb
CY = TR["Splay"][0]
# the stepover: the Main's upper tip, the Cont segment one edge beyond it
CS = 0.5 * (TR["Main"][-1] + TR["Cont"][0])
# each camera fills its 1000x1000 viewport exactly, so all four
# panels carry the same pixels; the gutter is added afterwards
PANEL, GUTTER = 1000, 22
VIEWS = [((0.5, 0.5), 0.5, ""),
         ((CY[0], CY[1]), 0.085, "the Y junction"),
         ((CS[0], CS[1]), 0.06, "the stepover")]

dumps = [np.load(f, allow_pickle=True) for _t, f in CASES]
allv = np.concatenate([d["logtau"] for d in dumps])
clim = (float(np.percentile(allv, 2)), float(np.percentile(allv, 99.5)))

# the trace colour is the SIGNED slip in each representation's own
# currency, on one map with grey at zero: blue sinistral, green dextral,
# each sense scaled to its own extreme so the small one stays visible.
# With no sinistral slip anywhere (this network, at this width) the blue
# half would be a range that does not exist, so the map drops to its
# dextral half and the bar runs 0 to the peak.
SENSE = ["#1f4fbf", "#7aa6ff", "#d9d9d9", "#7fe07a", "#118a2e"]
alls = np.concatenate([d["slips"][:, 2] for d in dumps])
alls = alls[np.isfinite(alls)]
lo, hi = float(alls.min()), float(alls.max())
TWO_SIDED = lo < -1e-3
if TWO_SIDED:
    SLIP_CMAP = LinearSegmentedColormap.from_list("slip_sense", SENSE)
    NORM = TwoSlopeNorm(vcenter=0.0, vmin=lo, vmax=hi)
    TICKS = {0.0: f"{lo:.3f}", 0.25: f"{lo / 2:.3f}", 0.5: "0",
             0.75: f"{hi / 2:.2f}", 1.0: f"{hi:.2f}"}
else:
    SLIP_CMAP = LinearSegmentedColormap.from_list("slip_dextral", SENSE[2:])
    NORM = Normalize(vmin=0.0, vmax=hi)
    TICKS = {0.0: "0", 0.5: f"{hi / 2:.2f}", 1.0: f"{hi:.2f}"}
KEY = "slip rate (+ dextral)"

pl = pv.Plotter(off_screen=True, shape=(len(VIEWS), len(CASES)),
                window_size=(PANEL * len(CASES), PANEL * len(VIEWS)),
                border=False)
for j, ((title, _f), d) in enumerate(zip(CASES, dumps)):
    for i, ((cx, cy), scale, ztag) in enumerate(VIEWS):
        pl.subplot(i, j)
        pl.set_background("white")
        pvm = pv.UnstructuredGrid(d["cells"], d["celltypes"], d["points"])
        pvm.point_data["logtau"] = d["logtau"]
        pl.add_mesh(pvm, scalars="logtau", cmap="magma", clim=clim,
                    show_edges=False, lighting=False,
                    show_scalar_bar=(i == 0 and j == 0),
                    scalar_bar_args=dict(title="log10 tau_II", n_labels=4,
                                         color="black", vertical=True,
                                         position_x=0.84, position_y=0.06))
        if i > 0:
            pl.add_mesh(pvm.extract_all_edges(), color="white",
                        line_width=0.4, opacity=0.3, lighting=False)
        arr = d["slips"]
        for seg in np.split(arr, np.flatnonzero(np.isnan(arr[:, 0]))):
            seg = seg[~np.isnan(seg[:, 0])]
            if len(seg) < 2:
                continue
            t = seg[:, :2] - seg[:, :2].mean(axis=0)
            _u, _s, vt = np.linalg.svd(t, full_matrices=False)
            seg = seg[np.argsort(t @ vt[0])]
            vals = np.where(np.isfinite(seg[:, 2]), seg[:, 2], 0.0)
            if seg.shape[1] > 3:
                vals = np.where(seg[:, 3] > 0, vals, 0.0)
            line = pv.lines_from_points(np.column_stack(
                [seg[:, :2], np.full(len(seg), 0.004)]))
            line.point_data[KEY] = np.asarray(NORM(vals), dtype=float)
            pl.add_mesh(line, scalars=KEY, cmap=SLIP_CMAP, clim=(0.0, 1.0),
                        line_width=6 if i == 0 else 10, lighting=False,
                        render_lines_as_tubes=True,
                        show_scalar_bar=(i == 0 and j == 1),
                        annotations=TICKS,
                        scalar_bar_args=dict(title=KEY, n_labels=0,
                                             color="black", vertical=True,
                                             position_x=0.84,
                                             position_y=0.45))
        txt = f"{title}, w = {W}" if i == 0 else f"{ztag} — {title}"
        pl.add_text(txt, font_size=13, color="black",
                    position=(18.0, 960.0))
        pl.view_xy()
        pl.camera.parallel_projection = True
        pl.camera.focal_point = (cx, cy, 0.0)
        pl.camera.parallel_scale = scale
img = pl.screenshot(None, return_img=True)
pl.close()

# equal panel size and equal margins: cut the render into its four
# viewports and lay them out on white with one gutter width everywhere
nr, nc = len(VIEWS), len(CASES)
H = nr * PANEL + (nr + 1) * GUTTER
Wd = nc * PANEL + (nc + 1) * GUTTER
canvas = np.full((H, Wd, img.shape[2]), 255, dtype=img.dtype)
for i in range(nr):
    for j in range(nc):
        tile = img[i * PANEL:(i + 1) * PANEL, j * PANEL:(j + 1) * PANEL]
        y0 = GUTTER + i * (PANEL + GUTTER)
        x0 = GUTTER + j * (PANEL + GUTTER)
        canvas[y0:y0 + PANEL, x0:x0 + PANEL] = tile
out = "sf_note_stress_slip.png"
from PIL import Image
Image.fromarray(canvas).save(out)
print(f"wrote {out}  slip range [{lo:.4f}, {hi:.4f}] two-sided {TWO_SIDED}  logtau clim {clim}")
