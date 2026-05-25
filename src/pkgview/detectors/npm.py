from __future__ import annotations

import json
import logging
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.npm")


class NpmDetector(Detector):
    @property
    def name(self) -> str:
        return "npm"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: npm list -g --depth=0 --json")
        try:
            result = subprocess.run(
                ["npm", "list", "-g", "--depth=0", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # npm exits non-zero when there are peer dep warnings; parse anyway.
            # Guard against an empty body (e.g. no global packages installed).
            if not result.stdout.strip():
                return {}
            data = json.loads(result.stdout)
            for pkg_name, info in data.get("dependencies", {}).items():
                version: str | None = info.get("version") if isinstance(info, dict) else None
                packages[pkg_name] = Package(
                    name=pkg_name,
                    manager="npm",
                    version=version,
                    category="cli",
                )
        except FileNotFoundError:
            logger.debug("Not found: npm")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: npm list")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse npm list output: %s", exc)
        except OSError as exc:
            logger.warning("OS error running npm: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``npm outdated -g --json`` to find globally outdated packages."""
        logger.debug("Checking outdated npm packages")
        try:
            result = subprocess.run(
                ["npm", "outdated", "-g", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            # npm outdated exits 1 when there are outdated packages — that's OK
            if not result.stdout.strip():
                return
            data = json.loads(result.stdout)
            for name, info in data.items():
                if not isinstance(info, dict):
                    continue
                latest = info.get("latest") or info.get("wanted")
                if name in packages and latest:
                    packages[name].outdated = True
                    packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not check outdated npm packages: %s", exc)
