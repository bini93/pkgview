from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.asdf")


class AsdfDetector(Detector):
    """Detects runtimes installed via asdf version manager."""

    @property
    def name(self) -> str:
        return "asdf"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        # Prefer scanning ~/.asdf/installs/ to avoid needing the shell wrapper
        installs_dir = Path.home() / ".asdf" / "installs"
        if installs_dir.is_dir():
            return self._scan_installs(installs_dir)
        # Fallback: try the asdf binary directly (e.g. mise-managed asdf)
        return self._run_list()

    def _scan_installs(self, installs_dir: Path) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            for plugin_dir in sorted(installs_dir.iterdir()):
                if not plugin_dir.is_dir():
                    continue
                plugin = plugin_dir.name
                for version_dir in sorted(plugin_dir.iterdir()):
                    if not version_dir.is_dir():
                        continue
                    version = version_dir.name
                    key = f"{plugin}@{version}"
                    packages[key] = Package(
                        name=key,
                        manager="asdf",
                        version=version,
                        path=str(version_dir),
                        category="cli",
                    )
        except OSError as exc:
            logger.warning("Could not read asdf installs directory: %s", exc)
        return packages

    def _run_list(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        logger.debug("Subprocess: asdf list")
        try:
            result = subprocess.run(
                ["asdf", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            current_plugin: str | None = None
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if not line.startswith(" "):
                    current_plugin = stripped
                elif current_plugin:
                    version = stripped.lstrip("* ")
                    key = f"{current_plugin}@{version}"
                    packages[key] = Package(
                        name=key,
                        manager="asdf",
                        version=version,
                        category="cli",
                    )
        except FileNotFoundError:
            logger.debug("Not found: asdf")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: asdf list")
        except OSError as exc:
            logger.warning("OS error running asdf: %s", exc)
        return packages
