"""The viscosity-floor figure, from the runs of examples/viscosity_floor.py.

    python plot_viscosity_floor.py

reads, from this directory, viscosity_floor_<cell size>.json for each
resolution, viscosity_floor_<cell size>_from_rest.json where there is one,
and the _fields.npz and _map.npz of the finest run that wrote a map; and
writes ../viscosity_floor.png. The data here were made with
`python viscosity_floor.py -uw_cell_size <c>` for c = 0.1, 0.05, 0.025, and
with `-uw_from_rest 1` added for c = 0.1, 0.05.
"""
import glob
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = pathlib.Path(__file__).parent
every = [json.loads(pathlib.Path(p).read_text()) for p in glob.glob(str(here / "viscosity_floor_*.json"))]
runs = sorted((r for r in every if not r.get("from_rest")), key=lambda r: -r["h"])
rested = {r["h"]: r for r in every if r.get("from_rest")}
mapped = [r for r in runs if (here / f"viscosity_floor_{r['cell_size']:g}_map.npz").exists()][-1]
fields = np.load(here / f"viscosity_floor_{mapped['cell_size']:g}_fields.npz")
sens = np.load(here / f"viscosity_floor_{mapped['cell_size']:g}_map.npz")
colours = dict(zip([r["h"] for r in runs], ["#9ab7d3", "#3d7ab8", "#0b2f5b"][-len(runs):]))

fig = plt.figure(figsize=(7.2, 6.6))
grid = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.5], hspace=0.5, wspace=0.3)


def box(ax, title):
    ax.set_aspect("equal")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 1)
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_yticks([0, 1])
    ax.tick_params(labelsize=7)
    ax.set_title(title, fontsize=8.5, loc="left")


def bar(image, ax, label):
    b = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.015)
    b.set_label(label, fontsize=7.5)
    b.ax.tick_params(labelsize=7)


ax = fig.add_subplot(grid[0, :])
x, y = np.meshgrid(fields["x"], fields["y"])
image = ax.pcolormesh(x, y, np.log10(fields["eta"]), cmap="viridis", vmin=-3, vmax=0, shading="auto")
step = (slice(6, None, 12), slice(10, None, 20))
ax.quiver(x[step], y[step], fields["v"][step + (0,)], fields["v"][step + (1,)],
          color="white", scale=14, width=0.0025, alpha=0.85)
box(ax, rf"(a) effective viscosity and velocity, $\eta_{{\min}} = {float(fields['floor']):g}$")
bar(image, ax, r"$\log_{10}\eta$")

ax = fig.add_subplot(grid[1, :])
density = np.abs(sens["work"])
top = np.log10(density.max())
image = ax.pcolormesh(x, y, np.log10(np.maximum(density, 1e-12)), cmap="magma", vmin=top - 4, vmax=top,
                      shading="auto")
box(ax, rf"(b) where the floor does its work: $\mathrm{{d}}J/\mathrm{{d}}\eta_{{\min}}$ per unit area, "
        rf"rate of work, $\eta_{{\min}} = {float(sens['floor']):g}$")
bar(image, ax, r"$\log_{10}$ density")

ax_s = fig.add_subplot(grid[2, 0])
ax_n = fig.add_subplot(grid[2, 1])
for run in runs:
    colour = colours[run["h"]]
    floor = np.array([r["floor"] for r in run["rows"]])
    ax_s.loglog(floor, np.abs([r["uplift"]["S"] for r in run["rows"]]), "--", color=colour, lw=1.2)
    ax_s.loglog(floor, np.abs([r["work"]["S"] for r in run["rows"]]), "-", color=colour, lw=1.4,
                label=rf"$h = {run['h']:g}$")
    ax_n.semilogx(floor, [r["newton"] for r in run["rows"]], "o-", color=colour, ms=3, lw=1)
    if run["h"] in rested:
        cold = rested[run["h"]]["rows"]
        ax_n.semilogx([r["floor"] for r in cold], [r["newton"] for r in cold], "o--", color=colour,
                      ms=3.5, lw=0.9, mfc="white")
for a in (ax_s, ax_n):
    a.set_xlim(0.6, 0.8e-4)
    a.set_xlabel(r"viscosity floor $\eta_{\min}$", fontsize=8)
    a.tick_params(labelsize=7)
ax_s.set_ylim(1e-8, 1)
ax_s.set_ylabel(r"$|\,\mathrm{d}\ln J / \mathrm{d}\ln\eta_{\min}|$", fontsize=8)
ax_s.set_title("(c) sensitivity of the prediction", fontsize=8.5, loc="left")
ax_s.plot([], [], "k-", lw=1.4, label="rate of work")
ax_s.plot([], [], "k--", lw=1.2, label="uplift")
ax_s.legend(fontsize=7, frameon=False, loc="lower left")
ax_n.set_ylabel("Newton iterations", fontsize=8)
ax_n.set_ylim(bottom=0)
ax_n.set_title("(d) cost of the solve", fontsize=8.5, loc="left")
ax_n.plot([], [], "ko-", ms=3, lw=1, label="from the floor above")
ax_n.plot([], [], "ko--", ms=3.5, lw=0.9, mfc="white", label="from rest")
ax_n.legend(fontsize=7, frameon=False, loc="upper left")

fig.savefig(here.parent / "viscosity_floor.png", dpi=180, bbox_inches="tight")
print("wrote", here.parent / "viscosity_floor.png")
