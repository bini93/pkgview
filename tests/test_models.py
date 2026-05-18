from __future__ import annotations

import pytest

from pkgview.models import Package, MANAGED_MANAGERS


class TestPackageDefaults:
    def test_defaults(self):
        pkg = Package(name="foo", manager="brew")
        assert pkg.name == "foo"
        assert pkg.manager == "brew"
        assert pkg.version is None
        assert pkg.path is None
        assert pkg.category == "cli"

    def test_all_fields(self):
        pkg = Package(name="bar", manager="npm", version="1.2.3", path="/usr/bin/bar", category="app")
        assert pkg.version == "1.2.3"
        assert pkg.path == "/usr/bin/bar"
        assert pkg.category == "app"


class TestPackageIsManaged:
    @pytest.mark.parametrize("manager", sorted(MANAGED_MANAGERS))
    def test_managed_managers_return_true(self, manager):
        pkg = Package(name="x", manager=manager)
        assert pkg.is_managed is True

    def test_manual_returns_false(self):
        pkg = Package(name="x", manager="manual")
        assert pkg.is_managed is False

    def test_unknown_manager_returns_false(self):
        pkg = Package(name="x", manager="unknown_mgr")
        assert pkg.is_managed is False
