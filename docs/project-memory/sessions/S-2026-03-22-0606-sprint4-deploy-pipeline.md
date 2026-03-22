# Session

Session-ID: S-2026-03-22-0606-sprint4-deploy-pipeline
Title: Sprint 4 — Deployment pipeline for S3/CloudFront
Date: 2026-03-22
Author: agentC

## Goal

Build the deployment pipeline to push the web UI to S3/CloudFront at davidbmar.com.

## Context

Sprint 4 focuses on the public web UI. agentC is responsible for the deployment pipeline and integration. agentA handles data export, agentB handles frontend code.

## Plan

1. Create web/data/.gitkeep for exported data directory
2. Create web/health.json with version and deploy timestamp
3. Create deploy.sh that runs export, builds, uploads to S3, invalidates CloudFront
4. Add deploy instructions to README.md
5. Add _build/ to .gitignore

## Changes Made

- Created `web/data/.gitkeep` — directory for ghps export output
- Created `web/health.json` — health check with version and last-deploy timestamp
- Created `deploy.sh` — idempotent deployment script (export -> build -> S3 sync -> CloudFront invalidation)
- Updated `README.md` — added Deployment section with usage instructions
- Updated `.gitignore` — added `_build/` build artifacts

## Decisions Made

- deploy.sh gracefully handles missing `ghps export` command since agentA owns that feature
- Using `aws s3 sync --delete` to keep S3 bucket clean of stale files
- Build directory pattern (`_build/`) isolates deploy artifacts from source
- health.json gets timestamp written at deploy time, not from the static file

## Open Questions

- ghps export command/flags depend on agentA's implementation

## Links

Commits:
- (pending)
