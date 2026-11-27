"""run_summary.json for UWTN 2026-022: the numbers the README quotes for earth_recipe_movie, from
this folder's data/ only (records_trimmed.json, run_info.json, no_rebuild_steps.txt):
the run's identity and settings, the step kinds, the solver mesh's own phases per step (build,
transfer, to_base), the nonlinear and linear iteration counts and the KSP iteration-cap hits,
the trench's motion and the peak slip rate. Plain python3 (no numpy needed):
    python3 run_summary.py [-uw_data DIR] [-uw_json JSON]

KSP caps (underworld3 80d3ebe9, src/underworld3/utilities/rotated_bc.py, the rotated free-slip
solve this run uses): outer FGMRES ksp_max_it 300, pressure (Schur) fieldsplit_pres_ksp_max_it 200,
velocity fieldsplit_vel_ksp_max_it 200. The records hold, per nonlinear iteration, the outer
count (ksp_its) and the velocity and pressure sub-KSP counts at their LAST application in that
iteration (vel_its, pres_its); a cap hit is a count at or above its cap.
"""
import argparse
import json
import math
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
KM, MYR, CM_YR = 2900.0, 266497.0, 1.08819e-3
R_O = 2.2222                 # outer radius (model units; the run log: "annulus r_o 2.2222 r_i 1.2222")
CAPS = {"outer": 300, "vel": 200, "pres": 200}
ap = argparse.ArgumentParser()
ap.add_argument("-uw_data", default=os.path.join(HERE, "..", "data"))
ap.add_argument("-uw_json", default=os.path.join(HERE, "..", "run_summary.json"))
params = ap.parse_args()
records = json.load(open(os.path.join(params.uw_data, "records_trimmed.json")))
starts = json.load(open(os.path.join(params.uw_data, "run_info.json")))
starts = starts if isinstance(starts, list) else [starts]
info, p = starts[-1], starts[-1]["params"]


def stats(v):
    v = list(v)
    def g(x):
        return float(f"{x:.5g}")
    return {"n": len(v), "mean": g(st.mean(v)), "median": g(st.median(v)), "min": g(min(v)), "max": g(max(v))}


S = float(p["uw_spacing"]) or float(p["uw_cell"]) / 2 ** int(p["uw_refinement"])
W = 2.0 * S                  # the band width the driver places on the finest level (annulus_faults.py: W = 2 S)
h_base = float(p["uw_cell"]) / 2 ** int(p["uw_refinement"])
kind = [r["solver"]["kind"] for r in records]
addon = [r for r in records if r["solver"]["kind"].startswith("rebuild")]     # steps that built a faulted mesh
kept = [r for r in records if r["solver"]["kind"] == "ordinary"]             # steps that kept the step before's
reasons = {}
for line in open(os.path.join(params.uw_data, "no_rebuild_steps.txt")):
    if line.startswith("#") or not line.strip():
        continue
    why = line.split("\t", 1)[1]
    key = ("the fit found no slab top reaching the cap; the fault kept its place" if "keeps its place" in why else
           "placement refused (the fault touches the domain boundary); the previous fault kept" if "placement" in why
           else why.strip())
    reasons[key] = reasons.get(key, 0) + 1
