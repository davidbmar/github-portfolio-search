"""Reuse-aware building — retrieval, provenance, and the reuse ledger.

See ADR-0001. Pure logic; the MCP server wraps these in thin handlers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RELATIONS = frozenset({"reuse", "extend", "link", "inspired", "new"})


def load_building_text(building: str) -> tuple[str, str]:
    """Resolve the tool's `building` arg to (text, source_label).

    A short value that names an existing file is read as a design doc; anything
    else is treated as an inline description. The 400-char guard stops a long
    design-doc-passed-as-text from being probed as a filesystem path.
    """
    try:
        if len(building) < 400 and Path(building).is_file():
            return Path(building).read_text(), f"doc: {building}"
    except OSError:
        pass
    return building, f"description: {building[:80]}"


def record_reuse(
    ledger_path: str,
    built: str,
    reused: list[str],
    relation: str,
    note: str = "",
    session: str = "",
    ts: str | None = None,
) -> dict:
    """Append one reuse decision to the JSONL ledger; return the written record."""
    if not built:
        raise ValueError("built is required")
    if relation not in RELATIONS:
        raise ValueError(f"relation must be one of {sorted(RELATIONS)}, got {relation!r}")

    record = {
        "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built": built,
        "reused": list(reused or []),
        "relation": relation,
        "note": note,
        "session": session,
    }
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def _embedding_candidates(store, embedder, query: str, k: int) -> list[dict]:
    """Nearest repos by embedding, deduped to best score per repo."""
    vec = embedder.embed_text(query)
    raw = store.search(vec, limit=k * 3)
    best: dict[str, dict] = {}
    for row in raw:
        repo = row["repo_name"]
        score = round(1.0 - row["distance"], 4)
        if repo not in best or score > best[repo]["score"]:
            best[repo] = {"repo": repo, "score": score, "snippet": (row["text"] or "")[:200]}
    return sorted(best.values(), key=lambda c: -c["score"])[:k]


def reuse_check(store, embedder, projects: list[dict], building: str,
                k: int = 5, min_score: float = 0.05) -> dict:
    """Surface existing repos relevant to what's about to be built, with provenance.

    Score is `1.0 - sqlite_vec_L2_distance` (see ghps.store.search). Empirically,
    relevant repos land at a small POSITIVE score (~0.06-0.26) and off-topic ones
    go negative, so the default floor sits just above zero. (An earlier 0.5 default
    was mis-calibrated against similarity.json's cosine scale and returned
    'greenfield' for everything — caught by live smoke; see ADR-0001.)
    """
    from ghps.docsgen.search_docs import search_docs

    text, source = load_building_text(building)
    by_slug = {p.get("slug", ""): p for p in projects}
    matched_by_slug = {h["slug"]: h["matched"] for h in search_docs(projects, text, limit=50)}

    candidates = []
    for cand in _embedding_candidates(store, embedder, text, k):
        if cand["score"] < min_score:
            continue
        rec = by_slug.get(cand["repo"], {})
        candidates.append({
            "repo": cand["repo"],
            "score": cand["score"],
            "one_liner": rec.get("one_liner", ""),
            "repo_url": rec.get("repo_url", ""),
            "reuse_tags": rec.get("reuse_tags", []),
            "patterns": rec.get("patterns", []),
            "how_to_apply": rec.get("how_to_apply", ""),
            "why": {
                "matched_fields": matched_by_slug.get(cand["repo"], []),
                "snippet": cand["snippet"],
            },
        })

    return {
        "source": source,
        "verdict": "candidates" if candidates else "greenfield",
        "candidates": candidates,
    }
