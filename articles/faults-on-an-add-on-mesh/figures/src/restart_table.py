"""The restart table of RESTART_AND_RECORDS.md section 5 (and UWTN 2026-022), from the runs.

Each test is a pair: a run continued uninterrupted through the window, and the same run
restarted from its own checkpoint at the window's start. For the first step after the
restart: the nonlinear iterations and the Stokes time (record t_stokes), beside the
uninterrupted run's at the same step; then the agreement of the restarted run with the
uninterrupted one over the window (largest relative vrms and slip_max difference; whether
the fault events and the rebuild count n_built move identically). Prints the table as
markdown, then the run directories, their provenance (run_info.json, or for runs that
predate it the job log's Script/Container lines) and the records read.

    python restart_table.py -uw_tests "original:<dir>/old_a,<dir>/old_b;decisions+V_b:<dir>/new_a,<dir>/new_b;faulted-mesh checkpoint:<dir>/i3_a,<dir>/i3_b16"
"""
import glob
import json
import os

import underworld3 as uw

params = uw.Params(
    # label:uninterrupted,restarted;label:...  (section 5's three tests on kaiju by default)
    uw_tests="original driver:~/campaigns/dev-restart-runs/old_a,~/campaigns/dev-restart-runs/old_b;"
             "decision state + V_b warm start:~/campaigns/dev-restart-runs/new_a,~/campaigns/dev-restart-runs/new_b;"
             "faulted-mesh checkpoint:~/campaigns/dev-restart-runs/i3_a,~/campaigns/dev-restart-runs/i3_b16",
    uw_restart=3590,            # the checkpoint the restarted runs start from
    uw_last=3600,               # the window's last step
)


def records(run):
    with open(os.path.join(run, "records.json")) as f:
        return {r["step"]: r for r in json.load(f)}


def provenance(run):
    """Driver and library commits from run_info.json (the last entry: the restart's), or the
    driver path, container and arguments from the newest job log for runs that predate it."""
    path = os.path.join(run, "run_info.json")
    if os.path.exists(path):
        with open(path) as f:
            info = json.load(f)
        info = info[-1] if isinstance(info, list) else info
        return (f"run_info.json: driver {info.get('driver_commit')}, uw3 {info.get('uw3_commit')}, "
                f"np {info.get('mpi_ranks')}, restart_from {info.get('restart_from')}")
    logs = sorted(glob.glob(os.path.join(run, "slurm_*.out")), key=os.path.getmtime)
    if not logs:
        return "no run_info.json and no job log"
    head = {}
    with open(logs[-1]) as f:
        for line in f:
            key, _, value = line.partition(":")
            if key in ("Container", "Script", "Extra pkgs", "MPI ranks"):
                head[key] = value.strip()
    script = head.get("Script", "").split()
    return (f"{os.path.basename(logs[-1])} (no run_info.json): driver {script[0] if script else '?'}, "
            f"container {head.get('Container')}, overlay {head.get('Extra pkgs')}, np {head.get('MPI ranks')}, "
            f"args {' '.join(script[1:])}")


def its(r):
    sv = r.get("solver") or {}
    return sv.get("nonlinear_its", r.get("newton"))


first, last = int(params.uw_restart) + 1, int(params.uw_last)
rows, sources = [], []
for test in str(params.uw_tests).split(";"):
    label, pair = test.split(":", 1)
    a_dir, b_dir = (os.path.expanduser(p) for p in pair.split(","))
    a, b = records(a_dir), records(b_dir)
    window = [s for s in range(first, last + 1) if s in a and s in b]
    rel = lambda k: max(abs(b[s][k] - a[s][k]) / abs(a[s][k]) for s in window)
    events = all(a[s].get("events") == b[s].get("events") for s in window)
    built = all(a[s]["n_built"] - a[first]["n_built"] == b[s]["n_built"] - b[first]["n_built"] for s in window)
    rows.append((label, its(b[first]), b[first]["t_stokes"], its(a[first]), a[first]["t_stokes"],
                 rel("vrms"), rel("slip_max"), events, built, b[first]["n_built"] == a[first]["n_built"],
                 f"{window[0]}-{window[-1]}"))
    sources += [(label, "uninterrupted", a_dir, provenance(a_dir), sorted(a)[0], sorted(a)[-1]),
                (label, "restarted", b_dir, provenance(b_dir), sorted(b)[0], sorted(b)[-1])]

print(f"First step after the restart from {params.uw_restart} (step {first}); agreement over steps {first}-{last}\n")
print("| test | Newton its | Stokes s | uninterrupted: its / Stokes s | vrms (max rel) | slip_max (max rel) "
      "| events identical | rebuilds identical | n_built carried over |")
print("|---|---|---|---|---|---|---|---|---|")
for (label, bi, bs, ai, as_, dv, ds, ev, bu, carried, win) in rows:
    print(f"| {label} | {bi} | {bs:.0f} | {ai} / {as_:.0f} | {dv:.1e} | {ds:.1e} | {'yes' if ev else 'no'} "
          f"| {'yes' if bu else 'no'} | {'yes' if carried else 'no (reset)'} |")
print(f"\nRuns and records read (records.json; the table uses steps {first}-{last}):")
for label, role, d, prov, s0, s1 in sources:
    print(f"- {label}, {role}: {d} (records {s0}-{s1}); {prov}")
