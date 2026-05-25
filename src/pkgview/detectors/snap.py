from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.snap")


class SnapDetector(Detector):
    @property
    def name(self) -> str:
        return "snap"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: snap list")
        try:
            result = subprocess.run(
                ["snap", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            lines = result.stdout.splitlines()
            # Skip the header line: "Name  Version  Rev  Tracking  Publisher  Notes"
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    name, version = parts[0], parts[1]
                    packages[name] = Package(
                        name=name,
                        manager="snap",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: snap")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: snap list")
        except OSError as exc:
            logger.warning("OS error running snap: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``snap refresh --list`` to find snaps with available updates."""
        logger.debug("Checking outdated snap packages")
        try:
            result = subprocess.run(
                ["snap", "refresh", "--list"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return
            lines = result.stdout.splitlines()
            for line in lines[1:]:  # skip header
                parts = line.split()
                if len(parts) >= 2:
                    name, latest = parts[0], parts[1]
                    if name in packages:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated snap packages: %s", exc)
