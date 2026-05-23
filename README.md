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

- Detects programs from: **brew**, **brew-cask**, **npm** (global), **pip**, **pipx**, **cargo**, **apt**, **snap**, **flatpak**, **conda** / **mamba**, **pacman**, **dnf** / **yum**, **apk**, **nix**, **gem**, **composer**, **winget**, **scoop**, **chocolatey**, **nvm**, **asdf**, **pyenv**
- Scans `/Applications` and `~/Applications` on macOS for GUI apps
- Marks everything not tracked by a package manager as `manual`
- Correctly ignores macOS/Linux system binaries (`/bin`, `/usr/bin`, etc.)
- Correctly ignores Homebrew sub-binaries (e.g. `dart` from the `flutter` cask)
- All detectors run **in parallel** — fast even with many package managers installed
- Outputs a color-coded table or raw JSON (`--json`)
- Check for available updates with `--outdated`
- Export snapshots to JSON or CSV with `--export`

## Requirements

- **Python 3.9+** (already present on macOS and most Linux distros)
- No other runtime required

## Installation

### Recommended – install with pipx (no venv needed)

[pipx](https://pipx.pypa.io) installs CLI tools in an isolated environment automatically.

```bash
# Install pipx once (macOS)
brew install pipx
pipx ensurepath

# Install pkgview directly from GitHub
pipx install git+https://github.com/yourname/pkgview.git
```

The `pkgview` command is immediately available system-wide.

**Update to the latest version:**

```bash
pipx upgrade pkgview
```

### Alternative – with pip (once published on PyPI)

```bash
pip install pkgview
# or
uv tool install pkgview
```

> For development setup, project structure, and contribution guidelines, see [DEVELOPMENT.md](DEVELOPMENT.md).

## Usage

```
pkgview [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--filter TEXT` | `-f` | – | Show only programs from one manager.<br>Values: `brew`, `brew-cask`, `npm`, `pip`, `pipx`, `cargo`, `apt`, `snap`, `flatpak`, `conda`, `mamba`, `pacman`, `yay`, `dnf`, `yum`, `zypper`, `apk`, `nix`, `gem`, `composer`, `winget`, `scoop`, `chocolatey`, `nvm`, `asdf`, `pyenv`, `manual` |
| `--sort TEXT` | `-s` | `manager` | Sort column: `name`, `manager`, `version` |
| `--json` | `-j` | off | Output raw JSON instead of a table |
| `--paths` | `-p` | off | Add a Path column to the table |
| `--outdated` | `-o` | off | Check for available updates; highlight outdated packages in red |
| `--export PATH` | `-e` | – | Save snapshot to file (`.csv` → CSV, everything else → JSON) |
| `--no-apps` | – | off | Exclude GUI apps (`/Applications`) |
| `--no-manual` | – | off | Hide manually installed programs |
| `--version` | `-V` | – | Show version and exit |
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
| 🐍 | `conda` / `mamba` | macOS, Linux | `conda list --json` / `mamba list --json` |
| 🐧 | `pacman` | Linux (Arch) | `pacman -Qe` |
| 🐧 | `dnf` / `yum` | Linux (Fedora/RHEL) | `dnf repoquery --userinstalled` |
| 🐧 | `apk` | Linux (Alpine) | `apk list --installed` |
| ❄  | `nix` | macOS, Linux | `nix-env -q` |
| 💎 | `gem` | macOS, Linux | `gem list --no-verbose` |
| 🎵 | `composer` | macOS, Linux | `composer global show --format=json` |
| 🪟 | `winget` | Windows | `winget list --source winget` |
| 🪟 | `scoop` | Windows | `scoop list` |
| 🍫 | `chocolatey` | Windows | `choco list --local-only` |
| 🟩 | `nvm` | macOS, Linux | scans `~/.nvm/versions/node/` |
| 🔧 | `asdf` | macOS, Linux | scans `~/.asdf/installs/` |
| 🐍 | `pyenv` | macOS, Linux | scans `~/.pyenv/versions/` |
| ⚠  | `manual` | macOS, Linux | PATH scan (cross-referenced) |

Missing package managers are silently skipped — no errors.

## Roadmap

- [x] `pkgview --outdated` — highlight packages with available updates
- [x] `pkgview --export` — save snapshot as JSON/CSV for system backups
- [x] nvm / asdf / pyenv detector
- [x] Windows support (winget, scoop, chocolatey)
- [x] conda / mamba detector
- [x] pacman / dnf / apk / nix / gem / composer detectors
- [ ] TUI mode with [Textual](https://textual.textualize.io/) (`pkgview --tui`)
- [ ] Docker Desktop, VS Code extension detection
- [ ] Publish to [PyPI](https://pypi.org) — `pipx install pkgview` without GitHub URL *(workflow ready, pending first release)*
- [ ] [Homebrew Tap](https://docs.brew.sh/Tap-Migrating-to-a-New-Package) — `brew install yourname/tap/pkgview` *(formula template in `packaging/homebrew/`)*

## License

GPL-3.0-or-later — see [LICENSE](LICENSE) for details.
