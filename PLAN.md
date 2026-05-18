# pkgview – Erkenntnisse & Implementierungsplan

## Problem

Auf modernen Systemen werden Programme über viele verschiedene Wege installiert:
- Paketmanager (brew, npm, pip, apt, snap, flatpak, cargo …)
- Manuell heruntergeladen und in den PATH gelegt
- Als GUI-App installiert (z. B. `/Applications` auf macOS)

Es gibt kein einziges Tool das eine einheitliche Übersicht gibt. Das führt dazu, dass
manuell installierte Programme veralten und nicht gewartet werden.

---

## Technologie-Entscheidung

**Sprache: Python 3.9+**

| Kriterium        | Python        | Go            | Rust          |
|------------------|---------------|---------------|---------------|
| Kleiner Code     | ✅ (10 KB)    | ❌ (~10 MB Binary) | ❌ (~15 MB Binary) |
| Runtime nötig    | macOS/Linux haben Python bereits | ❌ nein (gut) | ❌ nein (gut) |
| Startup-Zeit     | ~300 ms       | ~20 ms        | ~5 ms         |
| Wartbarkeit      | ✅✅ sehr hoch | ✅ mittel     | ⚠️ hoch (Lernkurve) |
| Cross-Platform   | ✅            | ✅✅ sehr gut | ✅✅ gut      |
| Späteres TUI/UI  | ✅ (Textual)  | ✅✅ (bubbletea) | ✅✅ (ratatui) |

**Begründung**: Python ist auf macOS und Linux bereits vorhanden (kein Installation-Blocker),
der Quell-Code ist minimal und sehr gut lesbar, und die 300 ms Startzeit spielen keine Rolle
für ein Tool das selbst mehrere Sekunden braucht um alle Package Manager zu befragen.

**Stack:**
- `typer` – CLI-Argument-Parsing mit Type-Annotations
- `rich` – Farbige Tabellen, Progress-Spinner
- `uv` – Modernes, schnelles Python-Packaging (kein pip/venv Chaos)

---

## Architektur

### Kernprinzip: Plugin-Detektoren

Jeder Package Manager ist ein eigenständiger **Detector** der von einer gemeinsamen
Basisklasse erbt. Das ermöglicht:
- Einfaches Hinzufügen neuer Package Manager
- Alle Detektoren laufen **parallel** (ThreadPoolExecutor)
- Jeder Detektor schlägt still fehl wenn der Package Manager nicht installiert ist

### Datenfluss

```
PARALLEL:
  BrewDetector     → {"git": Package(name="git", manager="brew"), ...}
  NpmDetector      → {"prettier": Package(...), ...}
  PipDetector      → {"black": Package(...), ...}
  CargoDetector    → {"ripgrep": Package(...), ...}
  AptDetector      → (Linux)
  SnapDetector     → (Linux)
  FlatpakDetector  → (Linux)

DANN:
  MacOsAppsDetector → {"Firefox": Package(category="app"), ...}

DANN (braucht alle anderen als Referenz):
  ManualDetector   → scannt $PATH, markiert alles NICHT in obigen Sets als "manual"

OUTPUT:
  render_table()   → farbige Rich-Tabelle
  render_json()    → JSON (--json Flag)
```

### Projektstruktur

```
pgkview/
├── PLAN.md
├── pyproject.toml              ← uv/hatch Packaging, Entry Point: pkgview
├── src/
│   └── pkgview/
│       ├── __init__.py
│       ├── cli.py              ← typer App (Flags: --filter, --json, --no-apps, --sort)
│       ├── models.py           ← Package dataclass
│       ├── detectors/
│       │   ├── __init__.py
│       │   ├── base.py         ← Abstract Detector ABC
│       │   ├── brew.py         ← brew list --formula + --cask
│       │   ├── npm.py          ← npm list -g --depth=0 --json
│       │   ├── pip.py          ← pip list + pipx list --json
│       │   ├── cargo.py        ← cargo install --list
│       │   ├── apt.py          ← apt-mark showmanual (Linux)
│       │   ├── snap.py         ← snap list (Linux)
│       │   ├── flatpak.py      ← flatpak list --app (Linux)
│       │   ├── macos_apps.py   ← /Applications + ~/Applications
│       │   └── manual.py       ← PATH scan, Rest = "manual"
│       └── output/
│           ├── __init__.py
│           ├── table.py        ← rich Table mit Farbkodierung
│           └── json_out.py     ← JSON-Ausgabe
```

---

## Datenmodell

```python
@dataclass
class Package:
    name: str
    manager: str     # "brew" | "brew-cask" | "npm" | "pip" | "pipx" |
                     # "apt" | "snap" | "flatpak" | "cargo" | "manual"
    version: str | None
    path: str | None
    category: str    # "cli" | "app"
```

---

## CLI Interface

```bash
pkgview                          # Alle Programme als Tabelle
pkgview --filter brew            # Nur brew-Pakete
pkgview --filter manual          # Nur manuell installierte
pkgview --json                   # JSON-Ausgabe
pkgview --no-apps                # GUI-Apps ausschließen
pkgview --sort name              # Nach Name sortieren (default: manager)
pkgview --no-manual              # Manuelle ausblenden
```

---

## Erkannte Edge Cases

| Problem | Lösung |
|---------|--------|
| Apple Silicon vs Intel | Beide Pfade prüfen (`/opt/homebrew` + `/usr/local`) |
| nvm (Node Version Manager) | `npm root -g` zur Laufzeit auflösen |
| Gleicher Name in mehreren PMs | Letzter Detektor gewinnt (brew hat Priorität via Update-Reihenfolge) |
| Symlinks im PATH | `entry.resolve()` für echten Pfad |
| Detektor nicht vorhanden | `FileNotFoundError` → leeres Dict, kein Crash |
| `brew list` dauert lang | Timeout 30s, parallel zu anderen Detektoren |

---

## Erweiterbarkeit (späteres UI)

Die Trennung Detector → Model → Presenter macht es trivial, später:
- `output/tui.py` mit [Textual](https://textual.textualize.io/) hinzuzufügen
- Eine REST-API zu bauen die die Detektoren aufruft
- Einen Daemon zu bauen der den Zustand cached

Ein neuer Detector braucht nur:
1. Datei in `detectors/` anlegen
2. Von `Detector` erben
3. `detect() -> dict[str, Package]` implementieren
4. In `cli.py` zur `INDEPENDENT_DETECTORS` Liste hinzufügen

---

## Was NICHT implementiert wird (Scope)

- ❌ Windows (Phase 3)
- ❌ Update-Prüfung (z. B. `brew outdated`)
- ❌ Dependency-Tracking
- ❌ Auto-Update
- ❌ Entfernen/Installieren von Paketen

---

## Phase 2 Ideen (nach erstem Release)

- `pkgview --outdated` – zeigt veraltete Pakete
- `pkgview --export` – exportiert die Liste als JSON/CSV für Backups
- TUI mit Textual: interaktive Tabelle, sortierbar, filterbar
- macOS: Spotlight-Integration für noch bessere App-Erkennung
