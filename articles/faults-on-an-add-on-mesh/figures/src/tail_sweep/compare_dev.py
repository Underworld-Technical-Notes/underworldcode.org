"""Compare a rerun of problem A on a later underworld3 build with the original records.

    python compare_dev.py records_dev_a673cd52

Each rerun record is set beside the original record of the same smoother: the velocity
work, the peak slip, the patch-block solver and the solve time. The patch blocks are the
ASM blocks of the composite smoother on the finest level; the record lists their sub-PC
type as installed, so LU here means LU ran, not merely that the options asked for it.

Arms, by the suffix after the hierarchy:
    _faclu   blocks by LU (-uw_fac_lu 1)                original: the same name
    _facilu  blocks by ILU(0) (-uw_fac_ilu 1)           original: no suffix, which ran
                                                        ILU(0) by default before #912
    _nofac   no patch, SOR alone                        original: the same name
    (none)   the build's default; LU from #912 on      original: _faclu
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
SLIP_RTOL = 1e-4  # peak slip agrees to the solver tolerance (1e-6) with room to spare
ARMS = {"_faclu": ("_faclu", "lu"), "_facilu": ("", "ilu"),
        "_nofac": ("_nofac", "sor"), "": ("_faclu", "lu")}


def patch_solver(record):
    finest = record["level_smoothers"][-1]
    return ",".join(finest.get("asm_sub_pc", [finest["pc"]]))


def summary(record):
    its, apps = record["vel_its_all_applications_again"], record["vel_applications_again"]
    return {"its": its, "apps": apps, "per_app": round(its / apps, 2),
            "slip": record["peak_slip"], "patch": patch_solver(record),
            "t_solve_s": record["t_solve_again_s"]}


def main(rerun):
    paths = sorted((HERE / rerun).glob("A_*.json"))
    if not paths:
        print("no records in %s" % rerun)
        return 1
    ok = True
    for path in paths:
        head, arm, tail = re.fullmatch(r"(A_r\d+_H\d)((?:_\w+?)?)(_np\d+)", path.stem).groups()
        original_arm, expected = ARMS[arm]
        original = HERE / "records" / (head + original_arm + tail + ".json")
        new, old = summary(json.loads(path.read_text())), summary(json.loads(original.read_text()))
        same = (new["its"] == old["its"] and new["apps"] == old["apps"]
                and abs(new["slip"] - old["slip"]) <= SLIP_RTOL * abs(old["slip"])
                and new["patch"] == expected)
        print("%s  (against %s, expecting %s)" % (path.stem, original.stem, expected))
        for key in ("its", "apps", "per_app", "slip", "patch", "t_solve_s"):
            print("  %-10s %-22s %s" % (key, old[key], new[key]))
        print("  ->", "reproduces" if same else "DIFFERS")
        ok &= same
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
