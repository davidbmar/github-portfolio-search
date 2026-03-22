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
| B-005 | CLI tests fail on missing index edge cases (4 failures in test_cli.py) | Open | Medium |
| B-006 | test_e2e.py json decode error in CLI search JSON output | Open | Medium |
| B-007 | sprint-run.sh dies during "Collecting project metrics" phase | Open | High |
| F-001 | Add .env support for GITHUB_TOKEN (python-dotenv) | Open | Medium |
| F-002 | Add progress bar to indexer (tqdm) | Open | Low |
| F-003 | Add Makefile with install/test/serve/index targets | Open | Medium |
| B-008 | API /search and /clusters return empty when no index exists (no error msg) | Open | Medium |
| B-009 | davidbmar.com still shows placeholder — web UI not deployed | Fixed | High |
| B-010 | davidbmar.com "Could not load data" — data/repos.json is empty (.gitkeep only) | Open | Critical |
| B-011 | test_web_playwright.py errors — playwright not in dev dependencies | Open | High |
| B-012 | .venv symlinks break after agent merges (too many levels of symbolic links) | Open | High |
| F-004 | Deploy script should auto-export data before uploading | Open | Medium |
