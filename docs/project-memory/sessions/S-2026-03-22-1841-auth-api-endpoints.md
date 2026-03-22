# Session

Session-ID: S-2026-03-22-1841-auth-api-endpoints
Title: Add Google OAuth auth endpoints and access-list API
Date: 2026-03-22
Author: agentB

## Goal

Add authentication endpoints to the FastAPI server: Google JWT verification, access request/approve/deny workflow, and persistent access list.

## Context

Sprint 13 — replacing password gate with Google OAuth. agentA handles frontend OAuth, agentB (this) handles backend API endpoints, agentC handles Telegram notifications.

## Plan

1. Create src/ghps/auth.py with token verification and access list CRUD
2. Add auth/access endpoints to src/ghps/api.py
3. Add google-auth dependency
4. Write comprehensive tests

## Changes Made

- Created `src/ghps/auth.py`: Google JWT verification via google-auth library, JSON-file-based access list at ~/.ghps/access.json, functions for verify_token, is_approved, approve_email, deny_email, add_pending_request, get_pending_requests
- Updated `src/ghps/api.py`: Added 5 new endpoints (POST /api/auth/verify, POST /api/access/request, GET /api/access/pending, POST /api/access/approve, POST /api/access/deny), admin endpoints protected by GHPS_ADMIN_TOKEN env var
- Updated `pyproject.toml`: Added google-auth>=2.29 dependency
- Created `tests/test_auth.py`: 21 tests covering access list CRUD, token verification (mocked), and all API endpoints

## Decisions Made

- Used GHPS_ADMIN_TOKEN env var for admin endpoint auth (simple shared secret, sufficient for Telegram bot integration)
- Access list stored as JSON at ~/.ghps/access.json (consistent with project's lightweight approach)
- Admin endpoints return 403 JSONResponse (not exceptions) to match existing _err() pattern

## Links

Commits:
- TBD
