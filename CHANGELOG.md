# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
