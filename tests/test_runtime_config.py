"""Guards on how the deployed app is executed, not on what it computes.

Both facts asserted here were observed as real failures in the deployment log,
and neither is visible to the quantitative tests: the app imports and the
numbers are right, yet the process still logs an error or is one dependency
upgrade away from losing both charts.
"""
import pathlib
import sys
import threading
import time

import pytest

try:  # tomllib is stdlib from 3.11; the repo targets >= 3.11.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".streamlit" / "config.toml"
APP = ROOT / "app.py"


@pytest.mark.skipif(tomllib is None, reason="tomllib unavailable")
def test_the_local_sources_watcher_is_disabled():
    """The watcher's sys.modules eviction races a concurrent import.

    Streamlit 1.62's LocalSourcesWatcher responds to a source change by
    evicting the watched package and all its submodules from sys.modules.
    CPython's importlib._bootstrap._load ends with an unguarded
    ``sys.modules.pop(spec.name)``, so an eviction landing inside another
    thread's import of that package raises ``KeyError: 'rs_stages'`` there.

    The deployed source never changes while the process runs, so the watcher
    has nothing to gain and this to lose.
    """
    config = tomllib.loads(CONFIG.read_text())
    assert config.get("server", {}).get("fileWatcherType") == "none"


def test_the_import_eviction_race_is_real():
    """Evidence for the test above: the race is CPython's, not hypothetical.

    A package evicted from sys.modules while another thread is executing its
    body makes that thread raise KeyError with the bare package name — the
    exact error observed in the deployment log.
    """
    root = pathlib.Path(__import__("tempfile").mkdtemp())
    package = root / "evictionracepkg"
    package.mkdir()
    (package / "__init__.py").write_text("import time\ntime.sleep(0.6)\nVALUE = 1\n")
    sys.path.insert(0, str(root))
    caught: list[BaseException] = []

    def importer() -> None:
        try:
            __import__("evictionracepkg")
        except BaseException as exc:  # noqa: BLE001 - the point is what type it is
            caught.append(exc)

    thread = threading.Thread(target=importer)
    thread.start()
    try:
        time.sleep(0.3)  # land inside exec_module
        sys.modules.pop("evictionracepkg", None)  # what the watcher does
        thread.join(timeout=10)
    finally:
        sys.path.remove(str(root))
        sys.modules.pop("evictionracepkg", None)

    assert caught, "expected the importing thread to fail"
    assert isinstance(caught[0], KeyError)
    assert caught[0].args[0] == "evictionracepkg"


def test_charts_do_not_use_the_removed_components_api():
    """st.components.v1.html was scheduled for removal after 2026-06-01.

    Both charts render through it, so an upgrade past that removal would take
    the price chart and the participation trend with it. st.iframe is the
    supported replacement.
    """
    source = APP.read_text()
    assert "components.html(" not in source
    assert "streamlit.components" not in source
    assert source.count("st.iframe(") == 2
