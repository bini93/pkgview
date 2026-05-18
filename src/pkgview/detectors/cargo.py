from __future__ import annotations

import re
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


class CargoDetector(Detector):
    @property
    def name(self) -> str:
        return "cargo"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            result = subprocess.run(
                ["cargo", "install", "--list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            # Output format:
            #   ripgrep v14.1.1:
            #       rg
            #   bat v0.24.0:
            #       bat
            for line in result.stdout.splitlines():
                match = re.match(r"^(\S+)\s+v([\d.][^\s:]*):", line)
                if match:
                    name, version = match.group(1), match.group(2)
                    packages[name] = Package(
                        name=name,
                        manager="cargo",
                        version=version,
                        category="cli",
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return packages
