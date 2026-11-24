"""A movie figure plays on the site and shows its still in the PDF."""

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_pdf", ROOT / "scripts" / "build_pdf.py")
build_pdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_pdf)

MOVIE = """Before.

```{figure} figures/run.mp4
:placeholder: figures/run-still.png
:alt: the mesh moving
:label: fig-run

A caption.
```

After.
"""


def test_a_movie_figure_shows_its_still():
    out = build_pdf.movies_to_stills(MOVIE)
    assert "```{figure} figures/run-still.png\n" in out
    assert "run.mp4" not in out
    assert ":placeholder:" not in out
    assert ":alt: the mesh moving\n:label: fig-run\n\nA caption.\n```" in out


def test_a_colon_fence_is_swapped_too():
    text = MOVIE.replace("```", ":::")
    assert ":::{figure} figures/run-still.png\n" in build_pdf.movies_to_stills(text)


def test_an_image_figure_is_left_alone():
    text = MOVIE.replace("run.mp4", "run.png")
    assert build_pdf.movies_to_stills(text) == text


def test_a_movie_without_a_still_stops_the_build():
    text = MOVIE.replace(":placeholder: figures/run-still.png\n", "")
    with pytest.raises(SystemExit, match="has no :placeholder: still"):
        build_pdf.movies_to_stills(text, where="articles/x/x.md")


def test_the_published_notes_need_no_swap_today():
    # A guard on the swap, not on the notes: it must not touch any note that has
    # no movie, which is every note at the time of writing.
    for path in sorted(ROOT.glob("articles/*/*.md")):
        text = path.read_text(encoding="utf-8")
        if ".mp4" not in text and ".webm" not in text and ".mov" not in text:
            assert build_pdf.movies_to_stills(text) == text, path


def test_the_web_blocks_are_stripped_before_the_swaps_read_the_sources(monkeypatch):
    """A swap writes back the text it read. Read before the strip, it put the
    banner and the comments block back into the PDF of every note with a movie
    (UWTN 2026-011 1.1.0 and 1.2.0). And if a swap fails, the strip is undone."""
    events = []

    class Stop(Exception):
        pass

    def fake_run(*command):
        events.append(command[-1])
        return 0

    def fake_swaps():
        events.append("swaps")
        raise Stop

    monkeypatch.setattr(build_pdf, "run", fake_run)
    monkeypatch.setattr(build_pdf, "movie_swaps", fake_swaps)
    with pytest.raises(Stop):
        build_pdf.main()
    assert events.index("--remove") < events.index("swaps")
    assert events[-1] == "--add"
