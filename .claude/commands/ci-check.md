# CI/CD Check

Check the status of GitHub Actions CI pipeline and troubleshoot failures.

## Steps

1. Run `gh run list --limit 5` to show recent CI runs
2. If the latest run failed, run `gh run view <run-id> --log-failed` to get failure details
3. Analyze the failure:
   - **Test failure**: identify the failing test and suggest a fix
   - **Dependency install failure**: check `requirements.txt` / `requirements-dev.txt` for issues
   - **Cache miss / slow build**: check if HuggingFace model cache key changed
4. If all green, report the status and last passing commit

## Troubleshooting Tips

- CI runs on `ubuntu-latest` (Linux) — no Windows symlink workaround needed there
- The `docling[rapidocr]` install is heavy (~500MB); pip caching keeps subsequent runs fast
- HuggingFace models (~200MB ONNX) are cached under `~/.cache/huggingface/hub`
- Tests run with `PYTHONPATH=. pytest tests/ -v`
- Workflow file: `.github/workflows/ci.yml`
