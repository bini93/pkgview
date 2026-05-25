from __future__ import annotations

import json
import logging
import subprocess
from typing import Dict, List

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.conda")


def _conda_list(cmd: str) -> List[Dict]:
    """Run ``cmd list --json`` and return the parsed list. Never raises."""
    logger.debug("Subprocess: %s list --json", cmd)
    try:
        result = subprocess.run(
            [cmd, "list", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except FileNotFoundError:
        logger.debug("Not found: %s", cmd)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("Timeout running: %s list", cmd)
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse %s list output: %s", cmd, exc)
        return []
    except OSError as exc:
        logger.warning("OS error running %s: %s", cmd, exc)
        return []


class CondaDetector(Detector):
    """
    Detects packages installed in the active conda environment.

    Only queries the ``conda`` binary. Packages managed by mamba or
    micromamba are handled by the dedicated MambaDetector.
    """

    @property
    def name(self) -> str:
        return "conda"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        manager_label = "conda"

        items = _conda_list("conda")

        for item in items:
            name = item.get("name", "").strip()
            version = item.get("version")
            channel = item.get("channel", "")
            if not name:
                continue
            # Skip packages that came from pip inside the conda env
            if channel in ("pypi",):
                continue
            packages[name] = Package(
                name=name,
                manager=manager_label,
                version=version,
                category="cli",
            )
        return packages
