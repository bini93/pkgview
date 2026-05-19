from __future__ import annotations

from typing import List

from rich.console import Console, RenderableType
from rich.table import Table
from rich.text import Text

from pkgview.models import Package


MANAGER_STYLES: dict[str, str] = {
    "brew": "bold green",
    "brew-cask": "bold cyan",
    "npm": "bold yellow",
    "pip": "bold blue",
    "pipx": "bold bright_blue",
    "cargo": "bold red",
    "apt": "bold magenta",
    "snap": "bold bright_magenta",
    "flatpak": "bold bright_cyan",
    "manual": "bold yellow",
}

MANAGER_ICONS: dict[str, str] = {
    "brew": "🍺",
    "brew-cask": "🍺",
    "npm": "📦",
    "pip": "🐍",
    "pipx": "🐍",
    "cargo": "🦀",
    "apt": "🐧",
    "snap": "🐧",
    "flatpak": "🐧",
    "manual": "⚠ ",
}


def render_table(packages: List[Package], console: Console, show_paths: bool = False) -> None:
    table = Table(
        show_header=True,
        header_style="bold white",
        border_style="bright_black",
        row_styles=["", "dim"],
    )
    table.add_column("Name", style="white bold", no_wrap=True, min_width=18)
    table.add_column("Manager", no_wrap=True, min_width=14)
    table.add_column("Version", style="dim", min_width=8, max_width=14)
    table.add_column("Type", style="dim", min_width=5, max_width=6)
    if show_paths:
        table.add_column("Path", style="dim", overflow="ellipsis", no_wrap=True)

    for pkg in packages:
        style = MANAGER_STYLES.get(pkg.manager, "white")
        icon = MANAGER_ICONS.get(pkg.manager, "  ")
        manager_text = Text(f"{icon} {pkg.manager}", style=style)

        row: list[RenderableType] = [
            pkg.name,
            manager_text,
            pkg.version or "–",
            pkg.category,
        ]
        if show_paths:
            row.append(pkg.path or "–")

        table.add_row(*row)

    console.print()
    console.print(table)

    managed = sum(1 for p in packages if p.is_managed)
    manual = len(packages) - managed
    console.print(
        f"\n[dim]Total: [bold white]{len(packages)}[/bold white] programs  "
        f"│  [bold green]{managed}[/bold green] managed  "
        f"│  [bold yellow]{manual}[/bold yellow] manual[/dim]"
    )
