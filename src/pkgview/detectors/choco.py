from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.choco")


class ChocoDetector(Detector):
    """Detects packages installed via Chocolatey (Windows)."""

    @property
    def name(self) -> str:
        return "chocolatey"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: choco list --local-only")
        try:
            result = subprocess.run(
                ["choco", "list", "--local-only", "--no-progress"],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                # Skip footer lines like "X packages installed."
                if "package" in stripped.lower() and "installed" in stripped.lower():
                    continue
                parts = stripped.split()
                if len(parts) >= 2:
                    name, version = parts[0], parts[1]
                    packages[name] = Package(
                        name=name,
                        manager="chocolatey",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: choco")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: choco list")
        except OSError as exc:
            logger.warning("OS error running choco: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``choco outdated`` to find packages with available updates."""
        logger.debug("Checking outdated chocolatey packages")
        try:
            result = subprocess.run(
                ["choco", "outdated", "--no-progress"],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return
            for line in result.stdout.splitlines():
                # Format: "package_name|current_version|latest_version|pinned"
                parts = line.strip().split("|")
                if len(parts) >= 3:
                    name, _current, latest = parts[0], parts[1], parts[2]
                    if name in packages:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated choco packages: %s", exc)
