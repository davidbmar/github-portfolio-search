# B-022: narrate pipeline re-matures/re-renders a published theme on a second run

Status: Open
Priority: Medium
Date: 2026-07-12

## Summary

Two tests in `tests/narrate/test_pipeline.py` fail:
`test_run_end_to_end` and `test_published_theme_not_rerendered_on_second_run`.
On a second `run(...)` over the same PRs, `out2["themes_matured"]` is `1` where
the test expects `0` — i.e. an already-published theme is matured/re-rendered
again instead of being skipped. This contradicts the slug-pinning / idempotency
guarantee the narrate pipeline is supposed to hold across repeated runs.

## Steps to Reproduce

```bash
.venv/bin/python -m pytest \
  tests/narrate/test_pipeline.py::test_run_end_to_end \
  tests/narrate/test_pipeline.py::test_published_theme_not_rerendered_on_second_run -q
```

## Expected Behavior

A second run over the same input produces `themes_matured == 0` — published
themes are recognized as already-done and are not re-rendered.

## Notes

- **Pre-existing / unrelated to reuse-aware building.** Confirmed failing
  identically at commit `b099e394` (the main-merge commit, before any reuse work).
  Discovered while running the full suite as the Task 6 regression gate for
  S-2026-07-12-2332-reuse-aware-building.
- Both tests run in ~0.07s with fakes (no model/network) — pure pipeline logic,
  so this is a deterministic logic bug, not a flaky/env failure.
- Likely area: the "already published" / maturation-state check in
  `src/ghps/narrate/pipeline.py::run`. Relates to the committed slug-pinning
  registry idempotency.

## Links
- Session: S-2026-07-12-2332-reuse-aware-building (discovered here)
