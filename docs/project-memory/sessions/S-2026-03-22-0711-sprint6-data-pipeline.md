# Session

Session-ID: S-2026-03-22-0711-sprint6-data-pipeline
Title: Sprint 6 - Fix data pipeline and add sample data
Date: 2026-03-22
Author: agentA

## Goal

Fix B-010 (davidbmar.com shows "Could not load data" because data files are empty) by creating realistic sample data and hardening the deploy pipeline.

## Context

The site at davidbmar.com was broken because web/data/repos.json and clusters.json contained placeholder data with only 5 generic repos and 2 clusters. The deploy script had no validation, allowing empty/invalid data to be deployed.

## Plan

1. Create web/data/repos.json with 10 realistic repos from David's actual portfolio
2. Create web/data/clusters.json with 4 capability clusters
3. Verify export.py schema compatibility
4. Create scripts/generate-sample-data.py for reproducible sample data
5. Add data validation to deploy.sh

## Changes Made

- **web/data/repos.json**: Replaced 5 generic repos with 10 realistic portfolio repos (audio-stream-transcription, presigned-url-s3, grassyknoll, FSM-generic, tool-telegram-whatsapp, bot-customerobsessed, traceable-searchable-adr-memory-index, github-portfolio-search, tool-s3-cloudfront-push, everyone-ai)
- **web/data/clusters.json**: Replaced 2 generic clusters with 4 capability clusters (Voice & Audio Processing, Infrastructure & DevOps, AI & Search, Web Applications)
- **scripts/generate-sample-data.py**: New script that produces repos.json and clusters.json with validation
- **deploy.sh**: Added validate_json() function that checks file existence, size, valid JSON, and minimum entry counts before deploying

## Decisions Made

- Used `url` as primary field (matching export.py and app.js) but also included `html_url` (as brief requested) for forward compatibility
- Cluster assignments based on repo descriptions and topics from the brief
- deploy.sh validation uses python3 for JSON parsing since it's already a dependency

## Open Questions

- None

## Links

Commits:
- (pending)
