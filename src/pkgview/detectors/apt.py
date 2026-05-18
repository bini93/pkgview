from __future__ import annotations

import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


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
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return packages
