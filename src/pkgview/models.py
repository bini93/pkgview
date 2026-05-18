from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


MANAGED_MANAGERS: frozenset[str] = frozenset(
    {"brew", "brew-cask", "npm", "pip", "pipx", "apt", "snap", "flatpak", "cargo"}
)


@dataclass
class Package:
    name: str
    manager: str  # "brew" | "brew-cask" | "npm" | "pip" | "pipx" |
                  # "apt" | "snap" | "flatpak" | "cargo" | "manual"
    version: Optional[str] = None
    path: Optional[str] = None
    category: str = "cli"  # "cli" | "app"

    @property
    def is_managed(self) -> bool:
        return self.manager in MANAGED_MANAGERS
