"""trench-mesh.png for UWTN 2026-022: the solver mesh around the trench of earth_recipe_movie at
four steps, each panel a window on that step's trench (rotated so the trench is at the top),
the base mesh's edges in blue under the solver mesh's in black, the fault trace (state_N.json
"traces": the fault built into that checkpoint's mesh) in red, and a whole-annulus inset
locating the window. The meshes are read from the checkpoints' own topology (geometry/vertices
and viz/topology/cells of annulus.solver_mesh.NNNNN.h5 and of the base annulus.mesh.00000.h5),
so what is drawn is exactly what was saved.

Also measures, per step (written to trench_mesh.json):
  - the solver mesh's cells and vertices against the base's, the base cells the band replaced and
    the cells it put in their place, and the Band label's cells (Band label points that are
    triangles in the checkpoint's celltype label), the F0 / F0Plus / F0Minus face counts;
  - the base mesh's edges that are unchanged in the solver mesh (the same two vertices, at the
    same coordinates to 1e-9, joined by an edge of the solver mesh), everywhere and beyond each
    stated distance from the fault trace. An edge is "beyond d" when both its vertices are
    farther than d from the trace polyline (exact point-to-segment distances). Also the
    largest distance from the trace of a base edge the solver mesh does not keep.

Defaults read ../data next to this script and write trench-mesh.png to the note's figures/
(../../.. from here) and ../trench_mesh.json. The data/ h5 files are not in the repository (see
../README.md); pass -uw_data to the folder that holds them.
h5py, numpy, scipy, matplotlib (the uw3 container's python3):
    python3 trench_mesh.py [-uw_data DIR] [-uw_steps 10,130,460,799] [-uw_out PNG] [-uw_json JSON]
"""
import argparse
import json
import math
import os

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
KM = 2900.0                 # model length unit in km (mantle depth)
MYR = 266497.0              # model time unit in Myr
ap = argparse.ArgumentParser()
ap.add_argument("-uw_data", default=os.path.join(HERE, "..", "data"))
ap.add_argument("-uw_records", default=None, help="default: <uw_data>/records_trimmed.json")
ap.add_argument("-uw_steps", default="10,130,460,799")
ap.add_argument("-uw_why", default="early|half-way through the rollback|the furthest rollback|after the advance, the last step")
ap.add_argument("-uw_far", default="0.02,0.05,0.1")   # stated distances from the trace (model units)
ap.add_argument("-uw_margin", type=float, default=0.045)  # window margin around the four traces (model units)
# the inset turns the annulus so that this model angle (degrees) is at the top: 0, the trench's starting
# position (-uw_theta_trench 0), as in the run's whole-annulus talk renders; 90 draws the model's own frame
ap.add_argument("-uw_inset_up", type=float, default=0.0)
ap.add_argument("-uw_out", default=os.path.join(HERE, "..", "..", "..", "trench-mesh.png"))
ap.add_argument("-uw_json", default=os.path.join(HERE, "..", "trench_mesh.json"))
params = ap.parse_args()
data = os.path.abspath(params.uw_data)
steps = [int(s) for s in params.uw_steps.split(",")]
why = params.uw_why.split("|")
far = [float(d) for d in params.uw_far.split(",")]
out = os.path.abspath(params.uw_out)
records = {r["step"]: r for r in json.load(open(params.uw_records or os.path.join(data, "records_trimmed.json")))}


def read_mesh(path):
    """Vertices, the unique edges (vertex index pairs, sorted), the cells (sorted vertex triples)."""
    with h5py.File(path, "r") as h:
        X = h["geometry/vertices"][:]
        cells = h["viz/topology/cells"][:].astype(np.int64)
    e = np.vstack([cells[:, [0, 1]], cells[:, [1, 2]], cells[:, [2, 0]]])
    e.sort(axis=1)
    return X, np.unique(e, axis=0), np.sort(cells, axis=1)


def label_counts(path):
    """Points of the Band label that are cells (triangles), and the F0 / F0Plus / F0Minus label sizes."""
    with h5py.File(path, "r") as h:
        tri = h["labels/celltype/3/indices"][:, 0]

        def points(name):
            if f"labels/{name}" not in h:
                return np.zeros(0, dtype=np.int64)
            g = h[f"labels/{name}"]
            return np.concatenate([g[v]["indices"][:, 0] for v in g])
        band = points("Band")
        return {"band_points": int(len(band)), "band_cells": int(np.isin(band, tri).sum()),
                "F0": int(len(points("F0"))), "F0Plus": int(len(points("F0Plus"))),
                "F0Minus": int(len(points("F0Minus")))}


