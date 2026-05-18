from __future__ import annotations

import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


class FlatpakDetector(Detector):
    @property
    def name(self) -> str:
        return "flatpak"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=name,version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if not parts:
                    continue
                name = parts[0].strip()
                version = parts[1].strip() if len(parts) > 1 else None
                if name:
                    packages[name] = Package(
                        name=name,
                        manager="flatpak",
                        version=version,
                        category="app",
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return packages
