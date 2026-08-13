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

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def run(*command):
    return subprocess.call(list(command), cwd=ROOT)


def main():
    if run(sys.executable, "scripts/sync_archival.py") != 0:
        sys.exit("could not sync the archival metadata")
    if run(sys.executable, "scripts/banner_body.py", "--remove") != 0:
        sys.exit("could not strip the web-only banners")

    # A preview needs the PDF of the note under review, not of the other
    # forty-one. Rebuilding all of them costs 75 seconds against 4 for one, and
    # it is the single largest part of a preview build.
    #
    # Nothing archival is at risk either way: these PDFs are published to the
    # preview site and nowhere else. The deposited copies are built by the
    # deposit workflow from `main`, and this cannot reach them.
    only = [s for s in os.environ.get("UWTN_PDF_ONLY", "").split(",") if s.strip()]
    targets = []
    for slug in only:
        source = ROOT / "articles" / slug / ("%s.md" % slug)
        if source.exists():
            targets.append(str(source.relative_to(ROOT)))
        else:
            print("UWTN_PDF_ONLY names %s, which is not an article" % slug,
                  file=sys.stderr)
    if only and not targets:
        # Asked for a subset and none of it exists: build nothing rather than
        # silently falling back to all 42, which would look like it worked.
        sys.exit("UWTN_PDF_ONLY matched no articles: %r" % only)
    if targets:
        print("building %d PDF(s) only: %s" % (len(targets), ", ".join(only)))

    # Build the first one ALONE, then the rest.
    #
    # MyST renders exports concurrently, and Typst downloads the packages its
    # generated preamble imports -- @preview/tablex -- into a per-user cache on
    # first use. On a cold cache two compiles starting together race: one is
    # still writing the package while the other tries to read it, and that one
    # dies with "unresolved import" having just watched the download reach 100%.
    # A CI runner is fresh every time, so the cache is ALWAYS cold there.
    #
    # One serial compile first warms the cache; everything after it finds the
    # package already present. Deliberately not a list of package names to
    # pre-fetch: MyST generates that preamble, so any such list would be a copy
    # of someone else's decision, silently wrong after a MyST upgrade.
    #
    # Seen on PR #17, the first build to produce two PDFs at once. It is luck
    # rather than design that the 43-PDF production build has not hit it.
    status = 0
    if len(targets) > 1:
        status = run("myst", "build", "--typst", targets[0])
        if status == 0:
            status = run("myst", "build", "--typst", *targets[1:])
    else:
        status = run("myst", "build", "--typst", *targets)

    # Always, so a failed build does not leave every article without its banner.
    run(sys.executable, "scripts/banner_body.py", "--add")

    if status != 0:
        sys.exit("myst build --typst failed (exit %d)" % status)

    # Only the articles this build actually asked MyST for. A note at draft or
    # review is left out of the toc in production, so MyST never sees it and no
    # PDF appears -- and this guard, which exists to catch a template that has
    # stopped producing PDFs at all, reported that as a failure. It is the
    # correct alarm wired to the wrong sensor: nothing is wrong, the note is
    # simply not being published yet.
    import build_index
    unpublished = set()
    if not os.environ.get("UWTN_PREVIEW"):
        for path in sorted(ROOT.glob("articles/*/metadata.yml")):
            meta = build_index.read_yaml(path)
            if meta.get("status") in ("draft", "review", "withdrawn"):
                unpublished.add(meta["slug"])

    built = sorted(ROOT.glob("articles/*/*.pdf"))
    wanted = [p.parent.name for p in sorted(ROOT.glob("articles/*/*.md"))
              if "format: typst" in p.read_text(encoding="utf-8")
              and p.parent.name not in unpublished]
    if only:
        wanted = [slug for slug in wanted if slug in only]
    missing = sorted(set(wanted) - {p.parent.name for p in built})
    if missing:
        sys.exit("%d article(s) declare a PDF export but produced none: %s"
                 % (len(missing), ", ".join(missing[:5])))
    print("built %d archival PDF(s)" % len(built))


if __name__ == "__main__":
    main()
