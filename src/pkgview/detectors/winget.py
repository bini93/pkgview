from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.winget")


class WingetDetector(Detector):
    """Detects packages installed via Windows Package Manager (winget)."""

    @property
    def name(self) -> str:
        return "winget"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: winget list")
        try:
            result = subprocess.run(
                [
                    "winget",
                    "list",
                    "--source", "winget",
                    "--accept-source-agreements",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return {}
            lines = result.stdout.splitlines()
            # Skip header lines (Name, Id, Version, Available, Source) and separators
            header_passed = False
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if set(stripped.replace(" ", "")) <= set("-"):
                    header_passed = True
                    continue
                if not header_passed:
                    continue
                # Columns are separated by two or more spaces
                parts = re.split(r"  +", stripped)
                if len(parts) >= 3:
                    name = parts[0].strip()
                    version = parts[2].strip() if parts[2].strip() else None
                    if name:
                        packages[name] = Package(
                            name=name,
                            manager="winget",
                            version=version,
                            category="cli",
                        )
        except FileNotFoundError:
            logger.debug("Not found: winget")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: winget list")
        except OSError as exc:
            logger.warning("OS error running winget: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``winget upgrade --source winget`` to find available updates."""
        logger.debug("Checking outdated winget packages")
        try:
            result = subprocess.run(
                [
                    "winget",
                    "upgrade",
                    "--source", "winget",
                    "--accept-source-agreements",
                ],
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
                if set(stripped.replace(" ", "")) <= set("-") and stripped:
                    header_passed = True
                    continue
                if not header_passed:
                    continue
                parts = re.split(r"  +", stripped)
                # Columns: Name, Id, Version, Available, Source
                if len(parts) >= 4:
                    name = parts[0].strip()
                    latest = parts[3].strip()
                    if name in packages and latest:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated winget packages: %s", exc)
