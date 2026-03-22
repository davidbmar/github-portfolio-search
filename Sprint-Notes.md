# Sprint 7 — Agent Notes

*Started: 2026-03-22 15:32 UTC*

Phase 1 Agents: 2
- agentA-test-fixes
- agentB-real-data

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentA-test-fixes

*Completed: 2026-03-22 15:35 UTC*

### Files changed
- `tests/test_cli.py` — Removed `mix_stderr=False` from 3 `CliRunner()` calls (lines 143, 283, 316); changed `result.stderr` → `result.output` in assertions
- `src/ghps/cli.py` — Added environment variable suppression for model-loading progress bars (`TOKENIZERS_PARALLELISM`, `HF_HUB_DISABLE_PROGRESS_BARS`, `TRANSFORMERS_NO_ADVISORY_WARNINGS`) and set `sentence_transformers` logger to WARNING level

### Commands run
- `git pull origin main` — already up to date
- `python3 -m pytest tests/test_cli.py tests/test_e2e.py -v` — 18 passed
- `python3 -m pytest tests/ -v` — **137 passed, 0 failures, 0 errors**
- `git push -u origin HEAD` — pushed to `agentA-test-fixes`

### Notes / follow-on work
- The missing-index error handling in `cli.py` was already correct (`click.echo(..., err=True)` + `sys.exit(1)`). Only the test assertions needed updating.
- If Click is later downgraded below 8.2, these tests will still work since the default `mix_stderr=True` behavior is the same across all Click versions.


---

## agentB-real-data

*Completed: 2026-03-22 15:38 UTC*

### Files changed
- **`src/ghps/export.py`** — Language fallback: `""` → `"Unknown"` for repos with no language detected
- **`scripts/generate-sample-data.py`** — Replaced 10 fictional repos with 42 real repos from davidbmar's GitHub account
- **`scripts/index-and-export.sh`** — Added JSON validation step (checks files exist, are valid arrays, are non-empty)
- **`web/data/repos.json`** — Regenerated with 42 real repos, accurate descriptions and `html_url` links
- **`web/data/clusters.json`** — Regenerated with 6 logical clusters (Voice & Speech, Transcription & ASR, Browser-Native AI, AI & Search Tools, AWS Infrastructure, Developer Tools)
- **`docs/project-memory/sessions/S-2026-03-22-1538-real-data-pipeline.md`** — Session doc

### Commands run
- `git pull origin main`
- `curl` GitHub public API to fetch real repo metadata (106 repos across 2 pages)
- `python3 scripts/generate-sample-data.py --output web/data`
- `python3 -m pytest tests/ -v` — **129 passed, 0 failures**
- `git push -u origin HEAD`

### Notes / follow-on work
- **GITHUB_TOKEN not available** — used public API for metadata only. When token is available, run `GITHUB_TOKEN=ghp_xxx scripts/index-and-export.sh davidbmar` for full indexing with embeddings and `search-index.json` generation
- The `ORDER BY name` in `_build_repos` SQL already ensures deterministic output (no code change needed)
- Repos with no README are already handled — description is pulled from the DB `repos` table, not from README content