def dist_to_polyline(P, line):
    """Exact distance of each point in P to the polyline (segments of `line`)."""
    a, b = line[:-1], line[1:]
    ab = b - a
    best = np.full(len(P), np.inf)
    for k in range(len(a)):
        t = np.clip(((P - a[k]) @ ab[k]) / max(ab[k] @ ab[k], 1e-300), 0.0, 1.0)
        best = np.minimum(best, np.hypot(*(P - (a[k] + t[:, None] * ab[k])).T))
    return best


def rotate(xy, theta):
    """Rotate so the angle theta points up (+y)."""
    a = math.pi / 2 - theta
    c, s = math.cos(a), math.sin(a)
    return np.asarray(xy) @ np.array([[c, s], [-s, c]])


def code(pairs, n):
    return pairs[:, 0].astype(np.int64) * n + pairs[:, 1]


bX, bE, bC = read_mesh(os.path.join(data, "annulus.mesh.00000.h5"))
nb = len(bX)
b_tree = cKDTree(bX)
r = np.hypot(bX[:, 0], bX[:, 1])
r_o, r_i = float(r.max()), float(r.min())

states = {n: json.load(open(os.path.join(data, f"state_{n:05d}.json"))) for n in steps}
# one window size for every panel (the same scale), from the four traces in their rotated frames
rot = {n: rotate(np.asarray(states[n]["traces"][0]), float(states[n]["faults"][0]["theta"])) for n in steps}
allx = np.concatenate([rot[n][:, 0] for n in steps])
ally = np.concatenate([rot[n][:, 1] for n in steps])
lo = np.array([min(allx.min(), 0.0) - params.uw_margin, ally.min() - params.uw_margin])
hi = np.array([max(allx.max(), 0.0) + params.uw_margin, r_o + 0.012])

aspect = (hi[0] - lo[0]) / (hi[1] - lo[1])
panel_w = 5.9
fig_w, fig_h = 2 * panel_w + 0.4, 2 * (panel_w / aspect + 0.75) + 0.1
fig, axes = plt.subplots(2, 2, figsize=(fig_w, fig_h))
# explicit spacing (tight_layout does not see the inset axes): 0.75 in above each row for its title
fig.subplots_adjust(left=0.012, right=0.988, bottom=0.008, top=1 - 0.6 / fig_h, wspace=0.03,
                    hspace=0.75 / (panel_w / aspect))
