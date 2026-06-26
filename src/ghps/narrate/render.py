from __future__ import annotations

import html
import re
from pathlib import Path

from .schema import NarrateValidationError

TUTORIAL_SYSTEM = (
    "You are writing an APPLIED TUTORIAL (think a readable AWS applied-architecture blog) "
    "about a body of related work, for a developer who wants to learn the principles and reuse them. "
    "Output ONE JSON object: summary (string), narrative (string: what was built and why, no raw code "
    "dumps), principles (array), patterns (array), applied_examples (array: concrete ways to apply this), "
    "pitfalls (array). Ground everything in the provided PR facts. No marketing. JSON only."
)
_PROSE_KEYS = ("summary", "narrative", "principles", "patterns", "applied_examples", "pitfalls")


def write_tutorial_prose(theme: dict, prs: list[dict], client, *, model: str) -> dict:
    members = [p for p in prs if p["pr_number"] in theme.get("pr_numbers", [])]
    facts = "\n".join(
        f"- PR#{p['pr_number']}: {p.get('problem','')} | approach: {p.get('approach','')} | "
        f"pattern: {p.get('reusable_pattern')}" for p in members
    )
    user = f"Theme: {theme.get('title','')}\nRepos: {', '.join(theme.get('repos', []))}\nPR facts:\n{facts}"
    llm = client.complete_json(TUTORIAL_SYSTEM, user)
    for k in _PROSE_KEYS:
        if k not in llm:
            raise NarrateValidationError(f"tutorial missing field: {k}")
        theme[k] = llm[k]
    theme["model"] = model
    return theme


def _ul(items) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(str(i))}</li>" for i in items) + "</ul>" if items else ""


def render_learn_html(theme: dict) -> str:
    t = html.escape(theme.get("title", ""))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{t} — Learn</title></head><body>
<main><h1>{t}</h1>
<p class="summary">{html.escape(theme.get('summary',''))}</p>
<section><h2>What was built &amp; why</h2><p>{html.escape(theme.get('narrative',''))}</p></section>
<section><h2>Principles</h2>{_ul(theme.get('principles', []))}</section>
<section><h2>Patterns</h2>{_ul(theme.get('patterns', []))}</section>
<section><h2>How to apply</h2>{_ul(theme.get('applied_examples', []))}</section>
<section><h2>Pitfalls</h2>{_ul(theme.get('pitfalls', []))}</section>
<footer>Repos: {html.escape(', '.join(theme.get('repos', [])))}</footer>
</main></body></html>"""


def write_learn_pages(themes: list[dict], out_dir: str | Path) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    cards = []
    for t in themes:
        slug = t["slug"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            raise NarrateValidationError(f"unsafe slug: {slug!r}")
        p = out / f"{slug}.html"
        p.write_text(render_learn_html(t))
        written.append(str(p))
        cards.append(f'<li><a href="{html.escape(slug)}.html">{html.escape(t.get("title",""))}</a> '
                     f'— {html.escape(t.get("summary",""))}</li>')
    idx = out / "index.html"
    idx.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>Learn</title></head>"
                   f"<body><h1>Learn</h1><ul>{''.join(cards)}</ul></body></html>")
    written.append(str(idx))
    return written
