"""The style checker reports the habits it claims to, and nothing else.

Each check gets a positive case and a negative control, because a hint
that fires on everything is worse than no hint: it teaches an author to
ignore the report.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "scripts"))
import check_style  # noqa: E402


def _check(tmp_path, body):
    f = tmp_path / "note.md"
    f.write_text(body)
    hints, _voice = check_style.check(f)
    return {h[0] for h in hints}


def test_a_heading_that_argues_is_reported(tmp_path):
    body = "\n".join([
        "## The container: just what we need",
        "Text.",
        "## The launcher: an almost empty repository",
        "Text.",
        "## nbgitpuller: your notebooks, nothing required of them",
        "Text.",
    ])
    assert "heading-habit" in _check(tmp_path, body)


def test_labelled_headings_are_not_reported(tmp_path):
    """The negative control: a colon is what a label is made of."""
    body = "\n".join([
        "## Stage 1: Approximate lookup",
        "Text.",
        "## Stage 2: Inside/outside confirmation",
        "Text.",
        "## Stage 3: Unwrapping",
        "Text.",
        "## Ubuntu:",
        "Text.",
        "## UWTN 2026-014: Setting up full multigrid",
        "Text.",
    ])
    assert "heading-habit" not in _check(tmp_path, body)


def test_announcing_the_writing_is_reported(tmp_path):
    assert "announcing" in _check(
        tmp_path, "Written plainly, the link says which version.\n")
    assert "announcing" not in _check(
        tmp_path, "The link says which version.\n")


def test_withholding_is_reported(tmp_path):
    assert "withholding" in _check(
        tmp_path, "The workflow then does the thing that matters:\n")
    assert "withholding" not in _check(
        tmp_path, "The workflow then dispatches to the launcher:\n")


def test_code_blocks_are_not_prose(tmp_path):
    """A fenced block may legitimately contain any of these strings."""
    body = "```python\n# the thing that matters\nx = 1\n```\n"
    assert _check(tmp_path, body) == set()


def test_front_matter_is_not_prose(tmp_path):
    body = "---\ntitle: \"A Note: What It Really Is\"\n---\n\nText.\n"
    assert _check(tmp_path, body) == set()


def test_densities_need_a_long_enough_document(tmp_path):
    """Short documents get no density hints: the ratio is meaningless."""
    assert "second-person" not in _check(
        tmp_path, "You should note that you can do this yourself.\n")


def test_a_one_word_subject_does_not_escape(tmp_path):
    """`Gadi:` is exempt because it is a series label, not because it is one
    word. A one-off one-word subject is the same construction as any other."""
    argued = "\n".join([
        "## Underworld: what it really does", "Text.",
        "## Binder: not what you think", "Text.",
        "## Containers: the surprise", "Text.",
    ])
    assert "heading-habit" in _check(tmp_path, argued)


def test_a_repeated_one_word_prefix_is_a_series_label(tmp_path):
    """The negative control for the rule above: one heading per machine."""
    series = "\n".join([
        "## Gadi: weak scaling, Q1", "Text.",
        "## Gadi: weak scaling, Q2", "Text.",
        "## Magnus: weak scaling, Q1", "Text.",
        "## Magnus: weak scaling, Q2", "Text.",
    ])
    assert "heading-habit" not in _check(tmp_path, series)


def test_front_matter_may_start_after_a_blank_line(tmp_path):
    body = '\n---\ntitle: "X"\ndescription: to be honest, a note\n---\n\nText.\n'
    assert _check(tmp_path, body) == set()
