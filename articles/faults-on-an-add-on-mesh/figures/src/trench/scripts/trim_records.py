"""data/records_trimmed.json and data/no_rebuild_steps.txt for UWTN 2026-022 from the run
earth_recipe_movie: only the per-step fields that trench_cost.py, trench_mesh.py and
run_summary.py read, so the figures and the README numbers regenerate from this folder alone.
The steps whose solver mesh was not rebuilt (record solver.kind "ordinary") are listed with
the rank-0 log line that says why. Plain python3 (no numpy):
    python3 trim_records.py <run dir> <data dir>
"""
import json
import os
import re
import sys

run, out = sys.argv[1], sys.argv[2]
records = json.load(open(os.path.join(run, "records.json")))
TOP = ("step", "t", "dt", "theta_trench", "dip", "fault_depth", "slip_max", "converged", "n_built")
SOLVER = ("kind", "start", "converged", "nonlinear_its", "picard_its", "newton_its", "line_search_cutbacks",
          "rel_final", "pres_rtol", "ksp_its", "vel_its", "pres_its", "wall")
MESH = ("levels_cells", "band_cells_per_rank", "band_ranks", "width", "realisation", "division")
trimmed = []
for r in records:
    s = r["solver"]
    rec = {k: r[k] for k in TOP}
    rec["solver"] = {k: s[k] for k in SOLVER}
    mesh = s.get("mesh")
    rec["solver"]["mesh"] = {k: mesh[k] for k in MESH if k in mesh} if mesh else None
    trimmed.append(rec)
with open(os.path.join(out, "records_trimmed.json"), "w") as f:
    json.dump(trimmed, f, separators=(",", ":"))

# why the 'ordinary' steps kept the previous mesh, from the rank-0 log: block[N] holds the lines between
# step N-1's summary line and step N's. The fit's "the fault keeps its place" is printed during step N-1
# (its detection decides step N's mesh); a refused placement is printed at the start of step N itself.
ordinary = {r["step"] for r in records if r["solver"]["kind"] == "ordinary"}
blocks, block = {}, []
step_line = re.compile(r"^\[0\] step +(\d+) ")
with open(os.path.join(run, "slurm_resume.out"), errors="replace") as f:
    for line in f:
        if not line.startswith("[0] "):
            continue
        m = step_line.match(line)
        if m:
            blocks[int(m.group(1))] = block
            block = []
        else:
            block.append(line.rstrip("\n")[4:])
reasons = {n: [b for b in blocks.get(n - 1, []) if "keeps its place" in b]
           + [b for b in blocks.get(n, []) if "placement of" in b or "keeping the previous" in b] for n in ordinary}
with open(os.path.join(out, "no_rebuild_steps.txt"), "w") as f:
    f.write("# earth_recipe_movie: the steps that kept the previous step's solver mesh (records solver.kind "
            "'ordinary'), with the rank-0 log line (slurm_resume.out) that says why:\n# the fit's 'keeps its place' "
            "from the step before's detection, or a refused placement at the step's own rebuild\n")
    for n in sorted(ordinary):
        f.write(f"{n}\t{' | '.join(reasons.get(n, [])) or '(no reason line found)'}\n")
print(len(trimmed), "records;", len(ordinary), "steps without a rebuild ->", out)
