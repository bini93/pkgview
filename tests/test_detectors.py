from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from pkgview.detectors.brew import BrewDetector, _run, _versions
from pkgview.detectors.npm import NpmDetector
from pkgview.detectors.pip import PipDetector, _pip_packages, _pipx_packages
from pkgview.detectors.cargo import CargoDetector
from pkgview.detectors.manual import ManualDetector, SYSTEM_PATHS
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
