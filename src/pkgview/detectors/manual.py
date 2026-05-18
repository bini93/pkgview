from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


# Directories that contain OS-provided system binaries, not user-installed tools.
# Binaries here are skipped to avoid polluting the "manual" list.
SYSTEM_PATHS: frozenset[str] = frozenset({
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/usr/libexec",
    "/usr/lib",
    "/usr/games",
    "/snap/bin",              # snap managed
    "/var/lib/flatpak/exports/bin",  # flatpak managed
})

# Additional system paths to skip (Apple-internal tooling)
SYSTEM_PATH_PREFIXES: tuple[str, ...] = (
    "/Library/Apple/",
    "/System/Volumes/",
    "/System/Library/",
)

# If a binary's real path is under one of these prefixes it belongs to
# Homebrew even if the formula name does not match the binary name.
BREW_CELLAR_PREFIXES: tuple[str, ...] = (
    "/opt/homebrew/Cellar/",      # Apple Silicon – formulas
    "/opt/homebrew/Caskroom/",    # Apple Silicon – casks
    "/opt/homebrew/share/",       # Apple Silicon – shared files (e.g. flutter)
    "/opt/homebrew/opt/",         # Apple Silicon – opt links
    "/usr/local/Cellar/",         # Intel Mac – formulas
    "/usr/local/Caskroom/",       # Intel Mac – casks
    "/usr/local/share/",          # Intel Mac – shared files
    "/usr/local/opt/",            # Intel Mac – opt links
    "/home/linuxbrew/.linuxbrew/Cellar/",   # Linuxbrew
    "/home/linuxbrew/.linuxbrew/share/",    # Linuxbrew
)


class ManualDetector(Detector):
    """
    Scans every directory in $PATH for executable files.

    Any binary that is not already tracked by another detector is marked
    as manager="manual", meaning it was not installed by a known package
    manager and needs to be maintained by the user.

    System paths (e.g. /bin, /usr/bin) are excluded because they contain
    OS-provided tools, not user-installed software.

    ``managed`` should be the dict of already-detected packages so that
    known binaries are not duplicated as manual. Defaults to an empty dict
    (all PATH binaries will be reported as manual) which satisfies the
    no-argument construction implied by the Detector interface.
    """

    def __init__(self, managed: Dict[str, Package] | None = None) -> None:
        self._managed: Dict[str, Package] = managed if managed is not None else {}

    @property
    def name(self) -> str:
        return "manual"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        managed_names = set(self._managed.keys())

        path_dirs = os.environ.get("PATH", "").split(":")
        seen: set[str] = set()

        for path_dir in path_dirs:
            p = Path(path_dir)
            if not p.is_dir():
                continue
            # Skip OS system directories
            if str(p) in SYSTEM_PATHS:
                continue
            try:
                for entry in p.iterdir():
                    if entry.name in seen:
                        continue
                    seen.add(entry.name)

                    # Already tracked by a package manager
                    if entry.name in managed_names:
                        continue

                    try:
                        if entry.is_file() and os.access(str(entry), os.X_OK):
                            real_path = str(entry.resolve())
                            # Binary lives inside Homebrew → managed by brew
                            if any(real_path.startswith(p) for p in BREW_CELLAR_PREFIXES):
                                continue
                            # Binary is an Apple/macOS internal system tool
                            if any(real_path.startswith(p) for p in SYSTEM_PATH_PREFIXES):
                                continue
                            packages[entry.name] = Package(
                                name=entry.name,
                                manager="manual",
                                path=real_path,
                                category="cli",
                            )
                    except (PermissionError, OSError):
                        pass
            except (PermissionError, OSError):
                pass

        return packages
