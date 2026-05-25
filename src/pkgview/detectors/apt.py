from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.apt")


class AptDetector(Detector):
    @property
    def name(self) -> str:
        return "apt"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            # apt-mark showmanual lists only packages the user explicitly installed,
            # not auto-installed dependencies – exactly what we want.
            result = subprocess.run(
                ["apt-mark", "showmanual"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                name = line.strip()
                if name:
                    packages[name] = Package(name=name, manager="apt", category="cli")
        except FileNotFoundError:
            logger.debug("Not found: apt-mark")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: apt-mark showmanual")
        except OSError as exc:
            logger.warning("OS error running apt-mark: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``apt list --upgradable`` to find packages with available updates."""
        logger.debug("Checking outdated apt packages")
        try:
            result = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            for line in result.stdout.splitlines():
                # Format: "package/source version arch [upgradable from: old_ver]"
                if "/" not in line:
                    continue
                name = line.split("/")[0].strip()
                parts = line.split()
                latest = parts[1] if len(parts) >= 2 else None
                if name in packages and latest:
                    packages[name].outdated = True
                    packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated apt packages: %s", exc)
