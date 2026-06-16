# Code Style & Tooling

How code in this repo is formatted, linted, typed, and tested. `pyproject.toml` is the source
of truth for all tool configuration — this page states the rules; it does not duplicate the
settings.

## Rules

- Target **Python 3.10+**. Use modern idioms: f-strings, `pathlib`, and type hints.
- **Type-hint every public function.** `mypy` runs in strict mode (`disallow_untyped_defs`,
  `disallow_incomplete_defs`, `disallow_any_generics`, etc.). Run `uv run mypy src`.
- **Format with `black`** (line length 88): `uv run black .`.
- **Lint with `ruff`** (rule sets `E,W,F,I,B,C4,UP`): `uv run ruff check .`. `ruff` also owns
  import sorting (isort/`I`) — don't hand-order imports against it.
- **Test with `pytest`**: `uv run pytest`. Add tests for new features and keep coverage **above
  85%** (coverage is wired into `addopts`). Use the markers defined in `pyproject.toml`
  (`unit`, `integration`, `slow`, `mock`).
- Keep the package importable through `src/cosmicbiomass/__init__.py`: add new public symbols to
  `__all__`, and keep new code under the `src/` layout.
- Run `uv run ruff check .` and `uv run pytest` before submitting changes (CI runs both).

## Examples

### Do

```python
from pathlib import Path

def load_window(path: Path, radius: float = 200.0) -> "xr.Dataset":
    """Load a data window; fully type-hinted, f-strings, pathlib."""
    logger.info(f"loading {path} at radius={radius}")
    ...
```

### Don't

```python
def load_window(path, radius=200):        # missing type hints -> mypy strict fails
    print("loading " + str(path))         # use logging + f-strings, not print/concatenation
```

## Notes

- **Releasing** (version bumps, tags, CHANGELOG) is documented separately in
  [`../../CI_CD.md`](../../CI_CD.md). Remember the version lives in **two** places:
  `pyproject.toml` and `src/cosmicbiomass/__init__.py`.
- **Dependency versions:** track minimum supported versions and avoid strict upper bounds; pin a
  specific package only when a breaking change appears (see the repo `README.md`).
