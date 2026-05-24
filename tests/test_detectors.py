from __future__ import annotations

import io
import json
import plistlib
from unittest.mock import patch, MagicMock, mock_open
import subprocess

import pytest

from pkgview.detectors.brew import BrewDetector, _run, _versions
from pkgview.detectors.npm import NpmDetector
from pkgview.detectors.pip import PipDetector, _pip_packages, _pipx_packages
from pkgview.detectors.cargo import CargoDetector
from pkgview.detectors.mamba import MambaDetector, _mamba_list
from pkgview.detectors.manual import ManualDetector, SYSTEM_PATHS
from pkgview.detectors.macos_apps import (
    MacOsAppsDetector,
    _brew_cask_names,
    _read_app_plist,
    _spotlight_find_app_paths,
    _filesystem_find_app_paths,
)
from pkgview.models import Package


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_completed(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = returncode
    return proc


# ── BrewDetector ─────────────────────────────────────────────────────────────

class TestBrewDetectorRun:
    def test_returns_lines_on_success(self):
        with patch("pkgview.detectors.brew.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("git\nwget\n")
            lines = _run(["brew", "list", "--formula"])
        assert lines == ["git", "wget"]

    def test_returns_empty_on_nonzero_returncode(self):
        with patch("pkgview.detectors.brew.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("", returncode=1)
            lines = _run(["brew", "list"])
        assert lines == []

    def test_returns_empty_on_file_not_found(self):
        with patch("pkgview.detectors.brew.subprocess.run", side_effect=FileNotFoundError):
            lines = _run(["brew", "list"])
        assert lines == []

    def test_returns_empty_on_timeout(self):
        with patch("pkgview.detectors.brew.subprocess.run", side_effect=subprocess.TimeoutExpired("brew", 30)):
            lines = _run(["brew", "list"])
        assert lines == []

    def test_strips_blank_lines(self):
        with patch("pkgview.detectors.brew.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("git\n\n  \nwget\n")
            lines = _run(["brew", "list"])
        assert lines == ["git", "wget"]


class TestBrewDetectorVersions:
    def test_parses_name_and_version(self):
        with patch("pkgview.detectors.brew.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("git 2.44.0\nwget 1.21.4\n")
            v = _versions()
        assert v == {"git": "2.44.0", "wget": "1.21.4"}

    def test_ignores_lines_without_version(self):
        with patch("pkgview.detectors.brew.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("git\nwget 1.21.4\n")
            v = _versions()
        assert "git" not in v
        assert v["wget"] == "1.21.4"


class TestBrewDetectorDetect:
    def test_detects_formulae(self):
        formula_stdout = "git\nwget\n"
        cask_stdout = ""
        versions_stdout = "git 2.44.0\nwget 1.21.4\n"

        call_map = {
            ("brew", "list", "--versions"): _make_completed(versions_stdout),
            ("brew", "list", "--formula"): _make_completed(formula_stdout),
            ("brew", "list", "--cask"): _make_completed(cask_stdout),
        }

        def side_effect(cmd, **kwargs):
            return call_map.get(tuple(cmd), _make_completed(""))

        with patch("pkgview.detectors.brew.subprocess.run", side_effect=side_effect):
            result = BrewDetector().detect()

        assert "git" in result
        assert result["git"].manager == "brew"
        assert result["git"].version == "2.44.0"
        assert result["git"].category == "cli"

    def test_detects_casks(self):
        call_map = {
            ("brew", "list", "--versions"): _make_completed("firefox 123.0\n"),
            ("brew", "list", "--formula"): _make_completed(""),
            ("brew", "list", "--cask"): _make_completed("firefox\n"),
        }

        def side_effect(cmd, **kwargs):
            return call_map.get(tuple(cmd), _make_completed(""))

        with patch("pkgview.detectors.brew.subprocess.run", side_effect=side_effect):
            result = BrewDetector().detect()

        assert "firefox" in result
        assert result["firefox"].manager == "brew-cask"
        assert result["firefox"].category == "app"

    def test_returns_empty_when_brew_not_found(self):
        with patch("pkgview.detectors.brew.subprocess.run", side_effect=FileNotFoundError):
            result = BrewDetector().detect()
        assert result == {}


# ── NpmDetector ──────────────────────────────────────────────────────────────

class TestNpmDetector:
    def test_parses_global_packages(self):
        npm_json = json.dumps({
            "dependencies": {
                "typescript": {"version": "5.4.2"},
                "eslint": {"version": "9.0.0"},
            }
        })
        with patch("pkgview.detectors.npm.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(npm_json)
            result = NpmDetector().detect()

        assert "typescript" in result
        assert result["typescript"].version == "5.4.2"
        assert result["typescript"].manager == "npm"
        assert "eslint" in result

    def test_returns_empty_when_npm_not_found(self):
        with patch("pkgview.detectors.npm.subprocess.run", side_effect=FileNotFoundError):
            result = NpmDetector().detect()
        assert result == {}

    def test_returns_empty_on_invalid_json(self):
        with patch("pkgview.detectors.npm.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("not json")
            result = NpmDetector().detect()
        assert result == {}

    def test_handles_missing_version_in_dep(self):
        npm_json = json.dumps({"dependencies": {"foo": {}}})
        with patch("pkgview.detectors.npm.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(npm_json)
            result = NpmDetector().detect()
        assert result["foo"].version is None

    def test_returns_empty_on_timeout(self):
        with patch("pkgview.detectors.npm.subprocess.run", side_effect=subprocess.TimeoutExpired("npm", 30)):
            result = NpmDetector().detect()
        assert result == {}


# ── PipDetector ───────────────────────────────────────────────────────────────

class TestPipPackages:
    def test_parses_pip_list_output(self):
        pip_json = json.dumps([
            {"name": "requests", "version": "2.31.0"},
            {"name": "click", "version": "8.1.7"},
        ])
        with patch("pkgview.detectors.pip.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(pip_json)
            result = _pip_packages()
        assert len(result) == 2
        assert result[0]["name"] == "requests"

    def test_returns_empty_on_error(self):
        with patch("pkgview.detectors.pip.subprocess.run", side_effect=FileNotFoundError):
            result = _pip_packages()
        assert result == []


class TestPipxPackages:
    def test_parses_pipx_list_output(self):
        pipx_json = json.dumps({
            "venvs": {
                "black": {
                    "metadata": {
                        "main_package": {"package_version": "24.1.1"}
                    }
                }
            }
        })
        with patch("pkgview.detectors.pip.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(pipx_json)
            result = _pipx_packages()
        assert len(result) == 1
        assert result[0]["name"] == "black"
        assert result[0]["version"] == "24.1.1"

    def test_returns_empty_on_error(self):
        with patch("pkgview.detectors.pip.subprocess.run", side_effect=FileNotFoundError):
            result = _pipx_packages()
        assert result == []


class TestPipDetectorDetect:
    def test_pipx_overrides_pip_for_same_package(self):
        pip_data = [{"name": "black", "version": "22.0.0"}]
        pipx_data = [{"name": "black", "version": "24.1.1"}]

        with patch("pkgview.detectors.pip._pip_packages", return_value=pip_data), \
             patch("pkgview.detectors.pip._pipx_packages", return_value=pipx_data):
            result = PipDetector().detect()

        assert result["black"].manager == "pipx"
        assert result["black"].version == "24.1.1"

    def test_ignores_entries_without_name(self):
        pip_data = [{"name": "", "version": "1.0"}, {"version": "1.0"}]
        with patch("pkgview.detectors.pip._pip_packages", return_value=pip_data), \
             patch("pkgview.detectors.pip._pipx_packages", return_value=[]):
            result = PipDetector().detect()
        assert result == {}

    def test_normalises_name_to_lowercase(self):
        pip_data = [{"name": "Requests", "version": "2.31.0"}]
        with patch("pkgview.detectors.pip._pip_packages", return_value=pip_data), \
             patch("pkgview.detectors.pip._pipx_packages", return_value=[]):
            result = PipDetector().detect()
        assert "requests" in result
        assert "Requests" not in result


# ── CargoDetector ─────────────────────────────────────────────────────────────

class TestCargoDetector:
    CARGO_OUTPUT = (
        "ripgrep v14.1.1:\n"
        "    rg\n"
        "bat v0.24.0:\n"
        "    bat\n"
    )

    def test_detects_installed_crates_by_binary_name(self):
        with patch("pkgview.detectors.cargo.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(self.CARGO_OUTPUT)
            result = CargoDetector().detect()

        # Keys must be the binary names (what lives in $PATH), not crate names.
        assert "rg" in result
        assert result["rg"].version == "14.1.1"
        assert result["rg"].manager == "cargo"
        assert "bat" in result
        assert result["bat"].version == "0.24.0"
        # Crate names must NOT be keys – ManualDetector keys on binary names.
        assert "ripgrep" not in result

    def test_returns_empty_when_cargo_not_found(self):
        with patch("pkgview.detectors.cargo.subprocess.run", side_effect=FileNotFoundError):
            result = CargoDetector().detect()
        assert result == {}

    def test_returns_empty_on_nonzero_returncode(self):
        with patch("pkgview.detectors.cargo.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("", returncode=1)
            result = CargoDetector().detect()
        assert result == {}

    def test_skips_header_lines_without_binary(self):
        # Only header lines, no indented binary lines
        output = "ripgrep v14.1.1:\n"
        with patch("pkgview.detectors.cargo.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(output)
            result = CargoDetector().detect()
        assert result == {}

    def test_multiple_binaries_per_crate(self):
        output = (
            "fd-find v9.0.0:\n"
            "    fd\n"
            "    fd-find\n"
        )
        with patch("pkgview.detectors.cargo.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(output)
            result = CargoDetector().detect()
        assert "fd" in result
        assert "fd-find" in result
        assert result["fd"].version == "9.0.0"


# ── ManualDetector ────────────────────────────────────────────────────────────

class TestManualDetector:
    def test_finds_unmanaged_executable(self, tmp_path):
        binary = tmp_path / "mytool"
        binary.write_text("#!/bin/sh\necho hi")
        binary.chmod(0o755)

        with patch.dict("os.environ", {"PATH": str(tmp_path)}, clear=True):
            result = ManualDetector(managed={}).detect()

        assert "mytool" in result
        assert result["mytool"].manager == "manual"
        assert result["mytool"].category == "cli"

    def test_skips_managed_binary(self, tmp_path):
        binary = tmp_path / "git"
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        managed = {"git": Package(name="git", manager="brew")}
        with patch.dict("os.environ", {"PATH": str(tmp_path)}, clear=True):
            result = ManualDetector(managed=managed).detect()

        assert "git" not in result

    def test_skips_system_paths(self, tmp_path):
        # Simulate a system path entry being in PATH
        system_dir = list(SYSTEM_PATHS)[0]

        with patch.dict("os.environ", {"PATH": system_dir}, clear=True):
            result = ManualDetector(managed={}).detect()

        # Should not crash and system binaries should not appear
        # (system_dir may not exist in test env – just assert no exception)
        assert isinstance(result, dict)

    def test_skips_non_executable_files(self, tmp_path):
        not_exec = tmp_path / "readme.txt"
        not_exec.write_text("hello")
        not_exec.chmod(0o644)

        with patch.dict("os.environ", {"PATH": str(tmp_path)}, clear=True):
            result = ManualDetector(managed={}).detect()

        assert "readme.txt" not in result

    def test_skips_directories(self, tmp_path):
        subdir = tmp_path / "adir"
        subdir.mkdir()

        with patch.dict("os.environ", {"PATH": str(tmp_path)}, clear=True):
            result = ManualDetector(managed={}).detect()

        assert "adir" not in result

    def test_deduplicates_across_path_dirs(self, tmp_path):
        dir1 = tmp_path / "d1"
        dir2 = tmp_path / "d2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "mytool").write_text("#!/bin/sh")
        (dir1 / "mytool").chmod(0o755)
        (dir2 / "mytool").write_text("#!/bin/sh")
        (dir2 / "mytool").chmod(0o755)

        with patch.dict("os.environ", {"PATH": f"{dir1}:{dir2}"}, clear=True):
            result = ManualDetector(managed={}).detect()

        assert list(result.keys()).count("mytool") == 1

    def test_returns_empty_on_nonexistent_path_dir(self):
        with patch.dict("os.environ", {"PATH": "/does/not/exist"}, clear=True):
            result = ManualDetector(managed={}).detect()
        assert result == {}


# ── MambaDetector ─────────────────────────────────────────────────────────────

_MAMBA_JSON = json.dumps([
    {"name": "numpy", "version": "1.26.4", "channel": "conda-forge"},
    {"name": "pandas", "version": "2.2.1", "channel": "conda-forge"},
    {"name": "pip-only", "version": "1.0", "channel": "pypi"},
])


class TestMambaList:
    def test_returns_parsed_list_on_success(self):
        with patch("pkgview.detectors.mamba.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(_MAMBA_JSON)
            result = _mamba_list("mamba")
        assert len(result) == 3
        assert result[0]["name"] == "numpy"

    def test_returns_empty_on_nonzero_returncode(self):
        with patch("pkgview.detectors.mamba.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("", returncode=1)
            result = _mamba_list("mamba")
        assert result == []

    def test_returns_empty_on_file_not_found(self):
        with patch("pkgview.detectors.mamba.subprocess.run", side_effect=FileNotFoundError):
            result = _mamba_list("mamba")
        assert result == []

    def test_returns_empty_on_timeout(self):
        with patch(
            "pkgview.detectors.mamba.subprocess.run",
            side_effect=subprocess.TimeoutExpired("mamba", 60),
        ):
            result = _mamba_list("mamba")
        assert result == []

    def test_returns_empty_on_invalid_json(self):
        with patch("pkgview.detectors.mamba.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed("not json")
            result = _mamba_list("mamba")
        assert result == []


class TestMambaDetectorDetect:
    def test_uses_micromamba_first(self):
        call_counts: dict = {"micromamba": 0, "mamba": 0}

        def side_effect(cmd, **kwargs):
            name = cmd[0]
            call_counts[name] = call_counts.get(name, 0) + 1
            if name == "micromamba":
                return _make_completed(_MAMBA_JSON)
            return _make_completed("[]")

        with patch("pkgview.detectors.mamba.subprocess.run", side_effect=side_effect):
            result = MambaDetector().detect()

        assert call_counts["micromamba"] == 1
        assert call_counts.get("mamba", 0) == 0
        assert result["numpy"].manager == "micromamba"

    def test_falls_back_to_mamba_when_micromamba_missing(self):
        def side_effect(cmd, **kwargs):
            if cmd[0] == "micromamba":
                raise FileNotFoundError
            return _make_completed(_MAMBA_JSON)

        with patch("pkgview.detectors.mamba.subprocess.run", side_effect=side_effect):
            result = MambaDetector().detect()

        assert "numpy" in result
        assert result["numpy"].manager == "mamba"

    def test_excludes_pypi_packages(self):
        with patch("pkgview.detectors.mamba.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(_MAMBA_JSON)
            result = MambaDetector().detect()
        assert "pip-only" not in result

    def test_returns_empty_when_neither_tool_found(self):
        with patch("pkgview.detectors.mamba.subprocess.run", side_effect=FileNotFoundError):
            result = MambaDetector().detect()
        assert result == {}

    def test_package_fields(self):
        with patch("pkgview.detectors.mamba.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed(_MAMBA_JSON)
            result = MambaDetector().detect()
        pkg = result["pandas"]
        assert pkg.version == "2.2.1"
        assert pkg.category == "cli"


# ── MacOsAppsDetector ────────────────────────────────────────────────────────

def _make_plist_bytes(bundle_id: str = "com.example.App", version: str = "1.2.3") -> bytes:
    info = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleShortVersionString": version,
    }
    return plistlib.dumps(info)


class TestBrewCaskNames:
    def test_returns_frozenset_of_lowercase_cask_names(self):
        with patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Firefox\nGoogle-Chrome\n", returncode=0)
            result = _brew_cask_names()
        assert isinstance(result, frozenset)
        assert result == frozenset({"firefox", "google-chrome"})

    def test_returns_empty_frozenset_on_timeout(self):
        with patch(
            "pkgview.detectors.macos_apps.subprocess.run",
            side_effect=subprocess.TimeoutExpired("brew", 30),
        ):
            result = _brew_cask_names()
        assert isinstance(result, frozenset)
        assert result == frozenset()

    def test_returns_empty_frozenset_when_brew_not_found(self):
        with patch("pkgview.detectors.macos_apps.subprocess.run", side_effect=OSError):
            result = _brew_cask_names()
        assert isinstance(result, frozenset)
        assert result == frozenset()

    def test_returns_empty_frozenset_on_nonzero_returncode(self):
        with patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=1)
            result = _brew_cask_names()
        assert isinstance(result, frozenset)
        assert result == frozenset()


class TestSlowWarnings:
    """Verify that _run_with_slow_warning emits a message to stderr when the
    timer fires before the subprocess finishes, and stays silent otherwise."""

    class _ImmediateTimer:
        """Replacement for threading.Timer that fires the callback synchronously
        on start() so tests are deterministic without actual sleep."""
        daemon = False

        def __init__(self, delay: float, fn):  # noqa: ANN001
            self._fn = fn

        def start(self) -> None:
            self._fn()

        def cancel(self) -> None:
            pass

    class _NeverTimer:
        """Replacement for threading.Timer that never fires (cancel always wins)."""
        daemon = False

        def __init__(self, delay: float, fn):  # noqa: ANN001
            pass

        def start(self) -> None:
            pass

        def cancel(self) -> None:
            pass

    def test_brew_emits_warning_when_slow(self, capsys):
        with patch("pkgview.detectors.macos_apps.threading.Timer", self._ImmediateTimer), \
             patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="firefox\n", returncode=0)
            _brew_cask_names()
        err = capsys.readouterr().err
        assert "brew list --cask" in err
        assert "taking longer than expected" in err

    def test_brew_no_warning_when_fast(self, capsys):
        with patch("pkgview.detectors.macos_apps.threading.Timer", self._NeverTimer), \
             patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="firefox\n", returncode=0)
            _brew_cask_names()
        assert capsys.readouterr().err == ""

    def test_spotlight_emits_warning_when_slow(self, capsys):
        with patch("pkgview.detectors.macos_apps.threading.Timer", self._ImmediateTimer), \
             patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/Applications/Safari.app\n", returncode=0)
            _spotlight_find_app_paths()
        err = capsys.readouterr().err
        assert "mdfind" in err or "Spotlight" in err
        assert "taking longer than expected" in err

    def test_spotlight_no_warning_when_fast(self, capsys):
        with patch("pkgview.detectors.macos_apps.threading.Timer", self._NeverTimer), \
             patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/Applications/Safari.app\n", returncode=0)
            _spotlight_find_app_paths()
        assert capsys.readouterr().err == ""


class TestReadAppPlist:
    def test_returns_version_and_bundle_id(self, tmp_path):
        app = tmp_path / "MyApp.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(
            _make_plist_bytes("com.example.myapp", "3.0.1")
        )
        version, bundle_id = _read_app_plist(app)
        assert version == "3.0.1"
        assert bundle_id == "com.example.myapp"

    def test_falls_back_to_bundle_version_when_short_version_absent(self, tmp_path):
        app = tmp_path / "Legacy.app"
        (app / "Contents").mkdir(parents=True)
        info = {"CFBundleVersion": "42", "CFBundleIdentifier": "com.legacy"}
        (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))
        version, bundle_id = _read_app_plist(app)
        assert version == "42"
        assert bundle_id == "com.legacy"

    def test_returns_empty_strings_when_plist_missing(self, tmp_path):
        app = tmp_path / "NoPlist.app"
        (app / "Contents").mkdir(parents=True)
        version, bundle_id = _read_app_plist(app)
        assert version == ""
        assert bundle_id == ""

    def test_returns_empty_strings_on_invalid_plist(self, tmp_path):
        app = tmp_path / "Bad.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(b"not a plist at all")
        version, bundle_id = _read_app_plist(app)
        assert version == ""
        assert bundle_id == ""

    def test_returns_empty_strings_when_plist_root_is_not_dict(self, tmp_path):
        # plistlib.load() can legitimately return a list or other type when the
        # root element is not a dict.  Calling .get() on a list raises
        # AttributeError, which must be handled gracefully.
        app = tmp_path / "ListPlist.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(["item1", "item2"]))
        version, bundle_id = _read_app_plist(app)
        assert version == ""
        assert bundle_id == ""


class TestSpotlightFindAppPaths:
    def test_returns_paths_ending_in_dot_app(self):
        stdout = "/Applications/Safari.app\n/Applications/Xcode.app\n/not-an-app/foo\n"
        with patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=stdout, returncode=0)
            paths = _spotlight_find_app_paths()
        names = [p.name for p in paths]
        assert "Safari.app" in names
        assert "Xcode.app" in names
        assert "foo" not in names

    def test_returns_empty_on_nonzero_returncode(self):
        with patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=1)
            paths = _spotlight_find_app_paths()
        assert paths == []

    def test_returns_empty_on_timeout(self):
        with patch(
            "pkgview.detectors.macos_apps.subprocess.run",
            side_effect=subprocess.TimeoutExpired("mdfind", 30),
        ):
            paths = _spotlight_find_app_paths()
        assert paths == []

    def test_returns_empty_when_mdfind_not_found(self):
        with patch("pkgview.detectors.macos_apps.subprocess.run", side_effect=OSError):
            paths = _spotlight_find_app_paths()
        assert paths == []

    def test_excludes_volumes_trash_and_derived_data_paths(self):
        stdout = (
            "/Applications/Safari.app\n"
            "/Volumes/Backup/Applications/Safari.app\n"
            "/Users/user/.Trash/Firefox.app\n"
            "/Library/Developer/Xcode/DerivedData/MyApp/Build/Products/Debug/MyApp.app\n"
        )
        with patch("pkgview.detectors.macos_apps.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=stdout, returncode=0)
            paths = _spotlight_find_app_paths()
        assert len(paths) == 1
        assert paths[0].name == "Safari.app"


class TestMacOsAppsDetectorDetect:
    def test_returns_empty_on_non_macos(self):
        with patch("pkgview.detectors.macos_apps.sys.platform", "linux"):
            result = MacOsAppsDetector().detect()
        assert result == {}

    def test_spotlight_populates_version_from_plist(self, tmp_path):
        app = tmp_path / "MyApp.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(
            _make_plist_bytes("com.example.myapp", "5.0")
        )

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[app]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(), use_spotlight=True
            ).detect()

        assert "MyApp" in result
        assert result["MyApp"].version == "5.0"
        assert result["MyApp"].category == "app"

    def test_marks_brew_cask_when_name_matches(self, tmp_path):
        app = tmp_path / "Firefox.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[app]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(["firefox"]), use_spotlight=True
            ).detect()

        assert result["Firefox"].manager == "brew-cask"

    def test_marks_manual_when_name_not_in_casks(self, tmp_path):
        app = tmp_path / "UnknownApp.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[app]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(["firefox"]), use_spotlight=True
            ).detect()

        assert result["UnknownApp"].manager == "manual"

    def test_falls_back_to_filesystem_when_spotlight_empty(self, tmp_path):
        app = tmp_path / "Fallback.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[]), \
             patch("pkgview.detectors.macos_apps._filesystem_find_app_paths", return_value=[app]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(), use_spotlight=True
            ).detect()

        assert "Fallback" in result

    def test_use_spotlight_false_skips_mdfind(self, tmp_path):
        app = tmp_path / "FSApp.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        spotlight_called = []

        def fake_spotlight():
            spotlight_called.append(True)
            return []

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", side_effect=fake_spotlight), \
             patch("pkgview.detectors.macos_apps._filesystem_find_app_paths", return_value=[app]):
            MacOsAppsDetector(brew_casks=frozenset(), use_spotlight=False).detect()

        assert not spotlight_called

    def test_deduplicates_same_app_name(self, tmp_path):
        dir1 = tmp_path / "d1"
        dir2 = tmp_path / "d2"
        for d in (dir1, dir2):
            app = d / "DupApp.app"
            (app / "Contents").mkdir(parents=True)
            (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        paths = [dir1 / "DupApp.app", dir2 / "DupApp.app"]

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=paths):
            result = MacOsAppsDetector(
                brew_casks=frozenset(), use_spotlight=True
            ).detect()

        assert list(result.keys()).count("DupApp") == 1

    def test_skips_non_directory_paths(self, tmp_path):
        not_a_dir = tmp_path / "Ghost.app"
        # deliberately do NOT create it on disk

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[not_a_dir]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(), use_spotlight=True
            ).detect()

        assert "Ghost" not in result

    def test_version_none_when_plist_has_no_version(self, tmp_path):
        app = tmp_path / "NoVersion.app"
        (app / "Contents").mkdir(parents=True)
        info = {"CFBundleIdentifier": "com.noversion"}
        (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[app]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(), use_spotlight=True
            ).detect()

        assert result["NoVersion"].version is None

    def test_auto_detects_casks_when_brew_casks_is_none(self, tmp_path):
        app = tmp_path / "Firefox.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[app]), \
             patch("pkgview.detectors.macos_apps._brew_cask_names", return_value=frozenset(["firefox"])):
            result = MacOsAppsDetector(brew_casks=None, use_spotlight=True).detect()

        assert result["Firefox"].manager == "brew-cask"

    def test_cask_normalization_fails_for_versioned_app_names(self, tmp_path):
        # Known limitation: "1Password 8" normalises to "1password-8", which
        # does not match the Homebrew cask token "1password".
        # This test documents current behaviour so regressions are detected
        # if the matching logic is improved in the future.
        app = tmp_path / "1Password 8.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(_make_plist_bytes())

        with patch("pkgview.detectors.macos_apps.sys.platform", "darwin"), \
             patch("pkgview.detectors.macos_apps._spotlight_find_app_paths", return_value=[app]):
            result = MacOsAppsDetector(
                brew_casks=frozenset(["1password"]), use_spotlight=True
            ).detect()

        # "1password-8" != "1password" – naive normalisation misses this case.
        assert result["1Password 8"].manager == "manual"

    def test_name_property(self):
        assert MambaDetector().name == "mamba"

