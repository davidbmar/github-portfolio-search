# Session

Session-ID: S-2026-03-22-1840-oauth-frontend
Title: Add Google OAuth frontend with password gate fallback
Date: 2026-03-22
Author: agentA

## Goal

Replace the password gate with Google OAuth (Google Identity Services) while maintaining backward compatibility when no Google client ID is configured.

## Context

Sprint 13 — the site uses a simple password gate ("guild") for access control. This session adds proper Google Sign-In as the primary auth method, with the password gate as a fallback for deployments without OAuth configured.

## Plan

1. Create `web/config.json` with `googleClientId` and `apiUrl` placeholders
2. Create `web/js/auth.js` — Auth module with GIS integration, JWT decoding, localStorage state
3. Update `web/js/app.js` — replace password gate IIFE with auth-aware gate, add user info in header, auto-fill access request form
4. Update `web/index.html` — add GIS script tag and auth.js

## Changes Made

- Created `web/config.json` — config file with `googleClientId` and `apiUrl` placeholders
- Created `web/js/auth.js` — Auth module with: loadConfig(), isOAuthEnabled(), isAuthenticated(), getUser(), renderSignInButton(), signOut(), tryPasswordLogin(), onAuthChange()
- Updated `web/js/app.js` — replaced password gate IIFE with async auth gate that supports both Google OAuth and password fallback; added `_updateHeaderUserInfo()` for avatar/name/sign-out in header; auto-fill name/email in access request form from Google profile
- Updated `web/index.html` — added GIS client script tag and auth.js script tag

## Decisions Made

- **Client-side JWT decoding**: Decode Google's ID token in the browser for display purposes (name, email, picture). Server-side validation happens in the API (agentB's scope).
- **localStorage for OAuth, sessionStorage for password**: OAuth tokens persist across sessions (matching Google's token lifetime), password gate remains session-scoped (original behavior).
- **Dual-mode auth gate**: The IIFE now loads config.json first, then branches to Google Sign-In or password gate based on `googleClientId` being set.

## Open Questions

- Access request form currently shows "coming soon" on submit — agentB/agentC will implement the API endpoint and Telegram notification.

## Links

Commits:
- (pending)
