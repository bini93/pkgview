from __future__ import annotations

import json
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


class NpmDetector(Detector):
    @property
    def name(self) -> str:
        return "npm"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            result = subprocess.run(
                ["npm", "list", "-g", "--depth=0", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # npm exits non-zero when there are peer dep warnings; parse anyway
            data = json.loads(result.stdout)
            for pkg_name, info in data.get("dependencies", {}).items():
                version: str | None = info.get("version") if isinstance(info, dict) else None
                packages[pkg_name] = Package(
                    name=pkg_name,
                    manager="npm",
                    version=version,
                    category="cli",
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
            pass
        return packages
