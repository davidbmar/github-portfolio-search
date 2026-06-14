# B-021 — gen-docs should respect the GitHub rate limit (backoff instead of failing)

**Type:** Bug
**Status:** Open
**Priority:** Medium
**Found:** S-2026-06-13-2215-l0-project-docs (2026-06-13)

## Summary

A full `ghps gen-docs` run over ~137 repos exhausted the GitHub core rate limit
(5000/hr) mid-batch. Every subsequent repo failed with `403 — API rate limit
exceeded` (`x-ratelimit-remaining: 0`). 62 repos generated, 69 failed in one run.

Two contributing factors:
1. **Pre-fix `fetch_top_files` downloaded every matching blob** (hundreds of Blob
   API calls per large repo). Fixed in this session — `max_files` cap + reusing
   the known `default_branch` — which cuts per-repo calls from ~30+ to ~12.
2. **No rate-limit awareness.** A 403/limit hit becomes a per-repo
   `RecordGenerationError` (the repo lands in `failed[]`) rather than the run
   pausing until the limit resets.

## Impact

A single full-portfolio run can't finish in one pass; it needs a manual gap-fill
re-run after the hourly reset. The scheduled Action (`--stale`) is unaffected in
practice (few repos per run), but a `--force` refresh of all repos will hit this.

## Fix

In `github_client`, detect `x-ratelimit-remaining: 0` (or a 403 with the rate-limit
message) and either:
- sleep until `x-ratelimit-reset`, then retry (bounded), or
- raise a distinct `RateLimitError` that `generate_all` catches to stop early with
  a clear "resumes after HH:MM" message instead of marking dozens of repos failed.

Also consider a small inter-repo delay and conditional requests (ETag) to stretch
the budget. With the `max_files` cap, a full ~137-repo run now fits in one hourly
window (~2000 calls), so this is robustness, not a hard blocker.

## Workaround (current)

Re-run `ghps gen-docs` after the reset — idempotent, so it only generates the
repos still missing a record.
