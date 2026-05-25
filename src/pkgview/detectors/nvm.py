from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.nvm")


class NvmDetector(Detector):
    """Detects Node.js versions installed via nvm by scanning ~/.nvm/versions/node/."""

    @property
    def name(self) -> str:
        return "nvm"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        nvm_dir = Path.home() / ".nvm" / "versions" / "node"
        if not nvm_dir.is_dir():
            return {}
        try:
            for entry in sorted(nvm_dir.iterdir()):
                if not entry.is_dir():
                    continue
                version = entry.name.lstrip("v")
                key = f"node@{entry.name}"
                packages[key] = Package(
                    name=key,
                    manager="nvm",
                    version=version,
                    path=str(entry / "bin" / "node"),
                    category="cli",
                )
        except OSError as exc:
            logger.warning("Could not read nvm directory %s: %s", nvm_dir, exc)
        return packages
