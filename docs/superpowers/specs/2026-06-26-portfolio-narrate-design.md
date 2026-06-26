# Design: `/portfolio-narrate` — PR-grounded applied tutorials from your portfolio

**Date:** 2026-06-26
**Status:** Draft for review
**Author:** David Mar (with Claude + Codex consult)

## Problem

The daily digest at davidbmar.com/daily/ reads like a changelog, not a tutorial. Three root causes in `src/ghps/daily.py`:

1. **It only sees commit *messages*** (`_user_prompt`, daily.py:66) — never the code. You cannot write a code-grounded tutorial from `"fix: gate collect-complete"`.
2. **It groups by calendar day** (`aggregate_by_day`, daily.py:44) — an arbitrary boundary that can't tell a story arc that spans days.
3. **The output contract is tiny** — headline + 2 sentences + 2-4 bullets (`_SYSTEM`, daily.py:29).

Goal: produce in-depth, **applied tutorials** (AWS-applied-blog feel: principles + patterns + examples, grounded in real code) that read like a retrospective *grouped by theme/action*, and that improve as code is approved and pushed.

## Core bet (from the Codex consult)

> Durable, evidence-backed **theme records built from PRs** — not "LLM clusters diffs and three models write articles."

The load-bearing structure is **deterministic intermediate records + one strong model + validation**, reusing the proven pattern in `record_gen.py` (LLM owns prose+tags; generator owns identity, provenance, publication-state, render-safety; JSON-only + validate + retry-then-fail-closed). The multi-model panel is explicitly **deferred to v2**.

## Decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Input unit | **Merged PRs + bounded diffs** (fallback: commits) | Real code = tutorial-grade material; fires when "code is approved & pushed" |
| Grouping | **LLM clusters structured PR *facts* into themes** (not raw diffs) | Facts are small, stable, clusterable |
| Theme identity | **Immutable slug + alias list; embed-then-classify `attach\|create\|ignore`** | Stops `/learn/<slug>` URL churn across runs |
| Trigger | **Milestone (maturity score)**, not raw `>=3` count | Avoids thin/rotting articles |
| Model | **DashScope Qwen3.7** (single model, v1) | Already in CI secrets, no new key; `LLMClient` stays pluggable for later A/B |
| Packaging | **Thin Claude Code skill wrapping `src/ghps/` logic** | Installable across all Claude Codes; core logic stays importable + cron-runnable |
| Publishing (v1) | **Render to local `github-portfolio-search/web/learn/<slug>.html` (dry-run/preview)** | No cross-repo mutation; proves the bet before touching other repos |
| Publishing (v2) | **Commit + push `docs/html/learn-<slug>.html` to the source repo, gated by preflight** | Then nightly `fetch_html_docs` republishes → davidbmar.com. This is REAL plumbing (see correction below), built last |
| Delivery | **Manual skill run OR nightly cron**; shared `src/ghps` code path | Cron and skill must not diverge |

> **Correction (Codex review).** An earlier draft claimed "zero new publish plumbing." That was wrong. `fetch_html_docs` (`github_client.py:298`) reads `docs/html/**` from each repo's **GitHub default branch**, and `gen-docs.yml` checks out only *this* repo and commits only `projects/ web/`. Publishing a tutorial to a source repo therefore requires the skill to **commit + push to that repo first** — cross-repo mutation, push perms, preflight gates. v1 avoids this entirely by rendering to local `web/learn/`.

## Pipeline

```
1. SCAN     gh/git: merged PRs via a `merged_at` CURSOR (not PR-number high-water mark —
            PRs merge out of creation order). Re-scan an overlap window and keep a
            `seen_pr_numbers` set so late-merged old PRs are not skipped forever.
            Fallback to commits where PR data is unavailable.
2. REDUCE   Deterministic diff filter (NO LLM). Evidence comes from the GitHub PR
            files/diff + `merge_commit_sha`, NOT local branch history (squash/rebase-safe):
              - drop lockfiles, generated/vendored, snapshots, compiled assets, large blobs
              - cap per-PR by file count + token budget
              - ALWAYS keep tests changed + public interfaces changed
              - huge PRs: per-file summary first, then PR summary
            → PRRecord (one per PR), carrying files_hash, merge_commit_sha, facts_hash.
3. CLUSTER  Embed PRRecord summary (all-MiniLM-L6-v2, local) → retrieve candidate themes →
            ONE LLM step: attach | create | ignore, written to a MEMBERSHIP LEDGER.
            Re-runs REUSE prior decisions unless `--reclassify`. Slug is immutable.
4. MATURE   Deterministic maturity score + lifecycle transitions (see thresholds below).
            A scheduled lifecycle pass enforces stale_after (archive / merge / short-note).
5. WRITE    Single strong model drafts the tutorial from the ThemeRecord + evidence
            snippets. Self-critique pass: "list unsupported claims / missing evidence" → revise.
6. RENDER   ThemeRecord renders:
              (a) /daily/         enriched narrative blurb (no raw code) + link out
              (b) web/learn/<slug>.html   LOCAL tutorial (v1)  →  source-repo docs/html (v2)
              (c) project page    "What we built & why" section update (after a+b prove out)
```

