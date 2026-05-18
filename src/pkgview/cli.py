from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Type

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pkgview.detectors.base import Detector
from pkgview.detectors.brew import BrewDetector
from pkgview.detectors.npm import NpmDetector
from pkgview.detectors.pip import PipDetector
from pkgview.detectors.cargo import CargoDetector
from pkgview.detectors.apt import AptDetector
from pkgview.detectors.snap import SnapDetector
from pkgview.detectors.flatpak import FlatpakDetector
from pkgview.detectors.macos_apps import MacOsAppsDetector
from pkgview.detectors.manual import ManualDetector
from pkgview.models import Package
from pkgview.output.table import render_table
from pkgview.output.json_out import render_json

app = typer.Typer(
    help="[bold]pkgview[/bold] – list all installed programs and who manages them.",
    rich_markup_mode="rich",
)

console = Console()

# Detectors that are fully independent (run in parallel)
INDEPENDENT_DETECTORS: List[Type[Detector]] = [
    BrewDetector,
    NpmDetector,
    PipDetector,
    CargoDetector,
    AptDetector,
    SnapDetector,
    FlatpakDetector,
]

VALID_SORT_KEYS = {"name", "manager", "version"}
VALID_MANAGERS = {"brew", "brew-cask", "npm", "pip", "pipx", "cargo", "apt", "snap", "flatpak", "manual"}


@app.command()
def main(
    filter_manager: Optional[str] = typer.Option(
        None,
        "--filter",
        "-f",
        help="Only show programs from a specific manager. "
             "E.g. [cyan]brew[/cyan], [yellow]npm[/yellow], [yellow]manual[/yellow].",
    ),
    as_json: bool = typer.Option(False, "--json", "-j", help="Output raw JSON instead of a table."),
    no_apps: bool = typer.Option(False, "--no-apps", help="Exclude GUI apps (e.g. /Applications on macOS)."),
    sort_by: str = typer.Option(
        "manager",
        "--sort",
        "-s",
        help=f"Sort column: {', '.join(sorted(VALID_SORT_KEYS))}.",
    ),
    no_manual: bool = typer.Option(
        False,
        "--no-manual",
        help="Hide manually installed programs.",
    ),
    show_paths: bool = typer.Option(
        False,
        "--paths",
        "-p",
        help="Add a Path column to the table.",
    ),
) -> None:
    # Input validation
    if filter_manager and filter_manager not in VALID_MANAGERS:
        console.print(
            f"[red]Unknown manager '[bold]{filter_manager}[/bold]'. "
            f"Valid values: {', '.join(sorted(VALID_MANAGERS))}[/red]"
        )
        raise typer.Exit(code=1)

    if sort_by not in VALID_SORT_KEYS:
        console.print(
            f"[red]Unknown sort key '[bold]{sort_by}[/bold]'. "
            f"Valid values: {', '.join(sorted(VALID_SORT_KEYS))}[/red]"
        )
        raise typer.Exit(code=1)

    all_packages: dict[str, Package] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning package managers …", total=None)

        # ── Phase 1: independent detectors in parallel ──────────────────────
        with ThreadPoolExecutor(max_workers=len(INDEPENDENT_DETECTORS)) as executor:
            futures = {
                executor.submit(cls().detect): cls.__name__
                for cls in INDEPENDENT_DETECTORS
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    all_packages.update(result)
                except Exception:
                    pass  # individual detector failures are non-fatal

        # ── Phase 2: GUI apps (macOS only, sequential) ───────────────────────
        if not no_apps:
            progress.update(task, description="Scanning GUI apps …")
            try:
                all_packages.update(MacOsAppsDetector().detect())
            except Exception:
                pass

        # ── Phase 3: manual (needs all managed packages as reference) ────────
        if not no_manual:
            progress.update(task, description="Scanning PATH for manual installs …")
            try:
                manual = ManualDetector(managed=all_packages).detect()
                all_packages.update(manual)
            except Exception:
                pass

    packages = list(all_packages.values())

    # ── Filter ───────────────────────────────────────────────────────────────
    if filter_manager:
        packages = [p for p in packages if p.manager == filter_manager]

    if no_manual:
        packages = [p for p in packages if p.manager != "manual"]

    # ── Sort ─────────────────────────────────────────────────────────────────
    if sort_by == "name":
        packages.sort(key=lambda p: p.name.lower())
    elif sort_by == "version":
        packages.sort(key=lambda p: (p.version or "").lower())
    else:  # default: manager
        packages.sort(key=lambda p: (p.manager, p.name.lower()))

    # ── Render ───────────────────────────────────────────────────────────────
    if as_json:
        print(render_json(packages))
    else:
        render_table(packages, console, show_paths=show_paths)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
