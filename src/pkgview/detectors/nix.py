from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.nix")


class NixDetector(Detector):
    """Detects packages installed in the user Nix profile (nix-env)."""

    @property
    def name(self) -> str:
        return "nix"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: nix-env -q --no-name")
        try:
            result = subprocess.run(
                ["nix-env", "-q", "--no-name"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                # Format: "package-version" e.g. "ripgrep-14.1.1"
                stripped = line.strip()
                if not stripped:
                    continue
                # Strip Nix attribute suffixes like "-bin"
                last_dash = stripped.rfind("-")
                if last_dash > 0 and stripped[last_dash + 1:].replace(".", "").isdigit():
                    name = stripped[:last_dash]
                    version = stripped[last_dash + 1:]
                else:
                    name = stripped
                    version = None
                packages[name] = Package(
                    name=name,
                    manager="nix",
                    version=version,
                    category="cli",
                )
        except FileNotFoundError:
            logger.debug("Not found: nix-env")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: nix-env -q")
        except OSError as exc:
            logger.warning("OS error running nix-env: %s", exc)
        return packages

    def check_outdated(self, packages: Dict[str, Package]) -> None:
        """Uses ``nix-env --upgrade --dry-run`` to find outdated packages."""
        logger.debug("Checking outdated nix packages")
        try:
            result = subprocess.run(
                ["nix-env", "--upgrade", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout + result.stderr
            for line in output.splitlines():
                # Format: "upgrading 'old-version' to 'new-version'"
                if "upgrading" in line and " to " in line:
                    m = re.search(r"upgrading '([^']+)' to '([^']+)'", line)
                    if m:
                        old_attr, new_attr = m.group(1), m.group(2)
                        # Extract name (strip version)
                        last_dash = old_attr.rfind("-")
                        name = old_attr[:last_dash] if last_dash > 0 else old_attr
                        new_last = new_attr.rfind("-")
                        latest = new_attr[new_last + 1:] if new_last > 0 else None
                        if name in packages:
                            packages[name].outdated = True
                            packages[name].latest_version = latest
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Could not check outdated nix packages: %s", exc)
