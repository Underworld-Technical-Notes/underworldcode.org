"""Compare a rerun of problem A on a later underworld3 build with the original records.

    python compare_dev.py records_dev_a673cd52

For each record in the rerun folder, the original of the same name in records/ is read
and the velocity work, the peak slip and the patch-block solver are set side by side.
The patch blocks are the ASM blocks of the composite smoother on the finest level; the
record lists their sub-PC type as installed, so LU here means LU ran, not merely that
the options asked for it.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
SLIP_RTOL = 1e-4  # peak slip agrees to the solver tolerance (1e-6) with room to spare


def patch_solver(record):
    finest = record["level_smoothers"][-1]
    return ",".join(finest.get("asm_sub_pc", [finest["pc"]]))


def summary(record):
    its, apps = record["vel_its_all_applications_again"], record["vel_applications_again"]
    return {"its": its, "apps": apps, "per_app": its / apps,
            "slip": record["peak_slip"], "patch": patch_solver(record)}


def main(rerun):
    paths = sorted((HERE / rerun).glob("A_*.json"))
    if not paths:
        print("no records in %s" % rerun)
        return 1
    ok = True
    for path in paths:
        new = summary(json.loads(path.read_text()))
        original = HERE / "records" / path.name
        old = summary(json.loads(original.read_text())) if original.exists() else None
        print(path.stem)
        for key in ("its", "apps", "per_app", "slip", "patch"):
            print("  %-8s %-22s %s" % (key, old[key] if old else "-", new[key]))
        if old:
            same = (new["its"] == old["its"] and new["apps"] == old["apps"]
                    and abs(new["slip"] - old["slip"]) <= SLIP_RTOL * abs(old["slip"])
                    and new["patch"] == old["patch"])
            print("  ->", "reproduces" if same else "DIFFERS")
            ok &= same
        if "faclu" in path.stem or new["patch"] != "lu":
            ok &= new["patch"] == "lu"
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
