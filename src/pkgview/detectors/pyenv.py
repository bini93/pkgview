from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package

logger = logging.getLogger("pkgview.detectors.pyenv")


class PyenvDetector(Detector):
    """Detects Python versions installed via pyenv."""

    @property
    def name(self) -> str:
        return "pyenv"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        # Prefer scanning ~/.pyenv/versions/ to avoid subprocess overhead
        versions_dir = Path.home() / ".pyenv" / "versions"
        if versions_dir.is_dir():
            try:
                for entry in sorted(versions_dir.iterdir()):
                    if not entry.is_dir():
                        continue
                    version = entry.name
                    key = f"python@{version}"
                    packages[key] = Package(
                        name=key,
                        manager="pyenv",
                        version=version,
                        path=str(entry / "bin" / "python"),
                        category="cli",
                    )
            except OSError as exc:
                logger.warning("Could not read pyenv versions directory: %s", exc)
            return packages

        # Fallback: pyenv binary
        logger.debug("Subprocess: pyenv versions --bare")
        try:
            result = subprocess.run(
                ["pyenv", "versions", "--bare"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                version = line.strip().removeprefix("* ").removeprefix("  ").strip()
                if not version or version == "system":
                    continue
                key = f"python@{version}"
                packages[key] = Package(
                    name=key,
                    manager="pyenv",
                    version=version,
                    category="cli",
                )
        except FileNotFoundError:
            logger.debug("Not found: pyenv")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout running: pyenv versions")
        except OSError as exc:
            logger.warning("OS error running pyenv: %s", exc)
        return packages
