"""The outstanding report names the half-finished states, and stays quiet
otherwise.

The negative controls matter more than usual here. This exists because
silence was mistaken for good news, so a check that cannot answer must
say so rather than report nothing, and a clean repository must produce
no noise at all.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "scripts"))
import outstanding  # noqa: E402

CLEAN = {"unrecorded": [], "queued": [], "stale": [], "undeposited": [],
         "blind": [], "reserved": []}


def test_a_clean_repository_says_nothing():
    text, n = outstanding.report(dict(CLEAN))
    assert n == 0
    assert text == "Nothing outstanding."


def test_an_unanswerable_check_says_so_rather_than_nothing():
    """None is not []. If gh cannot answer, the report must not read as
    'nothing outstanding' -- that is the mistake this tool exists for."""
    f = dict(CLEAN, unrecorded=None)
    text, n = outstanding.report(f)
    assert "not checked" in text
    assert n == 0                      # unknown is not counted as outstanding


def test_unrecorded_timestamps_are_reported_as_bookkeeping():
    """They are no longer dangerous -- the identifiers reach main through the
    request -- so the report must not describe them as if they were."""
    f = dict(CLEAN, unrecorded=[
        {"number": 25, "title": "Deposit identifiers from run 1",
         "createdAt": "2026-08-17T21:39:38Z"}])
    text, n = outstanding.report(f)
    assert n == 1
    assert "#25" in text and "2026-08-17" in text
    assert "nothing is at risk" in text


def test_a_reserved_draft_with_no_request_is_distinguished_from_one_in_flight():
    """A reserved DOI whose request is open is the gate working. The same
    DOI with no request is an unused draft, and only this says so."""
    in_flight = dict(CLEAN,
                     reserved=[("note-a", "10.0/x")],
                     queued=[{"number": 7, "title": "Deposit: note-a",
                              "createdAt": "2026-09-01T00:00:00Z"}])
    text, n = outstanding.report(in_flight)
    assert n == 1 and "request #7 open" in text
    assert "NO OPEN REQUEST" not in text

    stranded = dict(CLEAN, reserved=[("note-a", "10.0/x")])
    text, n = outstanding.report(stranded)
    assert n == 1 and "NO OPEN REQUEST" in text


def test_a_request_with_nothing_reserved_is_reported():
    """A leftover from the shared-queue design, or a reserve that failed:
    merging it would not deposit anything."""
    f = dict(CLEAN, queued=[{"number": 33, "title": "Deposit: note-b",
                             "createdAt": "2026-08-23T00:00:00Z"}])
    text, n = outstanding.report(f)
    assert n == 1 and "#33" in text and "nothing reserved" in text


def test_a_note_ahead_of_its_deposit_is_reported():
    f = dict(CLEAN, stale=[("running-underworld-in-a-browser", "1.0.0", "1.1.0")])
    text, n = outstanding.report(f)
    assert n == 1
    assert "deposited 1.0.0, now 1.1.0" in text


def test_a_deposit_with_no_recorded_version_is_not_assumed_current():
    """A note deposited before archived_version existed must be reported,
    not silently taken to match."""
    f = dict(CLEAN, stale=[("old-note", "unrecorded", "1.0.0")])
    text, n = outstanding.report(f)
    assert n == 1 and "unrecorded" in text


def test_the_counts_add_up():
    f = {"unrecorded": [{"number": 1, "title": "t", "createdAt": "2026-01-01T00:00:00Z"}],
         "queued": [{"number": 2, "title": "Deposit: z",
                     "createdAt": "2026-01-01T00:00:00Z"}],
         "reserved": [("a", "10.0/x")],
         "stale": [("a", "1.0.0", "1.1.0")],
         "undeposited": ["b"],
         "blind": ["c"]}
    _text, n = outstanding.report(f)
    # 1 timestamps + 1 reserved + 1 orphan request + 1 stale + 1 never + 1 blind
    assert n == 6


def test_the_real_repository_surveys_without_network():
    """The metadata half must work with no gh and no network at all."""
    f = outstanding.survey(check_net=False)
    assert f["unrecorded"] is None and f["queued"] is None
    assert isinstance(f["stale"], list)
    # every deposited note carries archived_version after the backfill, so
    # nothing should be reported as having an unrecorded deposit version
    assert not [s for s in f["stale"] if s[1] == "unrecorded"], f["stale"]
    # and validate already forbids a doi with no record id
    assert f["blind"] == []
