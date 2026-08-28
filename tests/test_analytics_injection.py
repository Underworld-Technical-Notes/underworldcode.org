"""The analytics beacon is injected the one way this theme allows.

The theme hydrates the whole document, so a beacon placed statically is
reconciled away. These tests hold the two properties that follow: nothing
is written into the page except a bootstrap that runs after hydration,
and the beacon is confined to the production hostname so that previews
and the dev server do not report into the live figures.
"""
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "scripts"))
import inject_analytics  # noqa: E402

CONFIG = {"enabled": "true", "token": "abc123",
          "hostname": "www.underworldcode.org"}


def test_the_shipped_config_is_well_formed():
    """The token is a 32-character hex site identifier, and the hostname is
    the one the site actually serves -- the apex redirects to www, so a
    guard naming the apex would drop every visit."""
    config = inject_analytics.load_config()
    assert config["enabled"] in ("true", "false")
    if config["enabled"] == "true":
        assert re.fullmatch(r"[0-9a-f]{32}", config["token"]), config["token"]
    assert config["hostname"] == \
        pathlib.Path("CNAME").read_text().strip()


def test_the_beacon_matches_cloudflares_own_snippet():
    """Their snippet is type=module; ours must be too, or a future real
    module would fail to parse as a classic script and stop reporting."""
    payload = inject_analytics.bootstrap(CONFIG)
    assert 'script.type = "module"' in payload


def test_nothing_is_placed_statically():
    """The negative control for the whole approach: if the payload carried
    a beacon tag of its own, hydration would remove it."""
    payload = inject_analytics.bootstrap(CONFIG)
    assert "data-cf-beacon=" not in payload
    assert inject_analytics.BEACON in payload      # only as a string
    assert 'src="https://static.cloudflareinsights' not in payload


def test_the_bootstrap_waits_for_hydration():
    payload = inject_analytics.bootstrap(CONFIG)
    assert "readyState" in payload and "load" in payload


def test_the_beacon_is_confined_to_the_production_hostname():
    payload = inject_analytics.bootstrap(CONFIG)
    assert "www.underworldcode.org" in payload
    assert "window.location.hostname !== HOSTNAME" in payload


def test_the_token_reaches_the_page():
    assert '"abc123"' in inject_analytics.bootstrap(CONFIG)


def test_every_page_is_injected_once(tmp_path, monkeypatch):
    build = tmp_path / "_build" / "html"
    for name in ("index.html", "a/index.html", "b/index.html"):
        page = build / name
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<html><body>x</body></html>")
    monkeypatch.setattr(inject_analytics, "ROOT", tmp_path)
    monkeypatch.setattr(inject_analytics, "load_config", lambda *a: CONFIG)
    monkeypatch.setattr(sys, "argv", ["x", "--build", "_build/html"])
    inject_analytics.main()
    pages = sorted(build.rglob("*.html"))
    assert len(pages) == 3
    for page in pages:
        assert page.read_text().count(inject_analytics.MARKER) == 1

    # a second run is a no-op rather than a second beacon
    inject_analytics.main()
    for page in pages:
        assert page.read_text().count(inject_analytics.MARKER) == 1


def test_disabled_config_injects_nothing(tmp_path, monkeypatch):
    build = tmp_path / "_build" / "html"
    build.mkdir(parents=True)
    page = build / "index.html"
    page.write_text("<html><body>x</body></html>")
    monkeypatch.setattr(inject_analytics, "ROOT", tmp_path)
    monkeypatch.setattr(inject_analytics, "load_config",
                        lambda *a: {"enabled": "false", "token": ""})
    monkeypatch.setattr(sys, "argv", ["x", "--build", "_build/html"])
    inject_analytics.main()
    assert inject_analytics.MARKER not in page.read_text()


def test_enabled_without_a_token_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(inject_analytics, "load_config",
                        lambda *a: {"enabled": "true", "token": ""})
    monkeypatch.setattr(sys, "argv", ["x"])
    with pytest.raises(SystemExit):
        inject_analytics.main()
