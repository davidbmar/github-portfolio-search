# Session

Session-ID: S-2026-03-22-2013-sprint14-data-pipeline
Title: Sprint 14 - Data pipeline improvements (indexed_at, dry-run, freshness)
Date: 2026-03-22
Author: agentC

## Goal

Improve indexing reliability and add metadata for freshness tracking as part of Sprint 14.

## Context

Sprint 14 brief assigns agentC to improve the data pipeline: add indexed_at timestamps, dry-run mode, error handling, and freshness labels to search results.

## Plan

1. Add `indexed_at` column to repos table in store.py
2. Auto-populate indexed_at on insert/update, add get_index_stats()
3. Add --dry-run flag and error handling to indexer.py
4. Add freshness field to search results in search.py
5. Write comprehensive tests

## Changes Made

- `src/ghps/store.py`: Added `indexed_at TEXT` column to repos table schema, auto-populated during `add_repo()`, added `get_index_stats()` method
- `src/ghps/indexer.py`: Added `dry_run` parameter to `index_repos()` and `index_user()`, wrapped per-repo indexing in try/except for error resilience, added summary logging (indexed/failed/skipped counts), set `indexed_at` timestamp on repo metadata
- `src/ghps/search.py`: Added `indexed_at` and `freshness` fields to `SearchResult` dataclass, added `_freshness_label()` function (today/this_week/this_month/stale), fetches `indexed_at` from repos table during search
- `tests/test_data_pipeline.py`: New test file with 14 tests covering indexed_at storage, get_index_stats(), freshness labels, dry-run mode, and error handling
- `tests/test_search.py`: Updated mock store helper to include indexed_at in metadata rows

## Decisions Made

- `indexed_at` defaults to current UTC time if not explicitly provided, ensuring backward compatibility
- Freshness labels use indexed_at (not updated_at) since they reflect data freshness, not repo activity
- Dry-run skips embedding generation (expensive) and store writes, but still counts chunks
- Error handling logs with exc_info=True for debugging while continuing to next repo

## Open Questions

- None

## Links

Commits:
- See branch agentC-data-pipeline
