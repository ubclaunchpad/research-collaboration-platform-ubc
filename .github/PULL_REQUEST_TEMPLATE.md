**General Checklist:**

- [ ] Code formatted using `ruff format .`
- [ ] Unused imports removed (e.g., using `ruff check --select F401 --fix .`)
- [ ] All dependency changes reflected in `pyproject.toml` and `uv.lock` are up-to-date
- [ ] Patch version updated in `src/app/__version__.py`
- [ ] `CHANGELOG.md` updated with changes under appropriate version
- [ ] Code docs are up to date
- [ ] Testing instructions have been added in the repo or in this PR

**Additional Checklist for Release PRs:**

- [ ] This PR is for a release
- [ ] Minor version number incremented appropriately