#!/usr/bin/env python3
"""Build a preview. The ONE definition of what that means.

Both routes call this -- `pixi run preview` from a laptop and the workflow on a
push -- because they publish to the same hashed directory, and if they built
different things the content at that URL would depend on which ran last. That
is the sort of difference nobody notices until two people are looking at the
same link and disagreeing about what it says.

What a preview is:

  * the notes the branch changes, and nothing else. One page instead of
    fifty-four, one PDF instead of forty-two: 37 seconds against 190. A preview
    is for checking how a note reads and renders, not for checking the site,
    and a sidebar holding one page is one you cannot get lost in.
  * unpublished notes shown -- UWTN_PREVIEW -- since that is the point.
  * a branch that changes no article gets the whole site, because then the site
    IS what changed.

ORDER MATTERS. `build-pdf` depends on `index`, which regenerates the full toc,
so the toc has to be cut AFTER it and before the HTML. Cut first and it is put
straight back: MyST builds everything, the saving vanishes, and nothing says
so -- the preview still works, just slowly, which is the hardest kind of
regression to notice.

Usage:
    python3 scripts/preview_build.py --slugs a-note,b-note --base-url /x/y
    python3 scripts/preview_build.py --whole-site --base-url /x/y
"""

import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def build(slugs, base_url, whole_site=False):
    env = dict(os.environ)
    env["UWTN_PREVIEW"] = "1"
    env["UWTN_PDF_ONLY"] = ",".join(slugs)
    if base_url:
        env["BASE_URL"] = base_url

    if not slugs or whole_site:
        steps = [["pixi", "run", "build"]]
    else:
        steps = [
            ["pixi", "run", "build-pdf"],
            [sys.executable, "scripts/preview_only.py", "--slugs", ",".join(slugs)],
            ["pixi", "run", "myst", "build", "--html"],
            [sys.executable, "scripts/fix_slugs.py"],
            [sys.executable, "scripts/inject_style.py"],
            [sys.executable, "scripts/stage_downloads.py"],
        ]
    for step in steps:
        if subprocess.call(step, cwd=ROOT, env=env) != 0:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slugs", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--whole-site", action="store_true")
    args = parser.parse_args()

    slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    if not build(slugs, args.base_url, args.whole_site):
        sys.exit("the preview build failed")
    print("preview built: %s" % (", ".join(slugs) if slugs and not args.whole_site
                                 else "the whole site"))


if __name__ == "__main__":
    main()
