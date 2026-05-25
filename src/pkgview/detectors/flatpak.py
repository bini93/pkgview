from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.flatpak")


class FlatpakDetector(Detector):
    @property
    def name(self) -> str:
        return "flatpak"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: flatpak list")
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=name,version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if not parts:
                    continue
                name = parts[0].strip()
                version = parts[1].strip() if len(parts) > 1 else None
                if name:
                    packages[name] = Package(
                        name=name,
                        manager="flatpak",
                        version=version,
                        category="app",
                    )
        except FileNotFoundError:
            logger.debug("Not found: flatpak")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: flatpak list")
        except OSError as exc:
            logger.warning("OS error running flatpak: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``flatpak remote-ls --updates`` to find apps with available updates."""
        logger.debug("Checking outdated flatpak packages")
        try:
            result = subprocess.run(
                ["flatpak", "remote-ls", "--updates", "--app",
                 "--columns=name,version"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if not parts:
                    continue
                name = parts[0].strip()
                latest = parts[1].strip() if len(parts) > 1 else None
                if name in packages:
                    packages[name].outdated = True
                    packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated flatpak packages: %s", exc)
