# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.5.2](https://github.com/bini93/pkgview/compare/pkgview-v0.5.1...pkgview-v0.5.2) (2026-05-25)


### Fixed

* handle XML parsing errors in _read_app_plist ([4a85ce2](https://github.com/bini93/pkgview/commit/4a85ce295d01bcd251d7e6c011d0342159ca53ac))

## [0.5.1](https://github.com/bini93/pkgview/compare/pkgview-v0.5.0...pkgview-v0.5.1) (2026-05-25)


### Fixed

* catch CalledProcessError in apk detector ([ac759f0](https://github.com/bini93/pkgview/commit/ac759f06b6b9b3b61d1f2250beef9b2dabf724c9))

## [0.5.0](https://github.com/bini93/pkgview/compare/pkgview-v0.4.0...pkgview-v0.5.0) (2026-05-25)


### Added

* add verbose mode ([#5](https://github.com/bini93/pkgview/issues/5)) ([acf468d](https://github.com/bini93/pkgview/commit/acf468d09eddecceb563ce871e7ff448a6262995))


### Fixed

* add missing 'with' block for actions/checkout in publish workflow ([ae5cc7e](https://github.com/bini93/pkgview/commit/ae5cc7e35a1b87e005812f581ddbb16025f12601))
* allow release-please to create PRs, add contents:read to publish job ([73e230e](https://github.com/bini93/pkgview/commit/73e230e5a6c4aa7ee0fa44f87e2dd1a104926481))
* explicitly set include-component-in-tag to match pkgview-v* tag format ([8a5a1a5](https://github.com/bini93/pkgview/commit/8a5a1a588b4db3029ebc940c0e2e02ada0c821e7))
* remove stray shell fragment from release-please workflow ([2ed78f1](https://github.com/bini93/pkgview/commit/2ed78f18cefcd5bf4ddf1db2352d6c318ce5b007))
* update actions/checkout and actions/setup-python to v6 in workflows ([ce7e321](https://github.com/bini93/pkgview/commit/ce7e3210fddc43e9aba97a879b515ee1197c2368))
* update release-please action to v5 and adjust permissions ([9af0c35](https://github.com/bini93/pkgview/commit/9af0c359e19b6d75a60a76f7e45ff96e1cf7d33f))

## [0.4.0](https://github.com/bini93/pkgview/compare/pkgview-v0.3.1...pkgview-v0.4.0) (2026-05-24)


### Added

* spotlight search ([#3](https://github.com/bini93/pkgview/issues/3)) ([9ebf3cf](https://github.com/bini93/pkgview/commit/9ebf3cfe5e680e24199d5e30f85c9272d9d4d2de))

## [0.3.1](https://github.com/bini93/pkgview/compare/pkgview-v0.3.0...pkgview-v0.3.1) (2026-05-23)


### ### Maintenance

* add issue and pull request templates, CODEOWNERS, CONTRIBUTING, and SECURITY documentation ([77156aa](https://github.com/bini93/pkgview/commit/77156aa9b4e1c21db9a2c45f0de7226b03d9ee67))

## [0.3.0](https://github.com/bini93/pkgview/compare/pkgview-v0.2.0...pkgview-v0.3.0) (2026-05-23)


### Added

* add CI workflow, changelog, and update project metadata ([91ad5d0](https://github.com/bini93/pkgview/commit/91ad5d01427cbeeb0f1f0c329d8ff7506b1bbd62))
* add DEVELOPMENT.md and Makefile for development setup and instructions ([84ae1cd](https://github.com/bini93/pkgview/commit/84ae1cdbfd45747e50ee536547d2636c2eb1cd85))
* add GitHub Actions workflow for publishing to PyPI and update README ([f1ad8ca](https://github.com/bini93/pkgview/commit/f1ad8caffdc67f369281e77d0b58cb40b3fabc59))
* add LICENSE file and update license information in pyproject.toml ([9ae928d](https://github.com/bini93/pkgview/commit/9ae928d31ab8da65e226b09817e2d4e8f4cd19d5))
* add Mamba and Micromamba support, enhance package detection and update README ([5e0d639](https://github.com/bini93/pkgview/commit/5e0d6393de9d7ce2b4f8397c3ea338d25b53b738))
* add release-please configuration and manifest files for automated releases ([e832f03](https://github.com/bini93/pkgview/commit/e832f03a9a9f2ca19bc9387cb7d3d1115580acb4))
* add support for various package managers and enhance detection capabilities ([584a7ba](https://github.com/bini93/pkgview/commit/584a7ba225c6f748e3e2f23051cb71c9ac12207c))
* enhance GitHub Actions workflow with testing steps and update project metadata ([404bdec](https://github.com/bini93/pkgview/commit/404bdec915dadd280c102907d1961d7aac07d5e4))
* initial implementation of pkgview ([bbabe0b](https://github.com/bini93/pkgview/commit/bbabe0b01924efa9a45156d58439a49cc15a4565))
* update release-please workflow to use RELEASE_PLEASE_TOKEN for authentication ([dba1376](https://github.com/bini93/pkgview/commit/dba13764f7322528cca8a6c6f27c1c2f0d4632e4))
* update version to 0.2.0, add new detectors and flags, enhance output formats ([2e202aa](https://github.com/bini93/pkgview/commit/2e202aafa8b5f6813e61e733d7f84eafb075af44))


### Changed

* update type hints and improve error handling in macOS apps detector ([a66cb22](https://github.com/bini93/pkgview/commit/a66cb22e07569257a4f028acff99d57a036598f2))


### Maintenance

* setup release-please and PyPI publishing ([86c45b5](https://github.com/bini93/pkgview/commit/86c45b578b7aea7af007edf3522066822e36e604))

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