## New schemas (alongside existing `Record`)

Both schemas get **their own validators** (mirroring `record_gen.py`'s fail-closed
validation). Do **not** reuse `Record`'s status enum (`idea|building|shipped`,
`schema.py:47`) — ThemeRecord needs its own lifecycle states.

**`PRRecord`** (generator-owned identity + LLM-owned facts):
```
pr_number, repo, merged_at, title, body, labels         # metadata (generator)
merge_commit_sha, files_hash, facts_hash, prompt_version # idempotency keys (generator)
files: [{path, adds, dels, lang, status}]               # manifest (generator)
problem, approach, components, apis_changed,            # facts (LLM, JSON-only)
tests_changed, reusable_pattern, risks
evidence: [{path, excerpt}]                             # high-signal snippets (generator-selected)
model, generated_at                                     # provenance (generator)
```
Upsert rule: same `files_hash` + same `prompt_version` → keep existing LLM facts;
changed hash or prompt/schema version → regenerate. Key: `repo/pr_number`.

**Membership ledger** (`state/membership.jsonl`) — the anti-drift primitive:
```
repo/pr_number -> { theme_id | "ignored", decision_reason,
                    candidate_scores[], classifier_model, prompt_version }
```
Default re-runs reuse the ledger; `--reclassify` is the only way to move a PR.

**`ThemeRecord`**:
```
theme_id, slug (IMMUTABLE), title (mutable), aliases[]   # identity (generator)
home_repo                                                # repo with most PRs in theme
repos[], pr_numbers[], keywords[]                        # membership (generator)
status: candidate | mature | published | archived        # OWN enum (not Record's)
candidate_since, last_activity_at, published_at, stale_after
maturity_score, maturity_reason                          # generator-computed
# LLM-owned tutorial prose (JSON-only, validated):
summary, narrative, principles[], patterns[], applied_examples[], pitfalls[]
source_commits[], model, generated_at                    # provenance
```

ThemeRecords are **derived** from PRRecords + the ledger. A force rebuild rebuilds
ThemeRecords from PRRecords — it must **never mint new slugs for known themes.**
Tutorial pages are **never raw LLM prose without a validated record underneath.**

## Thresholds (concrete, Codex-recommended v1 defaults)

**Clustering (cosine on MiniLM embeddings):**
- `>= 0.78` → eligible attach candidate
- `0.62 - 0.78` → ask the classifier with top-5 themes
- `< 0.62` → create-new or ignore only
- Attach also requires classifier confidence **and** ≥1 shared component/API/pattern keyword.
- `ignore` only for chore/deps/formatting/generated-only PRs.

**Maturity score:** `+2` per PR (cap 6), `+2` tests changed, `+2` public API/CLI surface,
`+1` docs/readme, `+2` `reusable_pattern==true`, `+2` release tag, `-3` chore/deps-heavy.
- `candidate`: ≥1 meaningful PR
- `mature`: score `>= 7`
- `published`: mature **and** generated tutorial validates
- `archived`: no meaningful activity after `90d` and score `< 5`
- `stale_after`: `45d` after `last_activity_at` for candidates, `120d` for published

A **lifecycle pass** (run each invocation) enforces these: archive, merge, or mark
"short-note-eligible." Without it, candidate records accumulate and retrieval gets noisier.

## Publishing detail

**v1 — local preview, no cross-repo writes.** Render mature themes to
`github-portfolio-search/web/learn/<slug>.html` + a `/learn/` index (small addition to
`aggregate.py`). Deploys with the existing `web/` push. Proves tutorial quality with zero
cross-repo risk.

**v2 — publish into the source repo, behind preflight gates.** Home repo = repo with the
most PRs in the theme (or an explicit pin). Tutorial written to
`<home_repo>/docs/html/learn-<slug>.html`, committed + pushed; nightly `fetch_html_docs`
republishes it. The skill needs a **slug → local repo path** map (default `~/src/<repo>`)
and MUST preflight before any write:
- repo path exists and remote owner/repo matches
- working tree clean (or explicit branch/worktree strategy)
- default branch known; push permission verified; protected-branch behavior known
- target path not git-ignored; **never write `index.html`** (repo docs build renames it to
  `overview.html`, `generate.py:194`); no collision with a human-authored `learn-<slug>.html`

