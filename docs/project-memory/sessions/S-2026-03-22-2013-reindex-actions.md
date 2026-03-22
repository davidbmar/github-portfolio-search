# Session

Session-ID: S-2026-03-22-2013-reindex-actions
Title: Add GitHub Actions reindex workflow and fix API no-index error handling
Date: 2026-03-22
Author: agentB (Claude)

## Goal

Create GitHub Actions workflow for automated reindexing/deployment, a standalone reindex script, and fix API graceful error handling when no index exists (B-008/B-016).

## Context

Sprint 14 agentB tasks. The site is static S3/CloudFront. Need automated reindexing via GitHub Actions and graceful API degradation when no index is present.

## Plan

1. Create `.github/workflows/reindex.yml` with manual dispatch + weekly cron
2. Create `scripts/reindex.sh` standalone script
3. Fix `src/ghps/api.py` to return 200 with empty results when no index exists
4. Add tests for the graceful error handling

## Changes Made

- Created `.github/workflows/reindex.yml`: manual dispatch + weekly cron, index/export/deploy pipeline with S3 sync and CloudFront invalidation, concurrency group
- Created `scripts/reindex.sh`: standalone idempotent script that indexes, exports, and deploys with summary output
- Updated `src/ghps/api.py`: added `_is_no_table_error()` helper to catch OperationalError from both sqlite3 and pysqlite3; /api/search, /api/clusters, /api/repos/{slug} now return `{"results": [], "error": "No index found. Run ghps index first."}` with 200 status instead of 500
- Created `tests/test_api_no_index.py`: 4 tests verifying graceful error handling on all three endpoints

## Decisions Made

- Used `_is_no_table_error()` type-name check instead of catching `sqlite3.OperationalError` directly, because `pysqlite3.dbapi2.OperationalError` doesn't inherit from stdlib `sqlite3.OperationalError`
- reindex.sh skips deploy gracefully if AWS CLI not installed (for local dev without AWS credentials)

## Open Questions

- None

## Links

Commits:
- (see branch agentB-reindex-actions)
