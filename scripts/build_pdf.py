#!/usr/bin/env python3
"""Build the archival PDFs, and fail if they do not build.

Three things have to happen in order, and the middle one is allowed to fail:

    sync the archival facts into the front matter
    take the web-only banner out       (it belongs on the site, not on page 1)
    myst build --typst
    put the banner back                (whether or not the build worked)

Written as a script rather than a shell one-liner because the exit status has
to survive the restore step. As a pixi task with `;` between the two, a broken
template produced **no PDFs at all** and the task still reported success -- CI
deposited a record with no article in it, and nothing said a word. A build step
that cannot fail is not a build step.

Usage:
    python3 scripts/build_pdf.py
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(*command):
    return subprocess.call(list(command), cwd=ROOT)


def main():
    if run(sys.executable, "scripts/sync_archival.py") != 0:
        sys.exit("could not sync the archival metadata")
    if run(sys.executable, "scripts/banner_body.py", "--remove") != 0:
        sys.exit("could not strip the web-only banners")

    status = run("myst", "build", "--typst")

    # Always, so a failed build does not leave every article without its banner.
    run(sys.executable, "scripts/banner_body.py", "--add")

    if status != 0:
        sys.exit("myst build --typst failed (exit %d)" % status)

    built = sorted(ROOT.glob("articles/*/*.pdf"))
    wanted = [p.parent.name for p in sorted(ROOT.glob("articles/*/*.md"))
              if "format: typst" in p.read_text(encoding="utf-8")]
    missing = sorted(set(wanted) - {p.parent.name for p in built})
    if missing:
        sys.exit("%d article(s) declare a PDF export but produced none: %s"
                 % (len(missing), ", ".join(missing[:5])))
    print("built %d archival PDF(s)" % len(built))


if __name__ == "__main__":
    main()
