from __future__ import annotations

import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.dnf")


class DnfDetector(Detector):
    """
    Detects user-installed packages on Fedora / RHEL / CentOS via dnf/yum.

    Uses ``dnf repoquery --userinstalled`` which lists only explicitly-installed
    packages (not auto-installed dependencies). Falls back to ``yum`` if dnf is
    not available.
    """

    @property
    def name(self) -> str:
        return "dnf"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        for cmd in (["dnf"], ["yum"]):
            packages = self._query(cmd)
            if packages:
                return packages
        return packages

    def _query(self, base_cmd: list) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: %s repoquery --userinstalled", base_cmd[0])
        try:
            result = subprocess.run(
                base_cmd + [
                    "repoquery",
                    "--userinstalled",
                    "--queryformat", "%{name}\t%{version}-%{release}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Last metadata"):
                    continue
                parts = line.split("\t")
                name = parts[0].strip()
                version = parts[1].strip() if len(parts) > 1 else None
                if name:
                    packages[name] = Package(
                        name=name,
                        manager="dnf",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: %s", base_cmd[0])
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: %s repoquery", base_cmd[0])
        except OSError as exc:
            logger.warning("OS error running %s: %s", base_cmd[0], exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``dnf check-update`` to find available updates."""
        logger.debug("Checking outdated dnf packages")
        try:
            result = subprocess.run(
                ["dnf", "check-update", "--quiet"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            # exit 100 = updates available, 0 = none, 1 = error
            if result.returncode not in (0, 100):
                return
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                # Format: "package.arch   version   repo"
                if len(parts) >= 2 and "." in parts[0]:
                    name = parts[0].rsplit(".", 1)[0]
                    latest = parts[1]
                    if name in packages:
                        packages[name].outdated = True
                        packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated dnf packages: %s", exc)
