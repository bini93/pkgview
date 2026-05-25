from __future__ import annotations

import json
import logging
import subprocess
from typing import Dict, List, Tuple

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.mamba")


def _mamba_list(cmd: str) -> List[Dict]:
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


# Candidates in preference order: micromamba first (standalone, no conda dep),
# then mamba (requires conda base env).
_CANDIDATES: Tuple[str, ...] = ("micromamba", "mamba")


class MambaDetector(Detector):
    """
    Detects packages installed in the active mamba / micromamba environment.

    Tries micromamba first, then mamba. The manager label reflects whichever
    tool responded. Packages that came via pip inside the environment are
    excluded (channel == "pypi") to avoid double-counting with PipDetector.
    """

    @property
    def name(self) -> str:
        return "mamba"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        items: List[Dict] = []
        manager_label = "mamba"

        for cmd in _CANDIDATES:
            items = _mamba_list(cmd)
            if items:
                manager_label = cmd  # "micromamba" or "mamba"
                break

        for item in items:
            name = item.get("name", "").strip()
            version = item.get("version")
            channel = item.get("channel", "")
            if not name:
                continue
            if channel in ("pypi",):
                continue
            packages[name] = Package(
                name=name,
                manager=manager_label,
                version=version,
                category="cli",
            )
        return packages
