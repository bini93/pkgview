from pkgview.detectors.brew import BrewDetector
from pkgview.detectors.npm import NpmDetector
from pkgview.detectors.pip import PipDetector
from pkgview.detectors.cargo import CargoDetector
from pkgview.detectors.apt import AptDetector
from pkgview.detectors.snap import SnapDetector
from pkgview.detectors.flatpak import FlatpakDetector
from pkgview.detectors.macos_apps import MacOsAppsDetector
from pkgview.detectors.manual import ManualDetector

__all__ = [
    "BrewDetector",
    "NpmDetector",
    "PipDetector",
    "CargoDetector",
    "AptDetector",
    "SnapDetector",
    "FlatpakDetector",
    "MacOsAppsDetector",
    "ManualDetector",
]
