"""trench-cost-window.png for UWTN 2026-022, earth_recipe_movie: the solver's cost over steps 2 to 141,
every one of which rebuilt the faulted mesh around the fitted fault. The window stops before step 142,
the first step that kept the previous mesh (data/no_rebuild_steps.txt); steps 0 and 1 are the cold
start and the first faulted mesh.
  (a) Stokes wall time per nonlinear iteration (record["solver"]["wall"]["stokes"] / nonlinear_its).
  (b) velocity iterations of each linear solve inside the nonlinear loop (record["solver"]["vel_its"]),
      every solve as a point, with the step's mean.
  (c) nonlinear iterations per step (record["solver"]["nonlinear_its"]).
Also writes trench_cost_window.json with the numbers the note quotes. Defaults read
../data/records_trimmed.json and write the PNG to the note's figures/ (../../.. from here).
numpy and matplotlib:
    python3 trench_cost_window.py [-uw_records JSON] [-uw_out PNG] [-uw_json JSON] [-uw_first N] [-uw_last N]
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("-uw_records", default=os.path.join(HERE, "..", "data", "records_trimmed.json"))
ap.add_argument("-uw_out", default=os.path.join(HERE, "..", "..", "..", "trench-cost-window.png"))
ap.add_argument("-uw_json", default=os.path.join(HERE, "..", "trench_cost_window.json"))
ap.add_argument("-uw_first", type=int, default=2)
ap.add_argument("-uw_last", type=int, default=141)
params = ap.parse_args()

records = [r for r in json.load(open(params.uw_records)) if params.uw_first <= r["step"] <= params.uw_last]
kinds = sorted({r["solver"]["kind"] for r in records})
assert kinds == ["rebuild_same_set"], kinds   # the window holds only steps that rebuilt the mesh
steps = np.array([r["step"] for r in records])
stokes = np.array([r["solver"]["wall"]["stokes"] for r in records])
nl = np.array([r["solver"]["nonlinear_its"] for r in records])
vel = [np.array(r["solver"]["vel_its"]) for r in records]
vel_all = np.concatenate(vel)
vel_mean = np.array([v.mean() for v in vel])
per_nl = stokes / nl
per_vel = stokes / np.array([v.sum() for v in vel])

INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": "#888888", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": "#e6e6e3",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
fig, (a, b, c) = plt.subplots(3, 1, figsize=(10, 7.6), sharex=True, gridspec_kw={"height_ratios": [1, 1, 1]})

a.plot(steps, per_nl, "o-", ms=2.8, lw=0.8, color="#2a78d6")
a.axhline(per_nl.mean(), color=MUTED, lw=0.8, ls="--")
a.set_ylim(0, 1.35 * per_nl.max())
a.set_ylabel("seconds")
a.set_title("(a) Stokes wall time per nonlinear iteration (mean %.1f s, dashed)" % per_nl.mean(),
            fontsize=9.5, loc="left")

rng = np.random.default_rng(0)
xs = np.concatenate([np.full(len(v), s) for s, v in zip(steps, vel)]) + rng.uniform(-0.25, 0.25, len(vel_all))
b.plot(xs, vel_all, ".", ms=2.4, color="#1baf7a", alpha=0.55, label="each linear solve")
b.plot(steps, vel_mean, "-", lw=1.0, color="#0d6e4b", label="mean over the step")
b.set_ylim(0, vel_all.max() + 3)
b.set_ylabel("velocity iterations")
b.yaxis.set_major_locator(MaxNLocator(integer=True, steps=[1, 2, 5, 10]))
b.legend(ncol=2, fontsize=8.3, loc="upper right", frameon=False, markerscale=2.5)
b.set_title("(b) velocity iterations per linear solve (mean %.1f, %d solves)" % (vel_all.mean(), len(vel_all)),
            fontsize=9.5, loc="left")

c.bar(steps, nl, width=0.8, color="#eb6834")
c.set_ylim(0, nl.max() + 3)
c.set_ylabel("iterations")
c.yaxis.set_major_locator(MaxNLocator(integer=True, steps=[1, 2, 5, 10]))
c.set_title("(c) nonlinear iterations per step", fontsize=9.5, loc="left")
c.set_xlabel("step")
c.set_xlim(steps.min() - 1, steps.max() + 1)
fig.tight_layout()
os.makedirs(os.path.dirname(os.path.abspath(params.uw_out)), exist_ok=True)
fig.savefig(params.uw_out, dpi=200, facecolor="white")


def stats(v):
    return {"mean": round(float(v.mean()), 3), "std": round(float(v.std()), 3), "min": round(float(v.min()), 3),
            "max": round(float(v.max()), 3)}


summary = {"note": "earth_recipe_movie, np 26, steps %d to %d (all rebuilt the faulted mesh)"
                   % (params.uw_first, params.uw_last),
           "steps": len(records),
           "stokes_s_per_step": stats(stokes),
           "stokes_s_per_nonlinear_iteration": stats(per_nl),
           "stokes_s_per_velocity_iteration": stats(per_vel),
           "nonlinear_iterations_per_step": stats(nl),
           "velocity_iterations_per_linear_solve": {**stats(vel_all), "solves": int(len(vel_all)),
                                                    "p5_p95": [float(x) for x in np.percentile(vel_all, [5, 95])]},
           "corr_stokes_time_vs_nonlinear_iterations": round(float(np.corrcoef(stokes, nl)[0, 1]), 3)}
with open(params.uw_json, "w") as f:
    json.dump(summary, f, indent=1)
print(json.dumps(summary, indent=1))
print("->", params.uw_out)
