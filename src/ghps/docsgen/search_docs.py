"""L2 discovery — search the L0 docs feed to answer "have we built X?".

Field-weighted keyword search over the structured records in
``web/data/projects.json``. No embeddings: the records already carry curated,
typed facts (capabilities, tech, patterns, reuse_tags) that make plain term
matching both effective and explainable — every hit reports which fields matched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Field → weight. The typed/reuse signals rank highest because they answer
# "what is this and what can I lift from it?" better than prose.
_FIELD_WEIGHTS = {
    "title": 5,
    "reuse_tags": 5,
    "capabilities": 4,
    "tech": 4,
    "patterns": 4,
    "components": 3,
    "integrates_with": 3,
    "one_liner": 3,
    "features": 2,
    "what_it_is": 1,
    "how_its_built": 1,
    "how_to_apply": 1,
}

_TOKEN = re.compile(r"[a-z0-9]+")

# Common words that match everywhere and would otherwise dominate scoring
# (e.g. "speech to text" must not rank an auth portal first because of "to").
_STOPWORDS = {
    "a", "an", "the", "to", "of", "and", "or", "for", "in", "on", "with",
    "is", "are", "be", "by", "as", "at", "from", "that", "this", "it",
    "how", "do", "i", "we", "you", "using", "use", "via", "into", "can",
}


def _terms(text: str) -> list[str]:
    """Tokenize to lowercase terms, dropping stopwords and 1-char noise."""
    return [t for t in _TOKEN.findall(text.lower()) if len(t) > 1 and t not in _STOPWORDS]


def _field_text(value) -> str:
    """Flatten a string or list-of-strings field to a lowercased haystack."""
    if isinstance(value, list):
        return " ".join(str(v) for v in value).lower()
    return str(value or "").lower()


def search_docs(projects: list[dict], query: str, limit: int = 10) -> list[dict]:
    """Rank *projects* against *query* by weighted field matches.

    Returns a list of hits sorted by score (desc), each:
        {slug, title, one_liner, repo_url, score, matched: [field, ...]}
    Projects with no matching term are omitted. Empty query → [].
    """
    terms = _terms(query)
    if not terms:
        return []

    hits: list[dict] = []
    for proj in projects:
        score = 0
        matched: list[str] = []
        for field, weight in _FIELD_WEIGHTS.items():
            haystack = _field_text(proj.get(field))
            if not haystack:
                continue
            field_hit = False
            for term in terms:
                occurrences = haystack.count(term)
                if occurrences:
                    score += weight * occurrences
                    field_hit = True
            if field_hit:
                matched.append(field)
        if score > 0:
            hits.append(
                {
                    "slug": proj.get("slug", ""),
                    "title": proj.get("title", proj.get("slug", "")),
                    "one_liner": proj.get("one_liner", ""),
                    "repo_url": proj.get("repo_url", ""),
                    "score": score,
                    "matched": matched,
                }
            )

    hits.sort(key=lambda h: (-h["score"], h["slug"]))
    return hits[:limit]


def load_feed(path: str) -> list[dict]:
    """Load the projects list from a projects.json feed file ([] if missing)."""
    p = Path(path)
    if not p.is_file():
        return []
    data = json.loads(p.read_text())
    return data.get("projects", []) if isinstance(data, dict) else []
