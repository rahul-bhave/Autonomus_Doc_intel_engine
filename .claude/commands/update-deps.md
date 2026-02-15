# Update Dependencies

Sync `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml` dependency lists after a sprint adds new packages.

## Steps

1. Run `pip freeze` in `.venv` to get current installed versions
2. Read `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml`
3. Identify any newly installed packages that are missing from the requirements files
4. Add missing packages with appropriate `>=` version pins and sprint comments
5. Keep the sprint-labeled section grouping (e.g., `# --- Document Parsing (Sprint 1) ---`)
6. Ensure `pyproject.toml` `[project.optional-dependencies].dev` stays in sync with `requirements-dev.txt`
7. Show a summary of what was added/changed

## Rules

- Use `>=` version pins (not `==`) for flexibility
- Add sprint number comments to new entries (e.g., `# Sprint 2`)
- Production deps go in `requirements.txt` + `pyproject.toml [project].dependencies`
- Test/dev-only deps go in `requirements-dev.txt` + `pyproject.toml [project.optional-dependencies].dev`
- Do NOT remove dependencies that are planned for future sprints — only add new ones
- Preserve existing comments and section grouping
