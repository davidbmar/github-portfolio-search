"""Golden-structure tests for the HTML renderer (no network)."""

from __future__ import annotations

import json
import re

from ghps.docsgen import render


def _record(**overrides) -> dict:
    base = {
        "slug": "demo",
        "title": "Demo Project",
        "repo_url": "https://github.com/davidbmar/demo",
        "visibility": "public",
        "status": "shipped",
        "thin": False,
        "one_liner": "Does a thing.",
        "what_it_is": "A demonstration with <script>danger</script>.",
        "how_its_built": "With Python.",
        "how_to_apply": "Copy it.",
        "diagram_architecture": "flowchart LR; A-->B",
        "diagram_sequence": "sequenceDiagram; A->>B: hi",
        "capabilities": ["demoing"],
        "components": ["main"],
        "tech": ["python"],
        "depends_on": [],
        "integrates_with": [],
        "patterns": ["adapter"],
        "reuse_tags": ["demo"],
        "todos": [{"kind": "unmerged_branch", "detail": "feat/x is 2 commits ahead"}],
        "generated_at": "2026-06-13T00:00:00Z",
        "source_commit": "abc1234",
        "model": "qwen-plus",
    }
    base.update(overrides)
    return base


def test_has_json_data_island_matching_record():
    html = render.render_page(_record())
    m = re.search(
        r'<script type="application/json" id="project-data">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert m is not None
    assert json.loads(m.group(1))["slug"] == "demo"


def test_includes_both_mermaid_blocks():
    html = render.render_page(_record())
    assert html.count('class="mermaid"') == 2
    assert "flowchart LR; A--&gt;B" not in html  # mermaid source must NOT be escaped
    assert "flowchart LR; A-->B" in html
    assert "sequenceDiagram; A->>B: hi" in html


def test_includes_json_ld_software_source_code():
    html = render.render_page(_record())
    assert '"@type": "SoftwareSourceCode"' in html


def test_escapes_prose_to_prevent_injection():
    html = render.render_page(_record())
    assert "<script>danger</script>" not in html
    assert "&lt;script&gt;danger&lt;/script&gt;" in html


def test_renders_hygiene_panel_when_todos_present():
    html = render.render_page(_record())
    assert "Needs attention" in html
    assert "feat/x is 2 commits ahead" in html


def test_renders_all_clear_when_no_todos():
    html = render.render_page(_record(todos=[]))
    assert "all on main" in html.lower()


def test_thin_badge_when_thin():
    html = render.render_page(_record(thin=True))
    assert "thin" in html.lower()
