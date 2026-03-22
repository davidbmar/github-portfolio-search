# Session

Session-ID: S-2026-03-22-1612-search-relevance-tuning
Title: Sprint 8 — Search relevance tuning with title and recency boosting
Date: 2026-03-22
Author: agentA

## Goal

Improve search result quality by adding title boosting and recency factors to the semantic search engine.

## Context

Sprint 8 agentA brief: search relevance tuning. The search engine currently ranks results purely by cosine similarity. Real-world queries like "presigned URL" should rank the S3-presignedURL repo first, and recently updated repos should be preferred over stale ones.

## Plan

1. Add title boosting (2x) and recency boosting (1.2x/1.0x/0.8x) to search.py
2. Add last_indexed timestamp and relevance-based sorting to export.py
3. Add tests for both boosting mechanisms
4. Update existing tests to account for new score multipliers

## Changes Made

- `src/ghps/search.py`: Added `_title_boost()` (2x when query terms appear in repo name) and `_recency_boost()` (1.2x < 6mo, 1.0x < 1yr, 0.8x older). Applied both multipliers to search scores.
- `src/ghps/export.py`: Added `last_indexed` ISO timestamp to repos.json. Changed sort order from alphabetical to relevance score (stars + recency). Added `relevance_score` field.
- `tests/test_search.py`: Added TestTitleBoosting (4 tests) and TestRecencyBoosting (5 tests). Updated existing score assertions to account for recency multiplier. Updated mock helper to provide `updated_at` metadata.
- `tests/test_export.py`: Changed `test_repos_sorted_by_name` to `test_repos_sorted_by_relevance_score`.

## Decisions Made

- Title boost uses substring matching (case-insensitive) rather than exact word match — catches "presigned" in "S3-presignedURL"
- Recency boost uses 182/365 day thresholds (6mo/1yr)
- Export relevance score = stars + recency_boost (simple additive formula)
- Reused `_recency_boost` from search.py in export.py to keep logic consistent

## Open Questions

- Pre-existing test ordering issue: CLI tests in test_search.py corrupt sys.modules, causing export fixture tests to fail when run in same session. Not introduced by this change.

## Links

Commits:
- (pending)
