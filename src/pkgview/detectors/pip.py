from __future__ import annotations

import json
import logging
import subprocess
from typing import Dict, List

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.pip")


def _pip_packages() -> List[Dict]:
    logger.debug("Subprocess: pip list --format=json")
    try:
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except FileNotFoundError:
        logger.debug("Not found: pip")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("Timeout running: pip list")
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse pip list output: %s", exc)
        return []
    except OSError as exc:
        logger.warning("OS error running pip: %s", exc)
        return []


def _pipx_packages() -> List[Dict]:
    logger.debug("Subprocess: pipx list --json")
    try:
        result = subprocess.run(
            ["pipx", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        items = []
        for pkg_name, info in data.get("venvs", {}).items():
            version = (
                info.get("metadata", {})
                    .get("main_package", {})
                    .get("package_version")
            )
            items.append({"name": pkg_name, "version": version})
        return items
    except FileNotFoundError:
        logger.debug("Not found: pipx")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("Timeout running: pipx list")
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse pipx list output: %s", exc)
        return []
    except OSError as exc:
        logger.warning("OS error running pipx: %s", exc)
        return []


class PipDetector(Detector):
    @property
    def name(self) -> str:
        return "pip"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}

        for item in _pip_packages():
            name = item.get("name", "").lower()
            if name:
                packages[name] = Package(
                    name=name,
                    manager="pip",
                    version=item.get("version"),
                    category="cli",
                )

        # pipx overrides pip for the same package (more specific)
        for item in _pipx_packages():
            name = item.get("name", "").lower()
            if name:
                packages[name] = Package(
                    name=name,
                    manager="pipx",
                    version=item.get("version"),
                    category="cli",
                )

        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``pip list --outdated --format=json`` to find outdated packages."""
        logger.debug("Checking outdated pip packages")
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return
            data = json.loads(result.stdout)
            for item in data:
                name = item.get("name", "").lower()
                latest = item.get("latest_version")
                if name in packages and latest:
                    packages[name].outdated = True
                    packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not check outdated pip packages: %s", exc)