stats = []
for i, (ax, n) in enumerate(zip(axes.ravel(), steps)):
    state, rec = states[n], records[n]
    fault = state["faults"][0]
    theta = float(fault["theta"])
    path = os.path.join(data, f"annulus.solver_mesh.{n:05d}.h5")
    sX, sE, sC = read_mesh(path)
    trace = np.asarray(state["traces"][0])
    # each solver vertex's base vertex (-1: a vertex the band made)
    d, m = b_tree.query(sX)
    m[d > 1e-9] = -1
    # solver edges and cells as base-vertex pairs / triples (only those with every vertex a base vertex)
    se = m[sE]
    se_ok = (se >= 0).all(axis=1)
    se_codes = code(np.sort(se[se_ok], axis=1), nb)
    sc = m[sC]
    sc_ok = (sc >= 0).all(axis=1)
    sc_b = np.sort(sc[sc_ok], axis=1)
    sc_codes = (sc_b[:, 0] * nb + sc_b[:, 1]) * nb + sc_b[:, 2]
    b_codes = code(bE, nb)
    kept = np.isin(b_codes, se_codes)                      # base edges the solver mesh keeps
    bc_codes = (bC[:, 0] * nb + bC[:, 1]) * nb + bC[:, 2]
    cells_kept = int(np.isin(bc_codes, sc_codes).sum())    # base cells the solver mesh keeps
    s_edge_in_base = np.zeros(len(sE), bool)
    s_edge_in_base[np.flatnonzero(se_ok)] = np.isin(se_codes, b_codes)
    dv = dist_to_polyline(bX, trace)
    de = np.minimum(dv[bE[:, 0]], dv[bE[:, 1]])           # an edge's distance: its nearer vertex's
    labels = label_counts(path)
    mesh = rec["solver"]["mesh"] or {}
    lc = mesh.get("levels_cells") or []
    s = {"step": n, "why": why[i] if i < len(why) else "", "t": rec["t"], "t_Myr": rec["t"] * MYR,
         "trench_deg_records": math.degrees(rec["theta_trench"]), "trench_deg_state": math.degrees(theta),
         "dip_deg": rec["dip"], "kind": rec["solver"]["kind"],
         "base_cells": int(len(bC)), "solver_cells": int(len(sC)), "added_cells": int(len(sC) - len(bC)),
         "records_levels_cells": lc, "records_band_cells_per_rank_sum": sum(mesh.get("band_cells_per_rank") or []),
         "records_band_ranks": mesh.get("band_ranks"),
         "base_cells_replaced": int(len(bC) - cells_kept), "new_cells": int(len(sC) - cells_kept),
         **labels,
         "base_vertices": int(nb), "solver_vertices": int(len(sX)), "new_vertices": int((m < 0).sum()),
         "base_edges": int(len(bE)), "base_edges_kept": int(kept.sum()), "base_edges_changed": int((~kept).sum()),
         "solver_edges": int(len(sE)), "solver_edges_not_in_base": int((~s_edge_in_base).sum()),
         "max_dist_changed_base_edge": float(de[~kept].max()) if (~kept).any() else 0.0,
         "max_dist_changed_base_edge_km": float(de[~kept].max() * KM) if (~kept).any() else 0.0,
         "beyond": {f"{dd:g}": {"km": dd * KM, "base_edges": int((de > dd).sum()),
                                "kept": int(kept[de > dd].sum()),
                                "share_kept": float(kept[de > dd].mean())} for dd in far}}
    stats.append(s)

    # the window, in the rotated frame: the trench at (0, r_o)
    def inside(X, E):
        seg = rotate(X, theta)[E]
        keep = ((seg >= lo - 0.03) & (seg <= hi + 0.03)).all(axis=2).any(axis=1)
        return seg[keep]

    ax.add_collection(LineCollection(inside(bX, bE), colors="#85c1e9", linewidths=1.3, zorder=1))
    ax.add_collection(LineCollection(inside(sX, sE), colors="black", linewidths=0.35, zorder=2))
    tr = rotate(trace, theta)
    ax.plot(tr[:, 0], tr[:, 1], color="#c0392b", lw=2.0, zorder=3, solid_capstyle="round")
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"({'abcd'[i]}) step {n}, {s['t_Myr']:,.0f} Myr, {s['why']}\n"
                 f"trench at {s['trench_deg_records']:.1f}°, fault dip {s['dip_deg']:.0f}°; "
                 f"the band adds {s['added_cells']} cells to the base's {s['base_cells']:,}", fontsize=9.5)
    # a 200 km scale bar, upper left (above the band's far side in every panel)
    bar = 200.0 / KM
    x0, y0 = lo[0] + 0.05 * (hi[0] - lo[0]), lo[1] + 0.70 * (hi[1] - lo[1])
    ax.plot([x0, x0 + bar], [y0, y0], color="black", lw=2.2, zorder=6, solid_capstyle="butt")
    ax.text(x0 + bar / 2, y0 + 0.006, "200 km", ha="center", va="bottom", fontsize=8.5, zorder=6,
            bbox=dict(fc="white", ec="none", pad=1.0, alpha=0.9))
    # the whole-annulus inset with the window drawn, bottom right
    h_in = 0.36
    ins = ax.inset_axes([1.0 - h_in / aspect - 0.005, 0.005, h_in / aspect, h_in], zorder=5)
    ins.add_patch(plt.Rectangle((-r_o * 1.06, -r_o * 1.06), 2.12 * r_o, 2.12 * r_o, fc="white", ec="#888888", lw=0.6))
    t = np.linspace(0, 2 * np.pi, 361)
    ins.fill(np.r_[r_o * np.cos(t), r_i * np.cos(t[::-1])], np.r_[r_o * np.sin(t), r_i * np.sin(t[::-1])],
             color="#e5e5e5", lw=0)
    for radius in (r_o, r_i):
        ins.plot(radius * np.cos(t), radius * np.sin(t), color="#888888", lw=0.5)
    box = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])
    # back to the model frame (by theta - pi/2), then turned so that -uw_inset_up is at the top
    ins.add_patch(Polygon(rotate(box, math.pi / 2 - theta + math.radians(params.uw_inset_up)), fill=False,
                          ec="#c0392b", lw=1.2))
    ins.set_xlim(-r_o * 1.06, r_o * 1.06)
    ins.set_ylim(-r_o * 1.06, r_o * 1.06)
    ins.set_aspect("equal")
    ins.axis("off")
os.makedirs(os.path.dirname(out), exist_ok=True)
fig.savefig(out, dpi=200, facecolor="white")
summary = {"run": "earth_recipe_movie", "steps": stats,
           "window": {"x": [float(lo[0]), float(hi[0])], "y": [float(lo[1]), float(hi[1])],
                      "width_km": float((hi[0] - lo[0]) * KM), "height_km": float((hi[1] - lo[1]) * KM)},
           "units": {"length_km": KM, "time_Myr": MYR}}
with open(params.uw_json, "w") as f:
    json.dump(summary, f, indent=1)
for s in stats:
    print(json.dumps({k: v for k, v in s.items() if k not in ("records_levels_cells",)}))
print("->", out, params.uw_json)
