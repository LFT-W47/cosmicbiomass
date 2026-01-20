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
