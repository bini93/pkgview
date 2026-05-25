from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.pacman")


class PacmanDetector(Detector):
    """
    Detects explicitly-installed packages on Arch-based Linux (pacman / yay).

    Uses ``pacman -Qe`` which lists only packages the user explicitly
    requested, not auto-installed dependencies.
    """

    @property
    def name(self) -> str:
        return "pacman"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: pacman -Qe")
        try:
            result = subprocess.run(
                ["pacman", "-Qe"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    name, version = parts[0], parts[1]
                    packages[name] = Package(
                        name=name,
                        manager="pacman",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: pacman")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: pacman -Qe")
        except OSError as exc:
            logger.warning("OS error running pacman: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``checkupdates`` (pacman-contrib) to find available updates."""
        logger.debug("Checking outdated pacman packages")
        try:
            result = subprocess.run(
                ["checkupdates"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            # checkupdates exits 1 when there are no updates (not an error)
            for line in result.stdout.splitlines():
                # Format: "package old_version -> new_version"
                parts = line.strip().split()
                if len(parts) >= 4:
                    name, latest = parts[0], parts[3]
                    if name in packages:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated pacman packages: %s", exc)
