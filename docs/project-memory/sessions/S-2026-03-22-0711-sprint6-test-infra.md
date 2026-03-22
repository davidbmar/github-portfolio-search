# Session

Session-ID: S-2026-03-22-0711-sprint6-test-infra
Title: Sprint 6 - Test infrastructure and Makefile improvements
Date: 2026-03-22
Author: agentB

## Goal

Fix remaining test failures (B-005, B-006), add playwright to test dependencies, skip playwright tests when browser not installed, and create complete Makefile targets.

## Context

Sprint 6 agentB task. B-005 and B-006 fixes were already in place from prior sprints. Remaining work: test infrastructure hardening.

## Plan

1. Verify B-005/B-006 already fixed
2. Add playwright to pyproject.toml test group
3. Add pytest.importorskip to test_web_playwright.py
4. Add export/deploy targets to Makefile
5. Verify all tests pass

## Changes Made

- pyproject.toml: Added `test` optional-dependency group with playwright
- tests/test_web_playwright.py: Added pytest.importorskip for graceful skip when playwright not installed
- Makefile: Added export and deploy targets, updated .PHONY list

## Decisions Made

- B-005/B-006 were already fixed in cli.py; no code changes needed there
- Created separate `test` dependency group rather than adding playwright to `dev` group, since playwright requires browser binaries
- Deploy target validates prerequisites (web/ dir and scripts/deploy.sh) before running

## Open Questions

None.

## Links

Commits:
- (pending)
