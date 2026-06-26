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


def write_tutorial_prose(theme: dict, prs: list[dict], client, *, model: str, retries: int = 2) -> dict:
    member_keys = set(theme.get("pr_numbers", []))
    members = [p for p in prs if f"{p['repo']}#{p['pr_number']}" in member_keys]
    facts = "\n".join(
        f"- PR#{p['pr_number']}: {p.get('problem','')} | approach: {p.get('approach','')} | "
        f"pattern: {p.get('reusable_pattern')}" for p in members
    )
    user = f"Theme: {theme.get('title','')}\nRepos: {', '.join(theme.get('repos', []))}\nPR facts:\n{facts}"
    last_missing = None
    for _ in range(retries):
        llm = client.complete_json(TUTORIAL_SYSTEM, user)
        missing = [k for k in _PROSE_KEYS if k not in llm]
        if not missing:
            for k in _PROSE_KEYS:
                theme[k] = llm[k]
            theme["model"] = model
            return theme
        last_missing = missing
    raise NarrateValidationError(f"tutorial missing fields: {last_missing}")


_LABEL_KEYS = ("name", "scenario", "title", "pattern", "principle")
_BODY_KEYS = ("description", "application", "detail", "body", "summary")


def _li(item) -> str:
    """Render one list item. Qwen sometimes returns structured objects
    (e.g. {name, description} for patterns, {scenario, application} for
    how-to-apply) instead of plain strings; render those as a labelled bullet
    rather than dumping the dict repr."""
    if isinstance(item, dict):
        label = next((item[k] for k in _LABEL_KEYS if item.get(k)), None)
        body = next((item[k] for k in _BODY_KEYS if item.get(k)), None)
        if label and body:
            return f"<li><strong>{html.escape(str(label))}</strong> — {html.escape(str(body))}</li>"
        # Unrecognised dict shape: join its values rather than show {'k': 'v'}.
        return f"<li>{html.escape(' — '.join(str(v) for v in item.values()))}</li>"
    return f"<li>{html.escape(str(item))}</li>"


def _ul(items) -> str:
    return "<ul>" + "".join(_li(i) for i in items) + "</ul>" if items else ""


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
