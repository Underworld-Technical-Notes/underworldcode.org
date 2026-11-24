"""trench-cost.png for UWTN 2026-022, earth_recipe_movie, from the run's per-step records
(record["solver"]["wall"], seconds, np 26):
  (a) wall time per step by phase, stacked: build (the solver mesh), transfer (the fields onto
      it), to_base (the solution back to the base mesh), Stokes, and the rest of the step
      (energy_strain + swarm + detection + the unattributed remainder). The checkpoint write is
      NOT included: record wall "step" is timed before the checkpoint, which is its own phase.
  (b) the three phases the separate solver mesh brings (build, transfer, to_base) per step.
  (c) the peak slip rate on the fault per step, slip_max, in model velocity units converted to
      cm/yr (1 model unit = 1.08819e-3 cm/yr: kappa 1e-6 m2/s over 2900 km).
  (d) the band's cells (on one rank of 26 at every build: band_cells_per_rank, band_ranks 1) and
      the cells the solver mesh adds to the base's finest level (levels_cells[-1] - [-2]), at every
      step whose solver mesh was built (the others keep the step before's mesh; no record).
Also writes trench_cost.json: per-phase mean / median / min / max and share of the step, with
and without the checkpoint, and the same for the steps that rebuilt and those that did not.
Defaults read ../data/records_trimmed.json and write trench-cost.png to the note's figures/
(../../.. from here) and ../trench_cost.json.
numpy and matplotlib:
    python3 trench_cost.py [-uw_records JSON] [-uw_out PNG] [-uw_json JSON]
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CM_YR = 1.08819e-3          # cm/yr per model velocity unit
MYR = 266497.0              # Myr per model time unit
ap = argparse.ArgumentParser()
ap.add_argument("-uw_records", default=os.path.join(HERE, "..", "data", "records_trimmed.json"))
ap.add_argument("-uw_out", default=os.path.join(HERE, "..", "..", "..", "trench-cost.png"))
ap.add_argument("-uw_json", default=os.path.join(HERE, "..", "trench_cost.json"))
params = ap.parse_args()
records = json.load(open(params.uw_records))
steps = np.array([r["step"] for r in records])
t_myr = np.array([r["t"] for r in records]) * MYR
PHASES = ("build", "transfer", "stokes", "to_base", "energy_strain", "swarm", "detection", "checkpoint", "step")
wall = {k: np.array([r["solver"]["wall"][k] for r in records]) for k in PHASES}
wall["other"] = wall["step"] - sum(wall[k] for k in ("build", "transfer", "stokes", "to_base", "energy_strain",
                                                     "swarm", "detection"))
wall["rest"] = wall["energy_strain"] + wall["swarm"] + wall["detection"] + wall["other"]
wall["step_with_checkpoint"] = wall["step"] + wall["checkpoint"]
kind = np.array([r["solver"]["kind"] for r in records])
built = kind != "ordinary"          # init_first and the rebuild_* steps: the solver mesh was (re)built

# the documented categorical order (blue, orange, aqua, yellow) and a neutral grey for the folded rest
COL = {"stokes": "#2a78d6", "build": "#eb6834", "transfer": "#1baf7a", "to_base": "#eda100", "rest": "#a3a29c"}
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": "#888888", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": "#e6e6e3",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
fig, (a, b, c, d) = plt.subplots(4, 1, figsize=(10, 11.2), sharex=True,
                                 gridspec_kw={"height_ratios": [3.2, 1.8, 1.8, 1.8]})

# (a) stacked: the solver-mesh phases at the bottom, the rest, Stokes on top
order = (("build", "building the add-on"), ("transfer", "fields onto it"),
         ("to_base", "solution back to the base"), ("rest", "rest of the step"), ("stokes", "Stokes solve"))
bottom = np.zeros(len(steps))
for key, label in order:
    a.fill_between(steps, bottom, bottom + wall[key], step="mid", color=COL[key], lw=0, label=label)
    bottom = bottom + wall[key]
a.set_ylabel("wall time per step (s)")
a.set_ylim(0, 1.16 * bottom.max())
a.legend(ncol=5, fontsize=8.3, loc="upper left", frameon=False, bbox_to_anchor=(0.0, 1.0))
a.set_title("(a) wall time per step by phase, without the checkpoint write", fontsize=9.5, loc="left")
top = a.secondary_xaxis("top", functions=(lambda s: np.interp(s, steps, t_myr), lambda m: np.interp(m, t_myr, steps)))
top.set_xlabel("model time (Myr)")
top.set_xticks([0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100])

# (b) the solver mesh's own phases, every step (no line: the 40 steps that kept the mesh show as the low points)
for key, label in (("build", "building the add-on"), ("transfer", "fields onto it"), ("to_base", "solution back")):
    b.plot(steps, wall[key], ".", ms=2.6, color=COL[key], label=label)
b.set_ylabel("wall time (s)")
b.set_ylim(-0.2, 6.8)
b.legend(ncol=3, fontsize=8.3, loc="upper right", frameon=False, markerscale=3)
b.set_title("(b) the three phases that rebuilding the add-on brings", fontsize=9.5, loc="left")

# (c) slip_max in cm/yr (step 0 has no fault in its mesh)
slip = np.array([r["slip_max"] for r in records]) * CM_YR
c.plot(steps[1:], slip[1:], "-", color="#2a78d6", lw=1.0)
c.set_ylabel("peak slip rate (cm/yr)")
c.set_ylim(0, None)
c.set_title("(c) peak slip rate on the fault", fontsize=9.5, loc="left")

# (d) the band's cells and the cells the solver mesh adds, at every build
bs = [(r["step"], sum(r["solver"]["mesh"]["band_cells_per_rank"]), r["solver"]["mesh"]["band_ranks"],
       r["solver"]["mesh"]["levels_cells"][-1] - r["solver"]["mesh"]["levels_cells"][-2])
      for r in records if r["solver"].get("mesh") and r["solver"]["mesh"].get("band_cells_per_rank")
      and len(r["solver"]["mesh"]["levels_cells"]) > 6]
bstep, bcells, branks, badd = (np.array(v) for v in zip(*bs))
d.plot(bstep, badd, ".", ms=2.6, color="#6250d6", label="cells the add-on adds to the base's finest level")
d.plot(bstep, bcells, ".", ms=2.6, color="#e87ba4", label="cells in the band")
d.set_ylabel("cells")
d.set_ylim(0, max(badd.max(), bcells.max()) * 1.25)
d.legend(ncol=2, fontsize=8.3, loc="upper left", frameon=False, markerscale=3)
d.set_title("(d) the band's size at each build", fontsize=9.5, loc="left")
d.set_xlabel("step")
d.set_xlim(-5, steps.max() + 5)
fig.tight_layout()
os.makedirs(os.path.dirname(os.path.abspath(params.uw_out)), exist_ok=True)
fig.savefig(params.uw_out, dpi=200, facecolor="white")


def stats(v):
    return {"mean": round(float(v.mean()), 3), "median": round(float(np.median(v)), 3),
            "min": round(float(v.min()), 3), "max": round(float(v.max()), 3)}


def table(sel):
    out = {}
    for k in ("build", "transfer", "stokes", "to_base", "energy_strain", "swarm", "detection", "other",
              "checkpoint", "step", "step_with_checkpoint"):
        v = wall[k][sel]
        out[k] = {**stats(v), "share_of_step": round(float(v.mean() / wall["step"][sel].mean()), 4),
                  "share_of_step_with_checkpoint": round(float(v.mean() / wall["step_with_checkpoint"][sel].mean()), 4)}
    out["steps"] = int(sel.sum())
    return out


summary = {"note": "seconds per step, np 26; 'step' excludes the checkpoint write, 'step_with_checkpoint' adds it; "
                   "'other' = step minus the seven timed phases before the checkpoint",
           "all_steps": table(np.ones(len(steps), bool)),
           "steps_built": table(built), "steps_not_built": table(~built),
           "kinds": {k: int((kind == k).sum()) for k in sorted(set(kind))},
           "total_hours": {"step": round(float(wall["step"].sum() / 3600), 2),
                           "checkpoint": round(float(wall["checkpoint"].sum() / 3600), 2),
                           "with_checkpoint": round(float(wall["step_with_checkpoint"].sum() / 3600), 2)},
           "slip_max_cm_yr_steps_1_on": {**stats(slip[1:]), "step_of_min": int(steps[1:][slip[1:].argmin()]),
                                         "step_of_max": int(steps[1:][slip[1:].argmax()])},
           "band_cells_at_builds": {**stats(bcells), "band_ranks": sorted(set(int(x) for x in branks)), "builds": len(bs)},
           "cells_added_at_builds": stats(badd)}
with open(params.uw_json, "w") as f:
    json.dump(summary, f, indent=1)
print(json.dumps(summary, indent=1))
print("->", params.uw_out)
