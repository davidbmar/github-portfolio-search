# Session

Session-ID: S-2026-07-12-2332-reuse-aware-building
Title: Reuse-aware building — MCP reuse-check + reuse ledger
Date: 2026-07-12
Author: David Mar (with Claude)

## Goal

Ship the Portfolio Constellation live, then design a mechanism so the portfolio
works as a **lego set**: before building anything new, scan what already exists
and why, then reuse / extend / link / start fresh — and capture that decision so
the portfolio gets smarter over time.

## Context

The constellation was built but never deployed (assets only on a local branch),
so CloudFront served the index.html shell at a 200 for `/constellation.html`.
Separately, the user wants the portfolio to be usable by AIs to "find what was
done and cache instead of rebuilding." Investigation showed there is no internal
repo→repo reuse graph to derive canonical blocks from — only embedding similarity,
which measures typicality, not reuse value.

## Plan

1. Root-cause + ship the constellation (push branch, PR to main, deploy, verify).
2. Design reuse-aware building (see ADR-0001): interactive MCP retrieval + a reuse
   ledger, deferring canonical-block derivation to v2 once real edges exist.
3. Implement v1: `portfolio_reuse_check`, `portfolio_record_reuse`, the reuse
   protocol/skill, the build-intent hook, and llms.txt surfacing.

## Changes Made

- Shipped Portfolio Constellation to davidbmar.com (PR #8 merged to main;
  reindex.yml deploy verified live — 98 stars, all assets HTTP 200).
- Resolved merge conflicts (sitemap union; dropped stale paren-named blog
  duplicate in favor of main's clean `2026.JUL07.06-RachetLoop.html`).
- Wrote ADR-0001 (reuse-aware building design).
- (implementation pending)

## Decisions Made

- Interactive, in-the-loop reuse retrieval over a precomputed canonical registry.
  Why: similarity is right for per-task retrieval, wrong for global ranking; and a
  static registry can't be honestly auto-derived without a real reuse graph.
- The `reuse-ledger.jsonl` is the only new state — it *becomes* the missing
  repo→repo graph, which later unblocks auto-derived canonical blocks (v2).

## Open Questions

- `min_score` default (0.5) — confirm against live retrieval quality once built.
- Should the hook trigger on `UserPromptSubmit` keywords, or a narrower signal?

## Resolved

- `relation` taxonomy locked: `reuse · extend · link · inspired · new`.
  `link` = a deliberate, author-blessed companion/"see also" edge (distinct from
  the constellation's inferred similarity threads). `new` records negative
  evidence (looked, nothing fit, why).
- `portfolio_reuse_check` must return **provenance** (query source + matched
  fields/snippet + score) and accept a **design doc / plan / any doc** as input,
  so results read as "surfaced because your design doc mentions X."

## Links

Commits:
- (pending)

PRs:
- #8 - Ship Portfolio Constellation + Ratchet Loops blog to davidbmar.com

ADRs:
- ADR-0001 - Reuse-aware building
