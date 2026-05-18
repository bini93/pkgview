from __future__ import annotations

import json

import pytest

from pkgview.models import Package
from pkgview.output.json_out import render_json
from pkgview.output.table import render_table, MANAGER_STYLES, MANAGER_ICONS

from io import StringIO
from rich.console import Console


# ── json_out ──────────────────────────────────────────────────────────────────

class TestRenderJson:
    def _make_packages(self):
        return [
            Package(name="git", manager="brew", version="2.44.0", path=None, category="cli"),
            Package(name="firefox", manager="brew-cask", version=None, path="/Applications/Firefox.app", category="app"),
            Package(name="mytool", manager="manual", version=None, path="/usr/local/bin/mytool", category="cli"),
        ]

    def test_returns_valid_json(self):
        packages = self._make_packages()
        output = render_json(packages)
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_all_fields_present(self):
        packages = [Package(name="git", manager="brew", version="2.44.0")]
        data = json.loads(render_json(packages))
        entry = data[0]
        assert entry["name"] == "git"
        assert entry["manager"] == "brew"
        assert entry["version"] == "2.44.0"
        assert entry["path"] is None
        assert entry["category"] == "cli"
        assert entry["managed"] is True

    def test_managed_flag_false_for_manual(self):
        packages = [Package(name="mytool", manager="manual")]
        data = json.loads(render_json(packages))
        assert data[0]["managed"] is False

    def test_empty_list(self):
        output = render_json([])
        data = json.loads(output)
        assert data == []

    def test_non_ascii_names_preserved(self):
        packages = [Package(name="tëst-ünïcödé", manager="pip")]
        output = render_json(packages)
        assert "tëst-ünïcödé" in output
        # ensure_ascii=False: no escaped unicode
        assert "\\u" not in output

    def test_indented_output(self):
        packages = [Package(name="x", manager="brew")]
        output = render_json(packages)
        # indent=2 means the output has newlines and spaces
        assert "\n" in output
        assert "  " in output


# ── table ─────────────────────────────────────────────────────────────────────

class TestRenderTable:
    def _console(self) -> tuple[Console, StringIO]:
        buf = StringIO()
        console = Console(file=buf, highlight=False, no_color=True)
        return console, buf

    def test_renders_without_exception(self):
        packages = [
            Package(name="git", manager="brew", version="2.44.0"),
            Package(name="mytool", manager="manual"),
        ]
        console, _ = self._console()
        render_table(packages, console)  # must not raise

    def test_package_names_appear_in_output(self):
        packages = [
            Package(name="uniquename123", manager="brew", version="1.0"),
        ]
        console, buf = self._console()
        render_table(packages, console)
        output = buf.getvalue()
        assert "uniquename123" in output

    def test_version_appears_in_output(self):
        packages = [Package(name="git", manager="brew", version="2.44.0")]
        console, buf = self._console()
        render_table(packages, console)
        assert "2.44.0" in buf.getvalue()

    def test_missing_version_shows_dash(self):
        packages = [Package(name="foo", manager="manual")]
        console, buf = self._console()
        render_table(packages, console)
        assert "–" in buf.getvalue()

    def test_summary_line_totals(self):
        packages = [
            Package(name="a", manager="brew"),
            Package(name="b", manager="npm"),
            Package(name="c", manager="manual"),
        ]
        console, buf = self._console()
        render_table(packages, console)
        output = buf.getvalue()
        assert "3" in output   # total
        assert "2" in output   # managed
        assert "1" in output   # manual

    def test_show_paths_adds_path_column(self):
        packages = [Package(name="git", manager="brew", path="/usr/bin/git")]
        console, buf = self._console()
        render_table(packages, console, show_paths=True)
        assert "/usr/bin/git" in buf.getvalue()

    def test_show_paths_false_hides_path(self):
        packages = [Package(name="git", manager="brew", path="/usr/bin/git")]
        console, buf = self._console()
        render_table(packages, console, show_paths=False)
        assert "/usr/bin/git" not in buf.getvalue()

    def test_empty_packages_renders_summary(self):
        console, buf = self._console()
        render_table([], console)
        output = buf.getvalue()
        assert "Total" in output


class TestManagerStylesAndIcons:
    def test_all_managed_managers_have_style(self):
        from pkgview.models import MANAGED_MANAGERS
        for manager in MANAGED_MANAGERS:
            assert manager in MANAGER_STYLES, f"Missing style for manager: {manager}"

    def test_all_managed_managers_have_icon(self):
        from pkgview.models import MANAGED_MANAGERS
        for manager in MANAGED_MANAGERS:
            assert manager in MANAGER_ICONS, f"Missing icon for manager: {manager}"

    def test_manual_has_style_and_icon(self):
        assert "manual" in MANAGER_STYLES
        assert "manual" in MANAGER_ICONS
