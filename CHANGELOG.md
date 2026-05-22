# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.2.0] – 2026-05-22

### Added

- **14 neue Detektoren:** `asdf`, `apk` (Alpine), `choco` (Windows/Chocolatey), `composer` (PHP global), `conda`, `dnf` (Fedora/RHEL/CentOS), `gem` (Ruby global), `mamba` / `micromamba`, `nix` (Nix-Profil), `nvm` (Node.js-Versionen), `pacman` (Arch Linux), `pyenv` (Python-Versionen), `scoop` (Windows), `winget` (Windows Package Manager)
- `--outdated` / `-o` Flag: prüft bei jedem Paketmanager auf verfügbare Updates und hebt veraltete Pakete hervor
- `--export` / `-e` Flag: speichert Snapshot in Datei; Format wird automatisch anhand der Endung erkannt (`.csv` → CSV, sonst JSON)
- CSV-Ausgabe (`render_csv`) als neues Ausgabeformat
- `outdated` und `latest_version` Felder im `Package`-Modell
- `check_outdated`-Unterstützung in: brew, pip, npm, snap, gem, nix, flatpak, dnf, scoop, conda, mamba
- Tests für alle neuen Detektoren (inkl. Mamba/Micromamba)

### Changed

- Tabellenausgabe zeigt optional die Spalten `Latest Version` und `Outdated` (bei `--outdated`)
- JSON- und CSV-Export enthalten `outdated` und `latest_version`
- `conda`-Detektor auf reine Conda-Environments beschränkt; Mamba/Micromamba in eigenen Detektor ausgelagert
- `npm`-Detektor unterstützt jetzt `check_outdated`
- `pip`-Detektor unterstützt jetzt `check_outdated`
- `snap`-Detektor zeigt verfügbare Updates an

---

## [0.1.0] – 2026-05-19

### Added

- Detects installed programs from: brew, brew-cask, npm (global), pip, pipx, cargo, apt, snap, flatpak
- Scans `/Applications` and `~/Applications` on macOS for GUI apps
- Marks everything not tracked by a known package manager as `manual`
- All detectors run in parallel for fast results
- Color-coded table output via `rich`
- JSON output with `--json`
- Filter by manager with `--filter`
- Sort by name, manager, or version with `--sort`
- `--no-apps`, `--no-manual`, `--paths` flags
- `pkgview --version` / `-V`
