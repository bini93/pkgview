from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.scoop")


class ScoopDetector(Detector):
    """Detects packages installed via Scoop (Windows)."""

    @property
    def name(self) -> str:
        return "scoop"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: scoop list")
        try:
            result = subprocess.run(
                ["scoop", "list"],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return {}
            header_passed = False
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                # Scoop header: "Installed apps:" or column header "Name  Version ..."
                if stripped.startswith("Installed apps:"):
                    continue
                if stripped.lower().startswith("name") and "version" in stripped.lower():
                    header_passed = True
                    continue
                if not header_passed:
                    # Try to detect data lines anyway: first column is the app name
                    if stripped.startswith("-"):
                        header_passed = True
                        continue
                # Data lines: "7zip  24.09.0  main  2025-01-01  -"
                parts = stripped.split()
                if len(parts) >= 2:
                    name, version = parts[0], parts[1]
                    packages[name] = Package(
                        name=name,
                        manager="scoop",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: scoop")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: scoop list")
        except OSError as exc:
            logger.warning("OS error running scoop: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``scoop status`` to find packages with available updates."""
        logger.debug("Checking outdated scoop packages")
        try:
            result = subprocess.run(
                ["scoop", "status"],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return
            header_passed = False
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.lower().startswith("name") and "latest" in stripped.lower():
                    header_passed = True
                    continue
                if stripped.startswith("-"):
                    header_passed = True
                    continue
                if not header_passed:
                    continue
                # "Name  Installed  Latest  Missing  Info"
                parts = stripped.split()
                if len(parts) >= 3:
                    name, _installed, latest = parts[0], parts[1], parts[2]
                    if name in packages:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated scoop packages: %s", exc)
