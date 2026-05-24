from __future__ import annotations

import plistlib
import subprocess
import sys
import threading
from pathlib import Path

from pkgview.detectors.base import Detector
from pkgview.models import Package


def _run_with_slow_warning(
    cmd: list[str],
    timeout: int,
    warn_after: float,
    warning: str,
) -> "subprocess.CompletedProcess[str] | None":
    """Run *cmd* and print *warning* to stderr if it hasn't finished within *warn_after* seconds.

    The full *timeout* is still honoured as a hard cap.  Returns the completed
    process, or ``None`` when the process times out or cannot be started.
    """
    def _warn() -> None:
        print(f"pkgview: {warning}", file=sys.stderr)

    timer = threading.Timer(warn_after, _warn)
    timer.daemon = True
    timer.start()
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        timer.cancel()


def _brew_cask_names() -> frozenset[str]:
    """Return the set of cask names currently managed by Homebrew."""
    result = _run_with_slow_warning(
        ["brew", "list", "--cask"],
        timeout=30,
        warn_after=10.0,
        warning="'brew list --cask' is taking longer than expected – Homebrew may be updating.",
    )
    if result is not None and result.returncode == 0:
        return frozenset(
            line.strip().lower()
            for line in result.stdout.splitlines()
            if line.strip()
        )
    return frozenset()


def _read_app_plist(app_path: Path) -> tuple[str, str]:
    """Read Info.plist from an .app bundle.

    Returns a ``(version, bundle_id)`` tuple. Both values are empty strings
    when the plist cannot be read or the keys are absent.

    Reading the plist file directly (via ``plistlib``) is faster and more
    reliable than spawning a ``mdls`` subprocess per application.
    """
    plist_path = app_path / "Contents" / "Info.plist"
    try:
        with open(plist_path, "rb") as fh:
            info = plistlib.load(fh)
        if not isinstance(info, dict):
            return "", ""
        version = str(
            info.get("CFBundleShortVersionString") or info.get("CFBundleVersion", "")
        )
        bundle_id = str(info.get("CFBundleIdentifier", ""))
        return version, bundle_id
    except (OSError, plistlib.InvalidFileException, ValueError):
        return "", ""


# Path segments that indicate unreliable mdfind results (Time Machine backups,
# system Trash, Xcode build artefacts).  Paths matching any of these are
# excluded from Spotlight results so the detector does not surface stale or
# transient app copies.
_SPOTLIGHT_EXCLUDE_SEGMENTS: tuple[str, ...] = ("/DerivedData/", "/.Trash/", "/.Trashes/")


def _spotlight_find_app_paths() -> list[Path]:
    """Use ``mdfind`` to find all .app bundles indexed by Spotlight.

    Spotlight covers a much wider set of locations than a fixed directory scan,
    including user-specific install paths, sandboxed containers, and any
    directory that happens to contain a .app bundle.  Returns an empty list
    when Spotlight is unavailable or the query times out, so callers must
    always provide a filesystem fallback.

    Paths under ``/Volumes/`` (external drives, Time Machine) and paths
    containing ``/.Trash/``, ``/.Trashes/``, or ``/DerivedData/`` (Xcode
    build artefacts) are excluded to avoid surfacing stale or transient copies
    of applications.
    """
    result = _run_with_slow_warning(
        ["mdfind", "kMDItemKind == 'Application'"],
        timeout=30,
        warn_after=5.0,
        warning="Spotlight (mdfind) is taking longer than expected – the index may be rebuilding.",
    )
    if result is None or result.returncode != 0:
        return []
    paths: list[Path] = []
    for raw in result.stdout.splitlines():
        p = raw.strip()
        if not p.endswith(".app"):
            continue
        if p.startswith("/Volumes/"):
            continue
        if any(seg in p for seg in _SPOTLIGHT_EXCLUDE_SEGMENTS):
            continue
        paths.append(Path(p))
    return paths


def _filesystem_find_app_paths() -> list[Path]:
    """Scan standard application directories for .app bundles.

    Only the **top level** of each directory is scanned (non-recursive).
    This is intentional: a recursive scan would be prohibitively slow and
    would pick up nested helper bundles inside existing ``.app`` packages.
    """
    scan_dirs = [
        Path("/Applications"),
        Path("/Applications/Utilities"),
        Path("/System/Applications"),
        Path("/System/Applications/Utilities"),
        Path.home() / "Applications",
    ]
    paths: list[Path] = []
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        try:
            for entry in scan_dir.iterdir():
                if entry.suffix == ".app":
                    paths.append(entry)
        except OSError:
            pass
    return paths


class MacOsAppsDetector(Detector):
    """Detects .app bundles on macOS.

    Discovery strategy (in order of preference):

    1. **Spotlight** (``mdfind``) – finds every application Spotlight has
       indexed, regardless of installation location.  This catches apps placed
       in non-standard directories that the old fixed-directory scan would miss.
    2. **Filesystem fallback** – scans ``/Applications``,
       ``/Applications/Utilities``, and ``~/Applications`` when Spotlight is
       unavailable or returns no results.

    For each discovered bundle, ``Contents/Info.plist`` is read directly via
    :mod:`plistlib` (no extra subprocess) to populate the ``version`` field and
    obtain the ``CFBundleIdentifier`` for future cask-matching improvements.

    Pass ``brew_casks`` (a set of already-detected cask names) to avoid a
    redundant ``brew list --cask`` subprocess call.  When omitted the detector
    falls back to calling brew itself.

    Set ``use_spotlight=False`` to skip the mdfind call entirely (useful in
    tests or on systems where Spotlight is disabled).
    """

    def __init__(
        self,
        brew_casks: frozenset[str] | None = None,
        use_spotlight: bool = True,
    ) -> None:
        # None signals "auto-detect"; an empty frozenset means "no casks known".
        self._brew_casks = brew_casks
        self._use_spotlight = use_spotlight

    @property
    def name(self) -> str:
        return "macos_apps"

    def detect(self) -> dict[str, Package]:
        if sys.platform != "darwin":
            return {}

        brew_casks = self._brew_casks if self._brew_casks is not None else _brew_cask_names()

        # Prefer Spotlight for broader coverage; fall back to filesystem scan.
        app_paths: list[Path] = []
        if self._use_spotlight:
            app_paths = _spotlight_find_app_paths()
        if not app_paths:
            app_paths = _filesystem_find_app_paths()

        packages: dict[str, Package] = {}
        for app_path in app_paths:
            if not app_path.is_dir():
                continue
            app_name = app_path.stem
            # Skip duplicate paths (Spotlight may return the same bundle twice
            # under different mount points or alias paths).
            if app_name in packages:
                continue

            version, _bundle_id = _read_app_plist(app_path)

            # Cask matching: normalize app name and compare against known casks.
            # This heuristic works well for most apps but can fail when the cask
            # token differs from the application name (e.g. "1password" vs
            # "1Password 7").  The bundle_id is available here for future
            # improvements (e.g. cross-referencing Homebrew cask metadata).
            normalized = app_name.lower().replace(" ", "-")
            manager = "brew-cask" if normalized in brew_casks else "manual"

            packages[app_name] = Package(
                name=app_name,
                manager=manager,
                version=version or None,
                path=str(app_path),
                category="app",
            )

        return packages
