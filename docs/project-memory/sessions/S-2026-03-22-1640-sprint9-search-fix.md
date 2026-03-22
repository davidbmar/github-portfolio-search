# Session

Session-ID: S-2026-03-22-1640-sprint9-search-fix
Title: Fix multi-word search (F-005) — OR logic with scoring
Date: 2026-03-22
Author: agentA (Claude)

## Goal

Fix F-005: multi-word queries like "voice processing" return 0 results. Switch from AND to OR logic with ranked scoring.

## Context

Sprint 9 task. The client-side SearchEngine in web/js/search.js required ALL query terms to match (AND logic). Recruiters searching "voice processing" got 0 results because no repo contained both "voice" and "processing" as separate indexed terms, even though voice repos are clearly relevant.

## Plan

1. Change scoreRepo() from AND to OR logic — any term matching = include
2. Add exact-phrase bonus for multi-word queries matching verbatim
3. Add multi-term match bonus (more terms = higher rank)
4. Update app.js result count to show "N results for term1, term2" format
5. Substring matching already works via String.includes()

## Changes Made

- web/js/search.js: Rewrote scoreRepo() to use OR logic (matched === 0 returns 0, instead of matched < terms.length). Added exact-phrase bonus (50 pts) when full query appears verbatim. Added multi-term bonus (5 pts per matched term). Extracted termMatches() helper. Passed fullQuery through search() to scoreRepo().
- web/js/app.js: Updated renderSearchResults() header to show "N results for term1, term2" when query has multiple words.

## Decisions Made

- OR logic over AND: recruiters benefit from broader results ranked by relevance rather than strict intersection. Exact-phrase matches still rank first due to 50-point bonus.
- No external fuzzy library: String.includes() already provides substring matching (e.g., "presigned" matches "presignedURL"), which satisfies the fuzzy tolerance requirement without added complexity.

## Open Questions

None.

## Links

Commits:
- (pending)
