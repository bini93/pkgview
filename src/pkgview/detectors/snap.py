from __future__ import annotations

import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


class SnapDetector(Detector):
    @property
    def name(self) -> str:
        return "snap"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            result = subprocess.run(
                ["snap", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            lines = result.stdout.splitlines()
            # Skip the header line: "Name  Version  Rev  Tracking  Publisher  Notes"
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    name, version = parts[0], parts[1]
                    packages[name] = Package(
                        name=name,
                        manager="snap",
                        version=version,
                        category="cli",
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return packages
