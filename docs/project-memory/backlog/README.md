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
| B-001 | Editable install broken — python3.14 venv site-packages path mismatch | Fixed | Critical |
| B-002 | pyproject.toml missing [project.scripts] entry for ghps CLI | Fixed | High |
| B-003 | sprint-config.sh DEFAULT_TEST_CMD needs venv prefix | Fixed | High |
| B-004 | test_embeddings.py and test_store.py fail to collect (import errors) | Fixed | High |
| B-005 | CLI tests fail on missing index edge cases (3 failures in test_cli.py) | Fixed | High |
| B-006 | test_e2e.py json decode error in CLI search JSON output | Fixed | High |
| B-007 | sprint-run.sh dies during "Collecting project metrics" phase | Open | Medium |
| F-001 | Add .env support for GITHUB_TOKEN (python-dotenv) | Fixed | Medium |
| F-002 | Add progress bar to indexer (tqdm) | Open | Low |
| F-003 | Add Makefile with install/test/serve/index targets | Fixed | Medium |
| B-008 | API /search and /clusters return empty when no index exists (no error msg) | Open | Medium |
| B-009 | davidbmar.com still shows placeholder — web UI not deployed | Fixed | High |
| B-010 | davidbmar.com "Could not load data" — data/repos.json is empty (.gitkeep only) | Fixed | Critical |
| B-011 | test_web_playwright.py errors — playwright not in dev dependencies | Fixed | High |
| B-012 | .venv symlinks break after agent merges (too many levels of symbolic links) | Fixed | High |
| B-013 | Web search is keyword-only — "voice processing" returns 0 results, needs fuzzy/semantic matching | Fixed | Medium |
| F-004 | Deploy script should auto-export data before uploading | Open | Medium |
| F-005 | Web search should support multi-word queries (split terms, match any) | Fixed | High |
| B-014 | Technology Distribution shows only 3 topics — most repos lack GitHub topic tags | Fixed | Medium |
| B-015 | AI & Search cluster contains non-AI repos (exampleLoops, Palindrome-Index) | Fixed | Low |
| F-006 | Auto-tag repos with topics inferred from README content during indexing | Fixed | Medium |
| B-016 | API /search and /clusters return 500 when no SQLite index exists (no graceful error) | Open | Medium |
| B-017 | google-auth not installed after sprint merge — pyproject.toml updated but venv not synced | Fixed | High |
| F-007 | Google Sign-In button not visible — needs googleClientId configured in web/config.json | Open | Medium |
| F-008 | Request Access form should show Google Sign-In when clientId is configured | Open | Medium |
