"""The viscosity-floor figure, from the runs of examples/viscosity_floor.py.

    python plot_viscosity_floor.py

reads viscosity_floor_<cell size>.json and the finest run's _fields.npz from
this directory, and writes ../viscosity_floor.png. The data here were made
with `python viscosity_floor.py -uw_cell_size <c>` for c = 0.1, 0.05, 0.025.
"""
import glob
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = pathlib.Path(__file__).parent
runs = sorted((json.loads(pathlib.Path(p).read_text()) for p in glob.glob(str(here / "viscosity_floor_*.json"))),
              key=lambda r: -r["h"])
finest = runs[-1]
fields = np.load(here / f"viscosity_floor_{finest['cell_size']:g}_fields.npz")
colours = ["#9ab7d3", "#3d7ab8", "#0b2f5b"][-len(runs):]

fig = plt.figure(figsize=(7.2, 5.4))
grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.35], hspace=0.42, wspace=0.3)

ax = fig.add_subplot(grid[0, :])
x, y = np.meshgrid(fields["x"], fields["y"])
image = ax.pcolormesh(x, y, np.log10(fields["eta"]), cmap="viridis", vmin=-3, vmax=0, shading="auto")
step = (slice(6, None, 12), slice(10, None, 20))
ax.quiver(x[step], y[step], fields["v"][step + (0,)], fields["v"][step + (1,)],
          color="white", scale=14, width=0.0025, alpha=0.85)
ax.set_aspect("equal")
ax.set_xlim(0, 4)
ax.set_ylim(0, 1)
ax.set_xticks([0, 1, 2, 3, 4])
ax.set_yticks([0, 1])
ax.set_title(rf"effective viscosity at $\eta_{{\min}} = {float(fields['floor']):g}$, $h = {finest['h']:g}$",
             fontsize=9)
bar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.015)
bar.set_label(r"$\log_{10}\eta$", fontsize=8)
bar.ax.tick_params(labelsize=7)
ax.tick_params(labelsize=7)

ax_s = fig.add_subplot(grid[1, 0])
ax_n = fig.add_subplot(grid[1, 1])
for run, colour in zip(runs, colours):
    floor = np.array([r["floor"] for r in run["rows"]])
    work = np.abs([r["work"]["S"] for r in run["rows"]])
    uplift = np.abs([r["uplift"]["S"] for r in run["rows"]])
    label = rf"$h = {run['h']:g}$"
    ax_s.loglog(floor, uplift, "--", color=colour, lw=1.2)
    ax_s.loglog(floor, work, "-", color=colour, lw=1.4, label=label)
    ax_n.semilogx(floor, [r["newton"] for r in run["rows"]], "o-", color=colour, ms=3, lw=1, label=label)
for a in (ax_s, ax_n):
    a.set_xlim(1.4e-4 / 1.4 * 0.9, 0.6)
    a.invert_xaxis()
    a.set_xlabel(r"viscosity floor $\eta_{\min}$", fontsize=8)
    a.tick_params(labelsize=7)
ax_s.set_ylim(1e-8, 1)
ax_s.set_ylabel(r"$|\,\mathrm{d}\ln J / \mathrm{d}\ln\eta_{\min}|$", fontsize=8)
ax_s.plot([], [], "k-", lw=1.4, label="rate of work")
ax_s.plot([], [], "k--", lw=1.2, label="uplift")
ax_s.legend(fontsize=7, frameon=False, loc="lower left")
ax_n.set_ylabel("Newton iterations, warm-started", fontsize=8)
ax_n.set_ylim(bottom=0)

fig.savefig(here.parent / "viscosity_floor.png", dpi=180, bbox_inches="tight")
print("wrote", here.parent / "viscosity_floor.png")
