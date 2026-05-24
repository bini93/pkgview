from __future__ import annotations

import contextlib
from typing import Iterator
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from pkgview.cli import app
from pkgview.models import Package


runner = CliRunner()


def _make_detector_cls(packages: dict) -> type:
    """Return a fresh fake Detector class whose detect() returns ``packages``."""
    class _FakeDetector:
        name = "fake"

        def detect(self):
            return packages
    return _FakeDetector


@contextlib.contextmanager
def _mock_detectors(
    independent_packages: dict | None = None,
    macos_packages: dict | None = None,
    manual_packages: dict | None = None,
) -> Iterator[None]:
    """
    Patch INDEPENDENT_DETECTORS (module-level list), MacOsAppsDetector, and
    ManualDetector so the CLI never hits the real filesystem / subprocesses.

    ``independent_packages`` is returned by *all* independent detectors combined
    (i.e. one fake detector that returns them all).
    """
    independent_packages = independent_packages or {}
    macos_packages = macos_packages or {}
    manual_packages = manual_packages or {}

    fake_independent_cls = _make_detector_cls(independent_packages)

    fake_macos = MagicMock()
    fake_macos.return_value.detect.return_value = macos_packages

    fake_manual = MagicMock()
    fake_manual.return_value.detect.return_value = manual_packages

    with patch("pkgview.cli.INDEPENDENT_DETECTORS", [fake_independent_cls]), \
         patch("pkgview.cli.MacOsAppsDetector", fake_macos), \
         patch("pkgview.cli.ManualDetector", fake_manual):
        yield


class TestCliInputValidation:
    def test_invalid_filter_exits_with_code_1(self):
        result = runner.invoke(app, ["--filter", "nonexistent_mgr"])
        assert result.exit_code == 1
        assert "Unknown manager" in result.output

    def test_invalid_sort_exits_with_code_1(self):
        result = runner.invoke(app, ["--sort", "invalid_key"])
        assert result.exit_code == 1
        assert "Unknown sort key" in result.output

    def test_valid_filter_accepted(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--filter", "brew"])
        assert result.exit_code == 0

    def test_valid_sort_accepted(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--sort", "name"])
        assert result.exit_code == 0


class TestCliJsonOutput:
    def test_json_flag_produces_valid_json(self):
        packages = {"git": Package(name="git", manager="brew", version="2.44.0")}
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--json"])

        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "git"

    def test_json_contains_all_fields(self):
        packages = {"git": Package(name="git", manager="brew", version="2.44.0")}
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--json"])

        import json
        entry = json.loads(result.output)[0]
        assert entry["name"] == "git"
        assert entry["manager"] == "brew"
        assert entry["version"] == "2.44.0"
        assert entry["managed"] is True


class TestCliFiltering:
    def test_filter_by_manager_keeps_only_matching(self):
        packages = {
            "git": Package(name="git", manager="brew"),
            "node": Package(name="node", manager="npm"),
        }
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--json", "--filter", "brew"])

        import json
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["manager"] == "brew"

    def test_no_manual_flag_skips_manual_detector(self):
        brew_pkg = {"git": Package(name="git", manager="brew")}
        with _mock_detectors(independent_packages=brew_pkg):
            result = runner.invoke(app, ["--json", "--no-manual"])

        import json
        data = json.loads(result.output)
        assert all(p["manager"] != "manual" for p in data)

    def test_no_apps_flag_skips_macos_apps(self):
        macos_pkg = {"Safari": Package(name="Safari", manager="manual", category="app")}
        with _mock_detectors(macos_packages=macos_pkg):
            result = runner.invoke(app, ["--json", "--no-apps"])

        import json
        data = json.loads(result.output)
        assert all(p["name"] != "Safari" for p in data)


class TestCliSorting:
    def _run_sorted(self, sort_key: str, packages: dict):
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--json", "--sort", sort_key])
        import json
        return json.loads(result.output)

    def test_sort_by_name(self):
        packages = {
            "zebra": Package(name="zebra", manager="brew"),
            "apple": Package(name="apple", manager="brew"),
            "mango": Package(name="mango", manager="brew"),
        }
        data = self._run_sorted("name", packages)
        names = [p["name"] for p in data]
        assert names == sorted(names, key=str.lower)

    def test_sort_by_manager(self):
        packages = {
            "z-npm": Package(name="z-npm", manager="npm"),
            "a-brew": Package(name="a-brew", manager="brew"),
        }
        data = self._run_sorted("manager", packages)
        managers = [p["manager"] for p in data]
        assert managers == sorted(managers)

    def test_sort_by_version(self):
        packages = {
            "z": Package(name="z", manager="brew", version="3.0.0"),
            "a": Package(name="a", manager="brew", version="1.0.0"),
            "m": Package(name="m", manager="brew", version="2.0.0"),
        }
        data = self._run_sorted("version", packages)
        versions = [p["version"] for p in data]
        assert versions == sorted(versions, key=str.lower)


class TestCliVerboseMode:
    def test_verbose_exits_with_code_0(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--verbose"])
        assert result.exit_code == 0

    def test_verbose_short_flag_exits_with_code_0(self):
        with _mock_detectors():
            result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0

    def test_verbose_shows_scan_header(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--verbose"])
        assert "Scanning package managers" in result.output

    def test_verbose_shows_detector_name(self):
        packages = {"git": Package(name="git", manager="fake")}
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--verbose"])
        assert "fake" in result.output

    def test_verbose_shows_singular_package_count(self):
        packages = {"git": Package(name="git", manager="fake")}
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--verbose"])
        assert "1 package" in result.output
        assert "1 packages" not in result.output

    def test_verbose_shows_plural_package_count(self):
        packages = {
            "git": Package(name="git", manager="fake"),
            "curl": Package(name="curl", manager="fake"),
        }
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--verbose"])
        assert "2 packages" in result.output

    def test_verbose_shows_total_elapsed_time(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--verbose"])
        assert "Scan completed in" in result.output

    def test_verbose_with_no_apps(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--verbose", "--no-apps"])
        assert result.exit_code == 0

    def test_verbose_with_no_manual(self):
        with _mock_detectors():
            result = runner.invoke(app, ["--verbose", "--no-manual"])
        assert result.exit_code == 0

    def test_verbose_combined_with_json(self):
        packages = {"git": Package(name="git", manager="fake")}
        with _mock_detectors(independent_packages=packages):
            result = runner.invoke(app, ["--verbose", "--json"])
        assert result.exit_code == 0
        # verbose header and JSON data must both be present in the combined output
        assert "Scanning package managers" in result.output
        assert '"name": "git"' in result.output

    def test_verbose_detector_failure_shows_inline(self):
        """A detector exception must appear inline in verbose mode."""
        class _FailingDetector:
            name = "exploding"

            def detect(self):
                raise RuntimeError("boom")

        with patch("pkgview.cli.INDEPENDENT_DETECTORS", [_FailingDetector]), \
             patch("pkgview.cli.MacOsAppsDetector") as mock_macos, \
             patch("pkgview.cli.ManualDetector") as mock_manual:
            mock_macos.return_value.detect.return_value = {}
            mock_manual.return_value.detect.return_value = {}
            result = runner.invoke(app, ["--verbose"])

        assert result.exit_code == 0
        assert "exploding" in result.output
        assert "boom" in result.output
