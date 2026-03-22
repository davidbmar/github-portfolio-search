# Backlog

Track bugs and feature requests here.

## Naming Convention

- **Bugs:** `B-NNN-short-description.md` (e.g., `B-001-login-crash.md`)
- **Features:** `F-NNN-short-description.md` (e.g., `F-001-dark-mode.md`)

## Template

Each item should include:

```markdown
# B-NNN: Short Title

Status: Open | In Progress | Done
Priority: Critical | High | Medium | Low
Date: YYYY-MM-DD

## Summary
What's the bug/feature?

## Steps to Reproduce (bugs)
1. ...

## Expected Behavior
What should happen?

## Links
- Session: S-YYYY-MM-DD-HHMM-slug
- PR: #123
```

## Current Items

| ID | Title | Status | Priority |
|----|-------|--------|----------|
| B-007 | sprint-run.sh dies during "Collecting project metrics" phase | Open | Medium |
| F-002 | Add progress bar to indexer (tqdm) | Open | Low |
| F-004 | Deploy script should auto-export data before uploading | Open | Medium |
| B-019 | Google OAuth gates entire site — public tier (browse/search) blocked for unauthenticated users | Fixed | High |
| F-009 | Public tier should be accessible without sign-in, auth only for gated features | Fixed | High |

## Archived (Fixed, pre-Sprint 10)

Items below were fixed in sprints 1-9 and are kept for historical reference.

| ID | Title | Fixed In |
|----|-------|----------|
| B-001 | Editable install broken — python3.14 venv site-packages path mismatch | Sprint 2 |
| B-002 | pyproject.toml missing [project.scripts] entry for ghps CLI | Sprint 2 |
| B-003 | sprint-config.sh DEFAULT_TEST_CMD needs venv prefix | Sprint 3 |
| B-004 | test_embeddings.py and test_store.py fail to collect (import errors) | Sprint 3 |
| B-005 | CLI tests fail on missing index edge cases (3 failures in test_cli.py) | Sprint 3 |
| B-006 | test_e2e.py json decode error in CLI search JSON output | Sprint 3 |
| F-001 | Add .env support for GITHUB_TOKEN (python-dotenv) | Sprint 4 |
| F-003 | Add Makefile with install/test/serve/index targets | Sprint 5 |
| B-008 | API /search and /clusters return empty when no index exists (no error msg) | Sprint 6 |
| B-009 | davidbmar.com still shows placeholder — web UI not deployed | Sprint 5 |
| B-010 | davidbmar.com "Could not load data" — data/repos.json is empty (.gitkeep only) | Sprint 6 |
| B-011 | test_web_playwright.py errors — playwright not in dev dependencies | Sprint 7 |
| B-012 | .venv symlinks break after agent merges (too many levels of symbolic links) | Sprint 7 |

## Archived (Fixed, Sprint 10+)

| ID | Title | Fixed In |
|----|-------|----------|
| B-013 | Web search is keyword-only — needs fuzzy/semantic matching | Sprint 10 |
| F-005 | Web search should support multi-word queries | Sprint 10 |
| B-014 | Technology Distribution shows only 3 topics — most repos lack topic tags | Sprint 12 |
| B-015 | AI & Search cluster contains non-AI repos | Sprint 12 |
| F-006 | Auto-tag repos with topics inferred from README content during indexing | Sprint 12 |
| B-016 | API /search and /clusters return 500 when no SQLite index exists | Sprint 14 |
| B-017 | google-auth not installed after sprint merge | Sprint 13 |
| F-007 | Google Sign-In button not visible — needs googleClientId configured | Sprint 13 |
| F-008 | Request Access form should show Google Sign-In when clientId is configured | Sprint 13 |
| B-018 | Mixed content warning — Google avatar loaded over http:// on HTTPS site | Sprint 14 |
