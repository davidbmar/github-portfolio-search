# Design — Daily Headline Digest (`/daily`)

**Session:** S-2026-06-20-2054-daily-headline-digest
**Status:** Approved — build with codex as the default engine.

## Goal
A "build in public" daily digest of portfolio activity: aggregate each day's
commits across all of davidbmar's repos, generate a catchy **headline** + a short
**summary** per day, and publish a `/daily` feed on davidbmar.com.

## Two decoupled stages
1. **Generate** (offline / nightly; needs GitHub PAT + an LLM engine): fetch
   commits across all repos → aggregate by **UTC day** → headline + summary per
   day → write `web/data/daily.json`.
2. **Render** (web build; no LLM): `daily.json` → `/daily` page + nav link.
   Static and fast — same pattern as `projects-search.json`.

## Engine (pluggable, resolved in this order)
1. **codex** (default) — `codex exec --skip-git-repo-check --sandbox read-only
   --output-last-message <file> '<prompt>'`. Returns clean
   `{"headline":…,"summary":…}` JSON in ~5s. Reliable, no local server.
2. **mlx** (optional) — POST to a local `mlx_lm.server` (Gemma 3 12B) at
   `localhost:8080`. Fully offline/free; needs RAM headroom.
3. **deterministic** (always-available fallback) — no LLM. Headline like
   "5 repos · 12 commits" so `/daily` always renders even with no engine.

Each engine implements `generate(date, commit_lines) -> {headline, summary}`.
The codex/mlx prompt is a fixed system instruction (tech-changelog editor, emit
ONLY JSON, don't invent facts) + the day's commit lines as the user message.

## Components
- **`github_client.fetch_commits(owner, repo, since=None, until=None, max_pages=…)`**
  *(new)* — paginated `GET /repos/{o}/{r}/commits`; returns
  `[{sha, message, date}]` (date = author/commit date, ISO-Z). Empty on 404/409
  (empty repo). Shares the session/auth with the other fetchers.
- **`ghps/daily.py`** *(new)*:
  - `aggregate_by_day(repo_commits) -> {date: [ {repo, sha, message} ]}` — buckets
    by UTC calendar day; skips empty days.
  - `CodexEngine` / `MlxEngine` / `DeterministicEngine` with a common
    `generate(date, lines) -> {headline, summary}`; `resolve_engine(name|auto)`.
  - `build_digests(repo_commits, engine) -> [day_record]` where a day_record is
    `{date, headline, summary, total_commits, repos:[{name, commits, messages}]}`,
    newest first.
  - `write_daily(days, path)` → `web/data/daily.json`
    (`{generated_at, count, days}`).
  - `collect(owner, gh, since) -> repo_commits` — iterate `gh.fetch_repos`, fetch
    each repo's commits since `since`.
- **`render.render_daily_page(days)`** — `/daily/index.html` + flat `daily.html`
  (CF no-trailing-slash), unified site nav, newest-first cards
  (headline · date · summary · repos-touched chips). Empty-state when no days.
- **`generate.publish_all`** — also render `/daily` from `daily.json` if present
  (so the static build stays the single renderer).
- **CLI `ghps daily`** — `--since <date>` (backfill window), `--engine
  auto|codex|mlx|deterministic`, `--owner davidbmar`. Writes `daily.json` and the
  page.
- **Nav** — add "Daily" to the SPA nav (`web/index.html`) and the unified static
  `_SITE_NAV` (`render.py`).

## Data contract (`web/data/daily.json`)
```json
{ "generated_at": "…Z", "count": 2, "days": [
  { "date": "2026-06-20", "headline": "Portfolio Search and Project Docs Expanded",
    "summary": "…", "total_commits": 12,
    "repos": [ { "name": "github-portfolio-search", "commits": 9,
                 "messages": ["feat: unify search…", "chore(web): regenerate…"] } ] } ] }
```

## Testing
- **pytest (TDD, offline):** `aggregate_by_day` (UTC bucketing, empty days),
  `DeterministicEngine` (no LLM), `build_digests` (shape, ordering, totals),
  `write_daily`, `fetch_commits` (mocked session: pagination, 404→empty, date
  parse), `render_daily_page` (cards, nav, empty state). The codex/mlx engines are
  injected, so the suite never calls a real LLM.
- **Live test:** run `ghps daily --since <recent> --engine codex` against real
  repos, confirm `daily.json` + `/daily` render in the browser.

## Risks / notes
- **Backfill cost/time:** all repos × all history = many codex calls (~5s each).
  Default `--since` to a recent window for the first run; widen deliberately.
- **codex availability:** if `codex` isn't on PATH or errors, engine resolution
  falls through to mlx → deterministic, so generation never hard-fails.
- **Ongoing/cron:** the nightly "Reindex and Deploy" runner can't run codex/MLX;
  ongoing generation runs locally (or a cron with codex creds). Digest data is
  committed, so the static site always has it.
