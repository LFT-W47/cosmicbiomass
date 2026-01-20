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

## Jobs

1. **pytest**: installs dev deps and runs the test suite.
2. **build**: creates sdist + wheel in `dist/`.
3. **publish_testpypi**: publishes to TestPyPI on alpha tags.
4. **publish_pypi**: publishes to PyPI on release tags.

## Manual publishing (optional)

From the repo root:

```bash
uv build
uv publish --repository testpypi
uv publish
```
