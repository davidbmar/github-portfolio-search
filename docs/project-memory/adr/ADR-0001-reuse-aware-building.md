# ADR-0001: Reuse-aware building — MCP retrieval + a reuse ledger, not a static canonical registry

Status: Accepted
Date: 2026-07-12

## Context

The portfolio now publishes a rich, machine-readable map of what has been built:
`constellation.json` (stars + clusters + similarity threads + centrality), the
`projects-index.json` / `*.record.json` docs corpus, and the `ghps-mcp` server
with semantic search. An arriving agent (a future Claude session, an external
LLM, or the author) can *read* the portfolio.

The goal is one step further: make the portfolio a **lego set**. Before building
anything new, an agent should scan what already exists and *why*, then **reuse**,
**extend**, **link to**, or knowingly start fresh — instead of rebuilding from
scratch and burning tokens re-deriving work that already exists.

The obvious first idea was a **precomputed "canonical blocks" registry** — a
blessed subset of repos elevated as reusable building blocks. Two flavors were
considered: hand-curated, and auto-derived from existing signals. Investigation
killed the auto-derived flavor as a *starting point*:

- There is **no internal repo→repo reuse graph** in the data. `depends_on` /
  `integrates_with` (85–87% populated) point at *external* systems ("AWS EC2",
  "Anthropic Claude API"), not sibling repos. The only signal relating two repos
  is **embedding similarity**, which measures topical *typicality*, not reuse
  value. A great building block is often *unique* — nothing resembles it because
  nothing else does that job — so similarity-centrality can canonize the wrong
  things.
- Reuse-intent fields don't discriminate: `reuse_tags` 97%, `how_to_apply` 100%.
  Nearly every repo claims to be reusable, so "has reuse signals" filters nothing.
- "Canonical" implies durable, but a nightly-recomputed ranking churns — today's
  block drops off tomorrow, which breaks "build on top of / link to."

## Decision

Build **reuse-aware building** as an *interactive, in-the-loop* mechanism, and
**defer** canonical-block derivation until real reuse data exists.

Five units, each with one job:

- **A — `portfolio_reuse_check(building, k=5, min_score=0.05)`** (new MCP tool,
  read-only). `building` may be a short natural-language description **or the text
  / path of a design doc, spec, or plan** — the tool embeds it and finds nearest
  existing repos via the *existing* `_handle_portfolio_search` path, joins each hit
  with its docs-feed reuse fields (`one_liner`, `reuse_tags`, `patterns`,
  `how_to_apply`, `repo_url`), applies `min_score`, and returns ranked candidates
  framed as reuse options — or an explicit "greenfield / no close match" so it
  stays quiet when there's nothing relevant.
  Each candidate carries **provenance** so the surfaced result is explainable, not
  a black box: (a) the **query source** ("your design doc `X.md`" vs an inline
  description), (b) **why it matched** — the repo's docs-feed fields that overlapped
  (`portfolio_find_docs` already returns "the fields that matched") and/or the
  matched README/source **snippet** (`_handle_portfolio_search` already returns it),
  and (c) the **score**. This lets the agent say "surfaced `parakeet-asr-service`
  (0.71) *because* your design doc mentions streaming ASR and it has
  reuse_tags [asr, streaming-transcription]."
- **B — `portfolio_record_reuse(built, reused[], relation, note)`** (new MCP tool,
  the only writer). Appends one edge per decision to
  `web/data/reuse-ledger.jsonl`. `relation ∈ {reuse, extend, link, inspired, new}`.
  This is the **only new state in the system** and is the missing repo→repo reuse
  graph, accumulated one decision at a time.
- **C — Reuse protocol** (a skill + a CLAUDE.md rule): "before building a new
  component, run `portfolio_reuse_check`; after deciding, `portfolio_record_reuse`."
  The habit layer, self-triggered by any agent that reads project instructions.
- **D — Reuse hook** (`settings.json`, `UserPromptSubmit` matching build-intent):
  injects a reminder to run the check. The deterministic "can't forget it" backstop.
- **E — Discovery surfacing** (`llms.txt`): register the reuse tools and
  `constellation.json` so external agents discover them.

Retrieval uses embedding similarity **correctly** here: as query→neighbor
retrieval against the specific thing being built (its actual strength), not as a
global reuse-worthiness ranking (its weakness).

### Deferred to v2 (explicitly out of scope for v1)

- Feed the ledger back into `constellation.json` as **real reuse edges** (bright =
  actually reused, faint = merely similar).
- **Auto-derive canonical blocks** — now honest, because it ranks on real reuse
  edges (inbound "reused-by" count), not typicality.
- Visualize reuse edges in the star map.

v1's job is to **collect the reuse data**; v2 derives the blocks from it.

## Consequences

### Positive
- Sidesteps the unsolved "what earns the canonical badge" problem — relevance is
  computed per-task, just-in-time.
- **Explainable retrieval**: every suggestion cites its provenance (query source +
  matched fields/snippet + score), so a reuse prompt is actionable ("surfaced
  because your design doc mentions X") instead of an ignorable black-box "similar
  repo." Reuses evidence the existing handlers already return.
- Reuses shipped machinery (embed + `store.search` + docs feed); the only new
  surface is the two tools + one append-only file.
- The interactive ask **manufactures the missing repo→repo graph** as a byproduct
  of building — turning a cold-start problem into a warm-over-time system, and
  eventually unblocking the auto-derived canonical blocks that v1 can't yet do.
- The ledger is committed and survives nightly cold rebuilds (same durability
  pattern as narrate slug pinning).

### Negative
- v1 delivers no canonical blocks yet — value compounds only as the ledger fills.
- The protocol (C) only helps when actually invoked; the hook (D) is the mitigation
  but risks noise if its build-intent trigger is too broad.
- Retrieval quality depends on a specific "what am I building" description; vague
  input retrieves poorly.

### Neutral
- `min_score` is calibrated to the **store's** scoring scale, not the constellation's.
  `reuse_check` ranks on `1.0 - sqlite_vec_L2_distance` (query↔chunk), where relevant
  repos score a small positive value (~0.06–0.26) and off-topic ones go negative —
  NOT the `similarity.json` cosine scale (median ~0.56, repo↔repo). Default floor is
  `0.05`, just above the natural zero boundary. (An initial `0.5` — wrongly borrowed
  from the exporter's `FAINT_FLOOR` reasoning — made the tool return 'greenfield' for
  everything; caught only by the live end-to-end smoke, not the mocked unit tests.)
- `reuse-ledger.jsonl` becomes a new committed artifact the deploy syncs.

## Evidence

- Data scan (2026-07-12, 140 projects): `integrates_with`/`depends_on` reference
  external systems, not sibling repos → no internal reuse graph. `reuse_tags` 97%,
  `how_to_apply` 100% → reuse-intent fields do not discriminate.
- `src/ghps/mcp_server.py::_handle_portfolio_search` already implements
  query→embedding→nearest-repo retrieval (`embed_text` → `store.search`,
  `score = 1.0 - distance`); the MCP is a local stdio server with filesystem
  access (reads `web/data/projects.json`), so it can also write the ledger.
- `scripts/export_constellation.py` computes centrality as similarity degree and
  notes GitHub stars are ~all zero — i.e., no external reuse signal to rank on.

## Links

Sessions:
- S-2026-07-12-2332-reuse-aware-building

PRs:
- (pending)

Commits:
- (pending)