sol = [r["solver"] for r in records]
outer = [x for s in sol for x in s["ksp_its"]]
vel = [x for s in sol for x in s["vel_its"]]
pres = [x for s in sol for x in s["pres_its"]]
theta = [math.degrees(r["theta_trench"]) for r in records]
i_min = min(range(len(theta)), key=theta.__getitem__)
km_per_deg = R_O * KM * math.pi / 180
slip = [r["slip_max"] * CM_YR for r in records[1:]]
summary = {
    "run": {"name": "earth_recipe_movie", "slurm_job": info.get("slurm_job"), "starts": len(starts),
            "restart_from": [s.get("restart_from") for s in starts], "started": info.get("started"),
            "nodes": info.get("nodes"), "mpi_ranks": info.get("mpi_ranks"), "ranks_per_node": info.get("ranks_per_node"),
            "driver_commit": info.get("driver_commit"), "uw3_commit_recorded": info.get("uw3_commit"),
            "uw3_path": info.get("uw3_path"), "container": info.get("container"), "petsc": info.get("petsc"),
            "driver": info.get("argv", [None])[0]},
    "steps": {"first": records[0]["step"], "last": records[-1]["step"], "count": len(records),
              "t_first": records[0]["t"], "t_last": records[-1]["t"],
              "Myr_first": round(records[0]["t"] * MYR, 1), "Myr_last": round(records[-1]["t"] * MYR, 1),
              "dt_Myr": stats(r["dt"] * MYR for r in records)},
    "settings": {k: p.get(k) for k in ("uw_chain", "uw_rebuild_cells", "uw_detect_every", "uw_detect_start",
                                        "uw_spacing", "uw_cell", "uw_refinement", "uw_band_widen", "uw_split_inset",
                                        "uw_split_inset_along", "uw_tol", "uw_pres_rtol", "uw_pres_rtol_cold",
                                        "uw_vel_rtol", "uw_newton_switch", "uw_warm_newton_switch",
                                        "uw_rebuild_newton_switch", "uw_picard", "uw_retry_keep",
                                        "uw_fault_realisation", "uw_fault_seams", "uw_fault_depth_max",
                                        "uw_ckpt_every", "uw_steps")},
    "derived": {"base_cell": h_base, "base_cell_km": h_base * KM, "rung_spacing_S": S, "rung_spacing_km": S * KM,
                "band_width_W_2S": W, "band_width_km": W * KM,
                "split_inset_km_along_fault": float(p["uw_split_inset"]) * S * KM,
                "effective": info.get("effective")},
    "kinds": {k: kind.count(k) for k in sorted(set(kind))},
    "no_rebuild_reasons": reasons,
    "solver_mesh_phases_s": {
        "steps_that_built_a_faulted_mesh": {k: stats(r["solver"]["wall"][k] for r in addon)
                                            for k in ("build", "transfer", "to_base")},
        "steps_that_kept_the_mesh": {k: stats(r["solver"]["wall"][k] for r in kept)
                                     for k in ("build", "transfer", "to_base")},
        "all_steps": {k: stats(r["solver"]["wall"][k] for r in records) for k in ("build", "transfer", "to_base")}},
    "levels_cells_at_builds": sorted({tuple(r["solver"]["mesh"]["levels_cells"][:-1]) for r in addon}),
    "iterations": {
        "converged_steps": sum(1 for s in sol if s["converged"]), "cold_starts": sum(1 for s in sol if s["start"] == "cold"),
        "nonlinear_total": sum(s["nonlinear_its"] for s in sol), "nonlinear_per_step": stats(s["nonlinear_its"] for s in sol),
        "picard_total": sum(s["picard_its"] for s in sol), "picard_per_step": stats(s["picard_its"] for s in sol),
        "newton_total": sum(s["newton_its"] for s in sol), "newton_per_step": stats(s["newton_its"] for s in sol),
        "line_search_cutbacks_total": sum(s["line_search_cutbacks"] for s in sol),
        "rel_final": stats(s["rel_final"] for s in sol)},
    "ksp": {"caps": CAPS, "per_nonlinear_iteration": len(outer),
            "outer": stats(outer), "vel_last_application": stats(vel), "pres_last_application": stats(pres),
            "cap_hits": {"outer": sum(1 for x in outer if x >= CAPS["outer"]),
                         "vel": sum(1 for x in vel if x >= CAPS["vel"]),
                         "pres": sum(1 for x in pres if x >= CAPS["pres"])},
            "pres_rtol_read_back": {str(k): sum(1 for s in sol if round(s["pres_rtol"], 4) == k)
                                    for k in sorted({round(s["pres_rtol"], 4) for s in sol})}},
    "trench": {"deg_first": round(theta[0], 3), "deg_min": round(theta[i_min], 3), "step_min": records[i_min]["step"],
               "Myr_min": round(records[i_min]["t"] * MYR, 1), "deg_last": round(theta[-1], 3),
               "rollback_deg": round(theta[0] - theta[i_min], 3),
               "rollback_km": round((theta[0] - theta[i_min]) * km_per_deg, 1),
               "advance_deg": round(theta[-1] - theta[i_min], 3),
               "advance_km": round((theta[-1] - theta[i_min]) * km_per_deg, 1),
               "km_per_deg_at_surface": round(km_per_deg, 2), "r_o": R_O},
    "slip_max_cm_yr_steps_1_on": {**stats(slip), "step_of_min": 1 + slip.index(min(slip)),
                                  "step_of_max": 1 + slip.index(max(slip)), "step_799": round(slip[-1], 3)},
}
with open(params.uw_json, "w") as f:
    json.dump(summary, f, indent=1, default=str)
print(json.dumps({k: v for k, v in summary.items() if k != "derived"}, indent=1, default=str))
print("->", params.uw_json)
