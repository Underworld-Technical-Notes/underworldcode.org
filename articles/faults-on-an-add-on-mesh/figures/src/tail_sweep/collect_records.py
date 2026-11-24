"""Collect the sweep's JSON records into summary tables (markdown) and one JSON file.

For problem B it also sums every application of the velocity sub-KSP from the run's
log (the 'Linear rotfsN_fieldsplit_vel_ solve converged/diverged ... iterations k'
lines), since vel_its_last is the last application per Newton increment only. The
smoother each level ran comes from the record; for the B arms run before the smoothers
were recorded, from the set-up probe of the same arm (probes/).

    python collect_records.py
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REASON = re.compile(r"Linear rotfs\d+_fieldsplit_vel_ solve (converged|did not converge|diverged)"
                    r".*?iterations (\d+)")
ORDER = {"H0": 0, "H0 nofac": 1, "H0 faclu": 2, "H1": 3, "H1 nofac": 4, "H1c": 5, "H2": 6, "H3": 7}


def velocity_work(log):
    """(applications, iterations, applications at the cap) over the whole run."""
    apps = its = capped = 0
    if not os.path.exists(log):
        return None
    with open(log) as f:
        for line in f:
            m = REASON.search(line)
            if m:
                apps += 1
                its += int(m.group(2))
                capped += m.group(1) != "converged"
    return apps, its, capped


def load(pattern, directory="records"):
    out = []
    for path in sorted(glob.glob(os.path.join(HERE, directory, pattern))):
        with open(path) as f:
            rec = json.load(f)
        rec["_tag"] = os.path.basename(path)[:-5]
        flag = next((s for s in ("nofac", "faclu") if f"_{s}_" in rec["_tag"]), None)
        rec["_arm"] = rec["hierarchy"] + (f" {flag}" if flag else "")
        out.append(rec)
    return out


def complexity(r):
    """Operator complexity: the nonzeros of every level over the finest level's."""
    nnz = [o["rows"] * o["nnz_per_row"] for o in r["level_ops_velocity"]]
    return sum(nnz) / nnz[-1] if nnz else float("nan")


def fcycle(r):
    """F-cycle complexity: as complexity(), each level weighted by its visits per
    application. pc_mg_type full runs a V-cycle from every level in turn, so the level
    d steps below the finest is smoothed d + 1 times."""
    nnz = [o["rows"] * o["nnz_per_row"] for o in r["level_ops_velocity"]]
    n = len(nnz)
    return sum((n - j) * nnz[j] for j in range(n)) / nnz[-1] if nnz else float("nan")


def smoothers(r):
    """The smoother of every level above the coarse solve, coarsest first: sor (whole
    level), or FAC-<block solver> (composite: whole-level SOR, then ASM over the band)."""
    sm = r.get("level_smoothers")
    if not sm:
        probe = os.path.join(HERE, "probes", r["_tag"].replace("_np4", "_probe_np4") + ".json")
        if not os.path.exists(probe):
            return "?"
        with open(probe) as f:
            sm = json.load(f)["level_smoothers"]
    return ", ".join(f"FAC-{e['asm_sub_pc'][0]}" if e["pc"] == "composite" else e["pc"]
                     for e in sm[1:])


def table_a(recs):
    rows = ["| np | h_b/S | arm | levels (cells) | smoother per level | nnz/row per level | op. complexity | F-cycle complexity | vel (last) | vel, all applications / applications | work (all its x F-cycle complexity) | pres | setup s | solve s | peak slip |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda r: (r["np"], r["n_rungs"], ORDER[r["_arm"]])):
        nnz = ", ".join(f"{o['nnz_per_row']:.0f}" for o in r["level_ops_velocity"])
        setup = r["t_place_s"] + r["t_solve_first_s"] - r["t_solve_again_s"]
        rows.append(
            f"| {r['np']} | {r['h_b_over_S']:.1f} | {r['_arm']} | "
            f"{', '.join(str(c) for c in r['level_cells'])} | {smoothers(r)} | {nnz} | "
            f"{complexity(r):.2f} | {fcycle(r):.2f} | "
            f"{r['vel_its_last'][0] if r['vel_its_last'] else '-'} | "
            f"{r['vel_its_all_applications_again']} / {r['vel_applications_again']} | "
            f"{r['vel_its_all_applications_again'] * fcycle(r):.0f} | "
            f"{r['pres_its_last'][0] if r['pres_its_last'] else '-'} | {setup:.1f} | "
            f"{r['t_solve_again_s']:.1f} | {r['peak_slip']:.8f} |")
    return "\n".join(rows)


def table_b(recs):
    rows = ["| h_b/S | arm | levels (cells) | smoother per level | nnz/row per level | op. complexity | F-cycle complexity | Newton (switch at) | vel total (last per increment) | vel per increment, Newton phase | caps 200 | vel, all applications / applications | work (all its x F-cycle complexity) | pres min-max | place s | solve s | peak slip |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda r: (-r["S"], ORDER[r["_arm"]])):
        nnz = ", ".join(f"{o['nnz_per_row']:.0f}" for o in r["level_ops_velocity"])
        work = velocity_work(os.path.join(HERE, "logs", r["_tag"] + ".log"))
        r["vel_work_all_applications"] = work
        mm = r["vel_its_newton_phase_min_max"]
        pres = r["pres_its_last"] or []
        rows.append(
            f"| {r['h_b_over_S']:.1f} | {r['_arm']} | "
            f"{', '.join(str(c) for c in r['level_cells'])} | {smoothers(r)} | {nnz} | "
            f"{complexity(r):.2f} | {fcycle(r):.2f} | "
            f"{r['newton_iterations']} ({r['continuation_switch_iteration']}) | {r['vel_its_last_total']} | "
            f"{mm[0]}-{mm[1]} | {r['vel_caps_200']} | "
            f"{work[1] if work else '-'} / {work[0] if work else '-'} | "
            f"{work[1] * fcycle(r) if work else float('nan'):.0f} | "
            f"{min(pres) if pres else '-'}-{max(pres) if pres else '-'} | {r['t_place_s']:.1f} | "
            f"{r['t_solve_s']:.0f} | {r['peak_slip']:.4f} |")
    return "\n".join(rows)


a, b = load("A_*.json"), load("B_*.json")
text = ("## Problem A, linear (the note's fixture)\n\n" + table_a(a)
        + "\n\n## Problem B, the yielding-lid box (one solve from rest, np 4)\n\n" + table_b(b) + "\n")
with open(os.path.join(HERE, "summary.md"), "w") as f:
    f.write(text)
with open(os.path.join(HERE, "records_all.json"), "w") as f:
    json.dump({"A": a, "B": b}, f, indent=1)
print(text)
