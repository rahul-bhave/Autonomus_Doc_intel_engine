# Finish Sprint

Run after completing a sprint to update all tracking files and verify everything is green.

## Steps

1. Run full test suite: `PYTHONPATH=. .venv/Scripts/pytest tests/ -v`
2. Verify all tests pass (zero failures)
3. Update `CLAUDE.md`:
   - Mark current sprint as `✅ DONE`
   - Mark next sprint as `⬜ NEXT`
   - Update "Installed in .venv" section
   - Update "File Map" with new files created this sprint
   - Replace sprint-specific "Next Steps" section with the next sprint's plan
4. Update auto memory `MEMORY.md`:
   - Update sprint status with test counts
   - Update dependencies list
   - Add any new key files
5. Run `/project:update-deps` to sync requirements files
6. Show summary: sprint completed, test count, files changed
