from __future__ import annotations

import subprocess
from typing import Dict, List

from pkgview.detectors.base import Detector
from pkgview.models import Package


def _run(cmd: List[str]) -> List[str]:
    """Run a command and return non-empty output lines. Never raises."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []


def _versions() -> Dict[str, str]:
    """Return {name: version} for all installed formulae via brew list --versions."""
    versions: Dict[str, str] = {}
    for line in _run(["brew", "list", "--versions"]):
        parts = line.split()
        if len(parts) >= 2:
            versions[parts[0]] = parts[1]
    return versions


class BrewDetector(Detector):
    @property
    def name(self) -> str:
        return "brew"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        versions = _versions()

        for name in _run(["brew", "list", "--formula"]):
            packages[name] = Package(
                name=name,
                manager="brew",
                version=versions.get(name),
                category="cli",
            )

        for name in _run(["brew", "list", "--cask"]):
            packages[name] = Package(
                name=name,
                manager="brew-cask",
                version=versions.get(name),
                category="app",
            )

        return packages
