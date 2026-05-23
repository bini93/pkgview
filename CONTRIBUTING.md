# Contributing to pkgview

Thank you for your interest in contributing! This guide explains the process.

## Before You Start

- Check the [open issues](https://github.com/bini93/pkgview/issues) to avoid duplicate work.
- For larger changes, **open an issue first** to discuss the approach before writing code.

## Workflow

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-new-detector
   ```
2. Make your changes and add tests.
3. Run the test suite locally — it must pass in full:
   ```bash
   make test
   ```
4. Open a **Pull Request** against `main`. Fill out the PR template completely.
5. At least **one maintainer review** is required before merging.
6. The PR is merged by a maintainer (not the author).

## Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feat/` | New feature or detector |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Tooling, CI, dependencies |
| `refactor/` | Code cleanup without behaviour change |

## Adding a New Package-Manager Detector

1. Create `src/pkgview/detectors/<name>.py` — inherit from `BaseDetector`.
2. Implement `is_available()` and `detect() -> list[Package]`.
3. Register the detector in `src/pkgview/detectors/__init__.py`.
4. Add tests in `tests/test_detectors.py`.
5. Update `README.md` — add the manager to the supported-managers table.

## Code Style

- Python 3.9+, no external runtime dependencies beyond what is in `pyproject.toml`.
- Format with `ruff format` and lint with `ruff check` before committing.
- Type annotations are encouraged but not enforced for existing code.

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(brew): add version pinning support
fix(npm): handle missing global prefix gracefully
docs: add detector tutorial to CONTRIBUTING
```

This drives the automated changelog and version bumps via `release-please`.

## Reporting Bugs

Use the **Bug Report** issue template. Include:
- OS and version
- `pkgview --version` output
- Full command and error output

## Proposing Features

Use the **Feature Request** issue template. Explain the use case, not just the solution.

## Code of Conduct

Be respectful. Constructive criticism is welcome; personal attacks are not.
