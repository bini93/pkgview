from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from pkgview.models import Package


class Detector(ABC):
    """Abstract base class for all package manager detectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this detector (e.g. 'brew', 'npm')."""
        ...

    @abstractmethod
    def detect(self) -> Dict[str, Package]:
        """
        Run detection and return a mapping of binary_name -> Package.

        Must never raise exceptions – return an empty dict on any failure
        so that one broken detector cannot crash the whole tool.
        """
        ...
