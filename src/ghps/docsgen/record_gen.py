"""Turn a RepoContext into a validated structured record via the LLM.

The LLM owns the prose, diagrams, and typed-metadata fields. The generator owns
the deterministic fields — slug, repo_url, visibility, thin, todos, provenance —
and never trusts the model for them. Invalid LLM output triggers one retry, then
a RecordGenerationError (caller marks a failure; never renders a broken page).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ghps.docsgen import hygiene, schema
from ghps.docsgen.context import RepoContext
from ghps.docsgen.llm_client import LLMError

_MAX_README_CHARS = 6000
_MAX_FILE_CHARS = 1500
_MAX_FILES = 6

# How many times to attempt generation: 1 try + 1 retry.
_MAX_ATTEMPTS = 2

# Fields the model is asked to author (the ONLY keys pulled from LLM output).
_LLM_OWNED = (
    "title",
    "one_liner",
    "what_it_is",
    "how_its_built",
    "how_to_apply",
    "diagram_architecture",
    "diagram_sequence",
    "capabilities",
    "components",
    "tech",
    "depends_on",
    "integrates_with",
    "patterns",
    "reuse_tags",
)

# Fields the GENERATOR owns and always sets in _assemble from trusted sources
# (ctx / derived state) — never from the untrusted LLM output. Kept strictly
# disjoint from _LLM_OWNED so model output can never populate a deterministic
# field; the assert below makes a future "let the model set status" diff fail
# at import time rather than silently widening the trust boundary.
_GENERATOR_OWNED = (
    "slug",
    "repo_url",
    "visibility",
    "status",
    "thin",
    "todos",
    "generated_at",
    "source_commit",
    "model",
)

assert set(_LLM_OWNED).isdisjoint(_GENERATOR_OWNED), (
    "trust boundary violated: a field is declared both LLM-owned and "
    "generator-owned"
)

_SYSTEM = """You are a senior engineer writing a precise, reusable project brief.
Output ONE JSON object with EXACTLY these keys and no others:
  title (string), one_liner (string),
  what_it_is (string), how_its_built (string), how_to_apply (string),
  diagram_architecture (Mermaid flowchart source string),
  diagram_sequence (Mermaid sequenceDiagram source string),
  capabilities, components, tech, depends_on, integrates_with, patterns,
  reuse_tags (all arrays of short strings).
The sequenceDiagram MUST reflect how the code actually runs (who calls whom) —
do not hand-wave it from the README. Keep prose concrete and free of marketing.
Mermaid must be valid: start diagram_architecture with 'flowchart' and
diagram_sequence with 'sequenceDiagram'."""


class RecordGenerationError(RuntimeError):
    """Raised when the LLM cannot produce a schema-valid record after retry."""


def build_messages(ctx: RepoContext) -> tuple[str, str]:
    """Return (system, user) prompt strings for *ctx*."""
    files_block = "\n\n".join(
        f"--- {path} ---\n{content[:_MAX_FILE_CHARS]}"
        for path, content in ctx.source_files[:_MAX_FILES]
    )
    thin_note = (
        "\nNOTE: this repo is THIN (fork/stub/empty). Keep every field short and "
        "factual; do not invent capabilities.\n"
        if ctx.thin
        else ""
    )
    user = f"""Repository: {ctx.slug}
URL: {ctx.repo_url}
Primary language: {ctx.language}
Topics: {", ".join(ctx.topics) or "(none)"}
Description: {ctx.description or "(none)"}{thin_note}

README (truncated):
{ctx.readme[:_MAX_README_CHARS] or "(no README)"}

Key source files (truncated):
{files_block or "(no source files retrieved)"}
"""
    return _SYSTEM, user


def generate_record(ctx: RepoContext, client, *, model: str | None = None) -> dict:
    """Generate a validated record for *ctx* using *client*.

    *model* is recorded as provenance; defaults to ``client.model``.
    """
    system, user = build_messages(ctx)

    last_error = ""
    for _attempt in range(_MAX_ATTEMPTS):
        # A failed LLM call (network/HTTP/unparseable) is retried just like an
        # invalid record — so one bad repo never aborts a batch run.
        try:
            llm_part = client.complete_json(system, user)
        except LLMError as exc:
            last_error = f"LLM call failed: {exc}"
            continue
        record = _assemble(ctx, llm_part, model or getattr(client, "model", "unknown"))
        errors = schema.validate_record(record)
        if not errors:
            return record
        last_error = f"record invalid: {errors}"

    raise RecordGenerationError(f"{ctx.slug}: {last_error}")


def _assemble(ctx: RepoContext, llm_part: dict, model: str) -> dict:
    """Merge LLM-owned fields with deterministic generator-owned fields."""
    record: dict = {field: llm_part.get(field) for field in _LLM_OWNED}
    record.update(
        {
            "slug": ctx.slug,
            "repo_url": ctx.repo_url,
            "visibility": ctx.visibility,
            "status": "shipped",
            "thin": ctx.thin,
            "todos": hygiene.derive_todos(ctx.branch_status, ctx.open_prs),
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "source_commit": ctx.head_sha[:7] if ctx.head_sha else "",
            "model": model,
        }
    )
    return record
