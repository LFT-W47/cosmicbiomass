# CI/CD (GitLab)

This project uses GitLab CI with `uv` for testing, building, and publishing.

## Runner

The pipeline targets the HIFIS docker autoscaler runner for fast, portable builds:

- `hifis-linux-small-amd64`
- `dind`
- `hifis`

These tags are set in [.gitlab-ci.yml](../.gitlab-ci.yml).

## Required CI variables

Configure in GitLab project settings → CI/CD → Variables:

- `TESTPYPI_TOKEN` (for TestPyPI uploads)
- `PYPI_TOKEN` (for PyPI uploads)

## Release tags

Publishing is tag-driven:

- **TestPyPI**: `vX.Y.ZaN` (example: `v0.1.0a1`)
- **PyPI**: `vX.Y.Z` (example: `v0.1.0`)

## Tag & publish workflow

1) Work on a feature branch and open a merge request.
2) Ensure CI passes, then merge into `main`.
3) Update version in:
	- [pyproject.toml](../pyproject.toml)
	- [src/cosmicbiomass/__init__.py](../src/cosmicbiomass/__init__.py)
4) Tag on `main`:
	- TestPyPI: `vX.Y.ZaN`
	- PyPI: `vX.Y.Z`
5) Push the tag to trigger publish:
	- `git push origin vX.Y.ZaN`
	- `git push origin vX.Y.Z`

Notes:
- Tags should be created on `main`, not feature branches.
- Use alpha tags only when you want a TestPyPI publish.
- Delete old alpha tags if needed to reduce noise.

## Tag cleanup (recommended)

Keep only a small set of alpha tags (e.g., latest 1–3). Remove old tags locally and remotely.

Examples:

```bash
# Delete local tags
git tag -d v0.1.0a1 v0.1.0a2

# Delete remote tags
git push origin :refs/tags/v0.1.0a1 :refs/tags/v0.1.0a2
```

Tip: avoid creating tags for every CI run. Only tag when you actually want a publish.

## Jobs

1. **lint**: runs `ruff` for fast static checks.
2. **pytest**: installs dev deps and runs the test suite.
3. **build**: creates sdist + wheel in `dist/` and runs `uv publish --dry-run`.
4. **publish_testpypi**: publishes to TestPyPI on alpha tags.
5. **publish_pypi**: publishes to PyPI on release tags.

## Manual publishing (optional)

From the repo root:

```bash
uv build
uv publish --repository testpypi
uv publish
```

## Release checklist

1) Update version in:
	- [pyproject.toml](../pyproject.toml)
	- [src/cosmicbiomass/__init__.py](../src/cosmicbiomass/__init__.py)
2) Ensure `main` is green (lint + tests).
3) Tag on `main`:
	- TestPyPI: `vX.Y.ZaN`
	- PyPI: `vX.Y.Z`
4) Verify TestPyPI install.
5) Tag a stable release when ready.
