# Session

Session-ID: S-2026-03-22-0556-sprint3-bug-fixes
Title: Sprint 3 bug fixes — B-001, B-004, Makefile, py.typed
Date: 2026-03-22
Author: agentA (Claude)

## Goal

Fix remaining packaging and test bugs from Sprint 1-2 (B-001, B-004). Add missing Makefile targets and py.typed marker.

## Context

Sprint 3 brief assigned agentA to fix test/packaging bugs. pyproject.toml had duplicate [project.scripts] sections causing install failure. Heavy deps (sentence-transformers, sqlite-vec) were imported at module level, making tests fragile without GPU/native deps.

## Plan

1. Fix duplicate [project.scripts] in pyproject.toml
2. Make sentence-transformers and sqlite-vec lazy imports
3. Add lint and serve targets to Makefile
4. Add py.typed marker
5. Ensure all tests pass

## Changes Made

- **pyproject.toml**: Merged duplicate `[project.scripts]` sections into one; added httpx and numpy to dev deps
- **src/ghps/embeddings.py**: Made `sentence_transformers` a lazy import (only loaded when model is accessed)
- **src/ghps/store.py**: Made `sqlite_vec` a lazy import (only loaded on first connect)
- **Makefile**: Added `lint` and `serve` targets
- **src/ghps/py.typed**: Added PEP 561 marker file

## Decisions Made

- Lazy imports over conftest mocking: Moving imports into methods is simpler and more robust than sys.modules patching in conftest. Tests that mock _model never trigger the real import.
- Used py_compile for lint target since no linter was specified in deps.

## Open Questions

None.

## Links

Commits:
- (see git log)
