from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.gem")


class GemDetector(Detector):
    """Detects globally installed Ruby gems."""

    @property
    def name(self) -> str:
        return "gem"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: gem list --no-verbose")
        try:
            result = subprocess.run(
                ["gem", "list", "--no-verbose"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                # Format: "gem_name (version1, version2)"
                line = line.strip()
                if not line or line.startswith("***"):
                    continue
                if "(" in line:
                    name = line[: line.index("(")].strip()
                    versions_str = line[line.index("(") + 1: line.index(")")]
                    version = versions_str.split(",")[0].strip()
                else:
                    name = line
                    version = None
                if name:
                    packages[name] = Package(
                        name=name,
                        manager="gem",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: gem")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: gem list")
        except OSError as exc:
            logger.warning("OS error running gem: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``gem outdated`` to find gems with available updates."""
        logger.debug("Checking outdated gem packages")
        try:
            result = subprocess.run(
                ["gem", "outdated"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return
            for line in result.stdout.splitlines():
                # Format: "gem_name (current < latest)"
                if "(" in line and "<" in line:
                    name = line[: line.index("(")].strip()
                    inner = line[line.index("(") + 1: line.index(")")]
                    parts = inner.split("<")
                    latest = parts[1].strip() if len(parts) > 1 else None
                    if name in packages:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated gem packages: %s", exc)
