from __future__ import annotations

import json
import subprocess
import sys
from typing import Dict, List

from pkgview.detectors.base import Detector
from pkgview.models import Package


def _pip_packages() -> List[Dict]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []


def _pipx_packages() -> List[Dict]:
    try:
        result = subprocess.run(
            ["pipx", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        items = []
        for pkg_name, info in data.get("venvs", {}).items():
            version = (
                info.get("metadata", {})
                    .get("main_package", {})
                    .get("package_version")
            )
            items.append({"name": pkg_name, "version": version})
        return items
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []


class PipDetector(Detector):
    @property
    def name(self) -> str:
        return "pip"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}

        for item in _pip_packages():
            name = item.get("name", "").lower()
            if name:
                packages[name] = Package(
                    name=name,
                    manager="pip",
                    version=item.get("version"),
                    category="cli",
                )

        # pipx overrides pip for the same package (more specific)
        for item in _pipx_packages():
            name = item.get("name", "").lower()
            if name:
                packages[name] = Package(
                    name=name,
                    manager="pipx",
                    version=item.get("version"),
                    category="cli",
                )

        return packages
