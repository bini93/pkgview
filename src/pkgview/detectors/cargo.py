from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.cargo")


class CargoDetector(Detector):
    @property
    def name(self) -> str:
        return "cargo"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: cargo install --list")
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
            # The binary name (indented line) is what ends up in $PATH, not the
            # crate name. We key by binary name so ManualDetector correctly
            # identifies these as managed.
            current_version: str | None = None
            for line in result.stdout.splitlines():
                match = re.match(r"^(\S+)\s+v([\d.][^\s:]*):" , line)
                if match:
                    current_version = match.group(2)
                elif current_version is not None and line.startswith("    "):
                    binary = line.strip()
                    if binary:
                        packages[binary] = Package(
                            name=binary,
                            manager="cargo",
                            version=current_version,
                            category="cli",
                        )
        except FileNotFoundError:
            logger.debug("Not found: cargo")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: cargo install --list")
        except OSError as exc:
            logger.warning("OS error running cargo: %s", exc)
        return packages