If any gate fails → skip that publish, log, continue. Never best-effort push.

## Skill / library boundary

**Logic lives in `src/ghps/` (importable, unit-tested); the skill is a thin wrapper.**
Start as **one importable CLI path** (e.g. `ghps narrate ...`) — *not* five scripts;
split modules only after the interfaces harden (Codex: "five scripts is premature
structure"). The same code runs from cron (`gen-docs.yml`) and from the skill, so they
cannot diverge.

```
src/ghps/narrate/        # core, importable, tested
  scan.py    reduce.py    cluster.py    mature.py    render.py    schema.py
~/.claude/skills/portfolio-narrate/
  SKILL.md               # frontmatter (name, description) + workflow; shells into `ghps narrate`
```

**State lives in the repo / a configured data dir, NOT inside the skill folder**
(`web/data/narrate/` or similar): `pr_records/`, `theme_records/`, `membership.jsonl`,
`cursor.json`. Putting state under `~/.claude/skills/...` would make cron and skill runs
diverge.

## Build sequence (ship the bet first; cross-repo publish LAST)

1. **`scan`** — merged-PR scanner → `PRRecord` stubs, with `merged_at` cursor, overlap,
   `seen_pr_numbers`, content hashes.
2. **`reduce`** — deterministic diff/evidence reducer + PRRecord validation. No clustering.
3. **`cluster`** — local MiniLM retrieval, immutable ThemeRecord creation, persisted
   membership ledger. Manual review mode acceptable.
4. **`mature`** — deterministic score/status transitions. No prose until this is stable.
5. **`render`** — one `learn-<slug>.html` from a mature ThemeRecord into local `web/learn/`
   (dry-run). Then `/daily/` blurb.
6. **cross-repo publish (v2)** — commit/push into source repo behind preflight. Last.

**First proof of the bet:** one mature theme built from 2-3 real merged PRs, rendered
locally from validated PRRecords + ThemeRecord, where a **re-run produces byte-stable
identity and membership.**

## What we are explicitly NOT building in v1 (Codex-flagged)

- **Cross-repo publishing** (commit/push into source repos). v1 renders to local `web/learn/`; cross-repo is v2, behind preflight gates.
- The 3-model panel (codex + gemini + agy). Deferred to v2 as a pluggable role layer once /learn pages prove out. (All three CLIs confirmed present: `codex exec`, `gemini -p`, `agy -p`.)
- Fully autonomous theme naming (slugs are immutable + alias-guarded).
- Release-tag special handling beyond a maturity-score boost.
- Updating per-project pages from the same record until the learn pages work (render path (c) lands after (a) and (b)).

## Failure modes & defenses

| Failure | Defense |
|---|---|
| Theme slug churn | Immutable slug, alias list, embed-then-classify retrieval-first |
| Orphan PRs (never reach a theme) | Stay as `candidate`, visible internally, never block; can publish as short note |
| Themes stuck at 2 PRs forever | `stale_after` → publish-short / merge / archive |
| Huge PR diffs blow token budget | Deterministic reducer caps + per-file pre-summarize |
| Tag bundles unrelated work → bad tutorial | Tag only *boosts* maturity; reusable-pattern evidence still required |
| LLM erases concrete facts | Tutorial built from validated `pr_record` evidence; self-critique pass flags unsupported claims |
| Re-run instability | State file of last-processed PR; records keyed by pr_number/theme_id, idempotent |

## Reused from existing code

- `record_gen.py` generation pattern (the core bet).
- `llm_client.py` DashScope/Anthropic JSON clients (set model in v1).
- `context.py` `fetch_html_docs` republish path (zero new publish plumbing for the tutorial).
- `render.py` HTML/Mermaid rendering + prompt-injection escaping.
- `aggregate.py` for the optional `/learn/` index.

## Resolved (post-Codex review)

1. **Milestone** — maturity score ≥7 (formula above), not a raw PR count. `candidate` at 1 meaningful PR.
2. **Embedding** — reuse `all-MiniLM-L6-v2` from `embeddings.py` (local, free, 384-dim) + keyword/Jaccard tie-break.
3. **Cross-repo home** — "most PRs wins" with an optional explicit pin.
4. **Publishing** — v1 local `web/learn/`; cross-repo push is v2, behind preflight, built last.
5. **State** — in-repo data dir, shared by cron + skill.

## Resolved (continued)

6. **Model — DashScope Qwen3.7** for everything (PRRecord fact extraction *and* tutorial
   prose), via the existing `DashScopeClient` (`llm_client.py:80`). Already wired into CI
   secrets, no new key. The `LLMClient` interface stays pluggable so Claude can be swapped
   in later for an A/B on prose quality if Qwen's tutorials fall short of the bar.
