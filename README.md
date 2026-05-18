# pkgview

A CLI tool that lists all programs installed on your system and shows whether each one is managed by a package manager (brew, npm, pip, cargo, apt, snap, flatpak) or was installed manually — and therefore needs to be maintained by you.

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┓
┃ Name                          ┃ Manager        ┃ Version    ┃ Type  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━┩
│ git                           │ 🍺 brew        │ 2.54.0     │ cli   │
│ k9s                           │ 🍺 brew        │ 0.50.18    │ cli   │
│ firebase-tools                │ 📦 npm         │ 15.8.0     │ cli   │
│ black                         │ 🐍 pip         │ 24.3.0     │ cli   │
│ docker                        │ ⚠  manual      │ –          │ cli   │
│ code                          │ ⚠  manual      │ –          │ cli   │
└───────────────────────────────┴────────────────┴────────────┴───────┘

Total: 75 programs  │  57 managed  │  18 manual
```

## Features

- Detects programs from: **brew**, **brew-cask**, **npm** (global), **pip**, **pipx**, **cargo**, **apt**, **snap**, **flatpak**
- Scans `/Applications` and `~/Applications` on macOS for GUI apps
- Marks everything not tracked by a package manager as `manual`
- Correctly ignores macOS/Linux system binaries (`/bin`, `/usr/bin`, etc.)
- Correctly ignores Homebrew sub-binaries (e.g. `dart` from the `flutter` cask)
- All detectors run **in parallel** — fast even with many package managers installed
- Outputs a color-coded table or raw JSON (`--json`)

## Requirements

- **Python 3.9+** (already present on macOS and most Linux distros)
- No other runtime required

## Installation

### Option A – editable install for development

```bash
git clone https://github.com/yourname/pgkview.git
cd pgkview
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

The `pkgview` command is now available inside the venv.

### Option B – install directly with pip (once published)

```bash
pip install pkgview
```

### Option C – with uv (if available)

```bash
uv tool install pkgview
```

## Usage

```
pkgview [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--filter TEXT` | `-f` | – | Show only programs from one manager.<br>Values: `brew`, `brew-cask`, `npm`, `pip`, `pipx`, `cargo`, `apt`, `snap`, `flatpak`, `manual` |
| `--sort TEXT` | `-s` | `manager` | Sort column: `name`, `manager`, `version` |
| `--json` | `-j` | off | Output raw JSON instead of a table |
| `--paths` | `-p` | off | Add a Path column to the table |
| `--no-apps` | – | off | Exclude GUI apps (`/Applications`) |
| `--no-manual` | – | off | Hide manually installed programs |
| `--help` | – | – | Show help and exit |

### Examples

```bash
# List everything, sorted by manager (default)
pkgview

# Show only manually installed programs (needs attention)
pkgview --filter manual

# Show only Homebrew formulas, sorted by name
pkgview --filter brew --sort name

# Show with full paths
pkgview --paths

# Export as JSON (e.g. for backups or scripting)
pkgview --json > programs.json

# Hide noise: no system apps, no manual tools
pkgview --no-apps --no-manual
```

## Supported Package Managers

| Icon | Manager | Platform | Detection method |
|------|---------|----------|-----------------|
| 🍺 | `brew` | macOS, Linux | `brew list --versions` |
| 🍺 | `brew-cask` | macOS | `brew list --cask` |
| 📦 | `npm` | macOS, Linux | `npm list -g --depth=0 --json` |
| 🐍 | `pip` | macOS, Linux | `pip list --format=json` |
| 🐍 | `pipx` | macOS, Linux | `pipx list --json` |
| 🦀 | `cargo` | macOS, Linux | `cargo install --list` |
| 🐧 | `apt` | Linux (Debian/Ubuntu) | `apt-mark showmanual` |
| 🐧 | `snap` | Linux | `snap list` |
| 🐧 | `flatpak` | Linux | `flatpak list --app` |
| ⚠ | `manual` | macOS, Linux | PATH scan (cross-referenced) |

Missing package managers are silently skipped — no errors.

## Project Structure

```
pgkview/
├── pyproject.toml              ← packaging config, entry point: pkgview
├── src/
│   └── pkgview/
│       ├── cli.py              ← typer app, all flags, parallel orchestration
│       ├── models.py           ← Package dataclass
│       ├── detectors/
│       │   ├── base.py         ← abstract Detector class
│       │   ├── brew.py
│       │   ├── npm.py
│       │   ├── pip.py
│       │   ├── cargo.py
│       │   ├── apt.py
│       │   ├── snap.py
│       │   ├── flatpak.py
│       │   ├── macos_apps.py   ← scans /Applications
│       │   └── manual.py       ← PATH scan, marks unknowns as "manual"
│       └── output/
│           ├── table.py        ← rich table renderer
│           └── json_out.py     ← JSON renderer
└── PLAN.md                     ← architecture decisions and future roadmap
```

## Adding a New Detector

Adding support for a new package manager takes ~30 lines. Here is a minimal example:

```python
# src/pkgview/detectors/my_manager.py
from __future__ import annotations

import subprocess
from typing import Dict

from pkgview.detectors.base import Detector
from pkgview.models import Package


class MyManagerDetector(Detector):
    @property
    def name(self) -> str:
        return "my_manager"

    def detect(self) -> Dict[str, Package]:
        packages: Dict[str, Package] = {}
        try:
            result = subprocess.run(
                ["my_manager", "list"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return {}
            for line in result.stdout.splitlines():
                name = line.strip()
                if name:
                    packages[name] = Package(name=name, manager="my_manager")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return packages
```

Then register it in `src/pkgview/cli.py`:

```python
from pkgview.detectors.my_manager import MyManagerDetector

INDEPENDENT_DETECTORS = [
    ...,
    MyManagerDetector,   # ← add here
]
```

And add a color/icon in `src/pkgview/output/table.py`:

```python
MANAGER_STYLES["my_manager"] = "bold green"
MANAGER_ICONS["my_manager"]  = "🔧"
```

Also add the name to `VALID_MANAGERS` in `cli.py` so `--filter my_manager` works.

## Development

```bash
# Install in editable mode
pip install -e .

# Run directly
pkgview --help

# Quick test (no GUI apps, sorted by name)
pkgview --no-apps --sort name
```

No test suite yet — contributions welcome.

## Roadmap

- [ ] `pkgview --outdated` — highlight packages with available updates
- [ ] `pkgview --export` — save snapshot as JSON/CSV for system backups
- [ ] nvm / asdf / pyenv detector
- [ ] Windows support (winget, scoop, chocolatey)
- [ ] TUI mode with [Textual](https://textual.textualize.io/) (`pkgview --tui`)
- [ ] Docker Desktop, VS Code extension detection

## License

MIT
