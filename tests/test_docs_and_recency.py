"""Tests for the per-project docs feature + recency/title findability fixes.

Covers:
  - github_client.fetch_html_docs   (scan docs/**/*.html)
  - context.build_context           (html_docs + pushed_at carried through)
  - record_gen                      (humanized titles, docs/pushed_at fields)
  - render                          (docs link, docs index page, newest-first grid)
  - generate.publish_all            (writes docs files + index, rejects traversal)
"""

from __future__ import annotations

import base64
import json
import types
from unittest.mock import MagicMock, patch

from ghps import github_client
from ghps.docsgen import context, generate, record_gen, render
from ghps.docsgen.context import RepoContext


# ---------------------------------------------------------------------------
# github_client.fetch_html_docs
# ---------------------------------------------------------------------------

def _resp(json_data, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


def _blob(text: str):
    return _resp({"content": base64.b64encode(text.encode()).decode(), "encoding": "base64"})


class TestFetchHtmlDocs:
    @patch.object(github_client, "_session")
    def test_returns_only_html_under_docs_html(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        tree = {"tree": [
            {"type": "blob", "path": "docs/html/a.html", "sha": "s1"},
            {"type": "blob", "path": "docs/html/sub/b.html", "sha": "s2"},
            {"type": "blob", "path": "docs/html/notes.md", "sha": "s3"},   # not html
            {"type": "blob", "path": "docs/other.html", "sha": "s4"},      # not docs/html/
            {"type": "blob", "path": "docs/_build/html/api.html", "sha": "s5"},  # sphinx
            {"type": "tree", "path": "docs/html", "sha": "t"},             # not a blob
        ]}
        session.get.side_effect = [_resp(tree), _blob("<h1>A</h1>"), _blob("<h1>B</h1>")]

        docs = github_client.fetch_html_docs("o", "r", default_branch="main")

        assert [p for p, _ in docs] == ["docs/html/a.html", "docs/html/sub/b.html"]
        assert docs[0][1] == "<h1>A</h1>"

    @patch.object(github_client, "_session")
    def test_missing_tree_returns_empty(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _resp({}, status_code=404)
        assert github_client.fetch_html_docs("o", "r", default_branch="main") == []


class TestFetchMarkdownDocs:
    @patch.object(github_client, "_session")
    def test_returns_only_markdown_under_docs_md(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        tree = {"tree": [
            {"type": "blob", "path": "docs/md/roadmap.md", "sha": "s1"},
            {"type": "blob", "path": "docs/md/sub/design.md", "sha": "s2"},
            {"type": "blob", "path": "docs/md/logo.png", "sha": "s3"},     # not md
            {"type": "blob", "path": "docs/other.md", "sha": "s4"},        # not docs/md/
            {"type": "blob", "path": "README.md", "sha": "s5"},            # not under docs/md/
            {"type": "tree", "path": "docs/md", "sha": "t"},               # not a blob
        ]}
        session.get.side_effect = [_resp(tree), _blob("# Roadmap"), _blob("# Design")]

        docs = github_client.fetch_markdown_docs("o", "r", default_branch="main")

        assert [p for p, _ in docs] == ["docs/md/roadmap.md", "docs/md/sub/design.md"]
        assert docs[0][1] == "# Roadmap"

    @patch.object(github_client, "_session")
    def test_missing_tree_returns_empty(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _resp({}, status_code=404)
        assert github_client.fetch_markdown_docs("o", "r", default_branch="main") == []


# ---------------------------------------------------------------------------
# context.build_context
# ---------------------------------------------------------------------------

def _repo_meta(**overrides):
    base = {
        "name": "demo", "description": "d", "language": "Python", "topics": [],
        "html_url": "https://github.com/davidbmar/demo", "private": False,
    }
    base.update(overrides)
    return base


def _ctx_gh(**docs_return):
    gh = MagicMock()
    gh.fetch_readme.return_value = "# Demo\n\nReal content for the project."
    gh.fetch_top_files.return_value = [("main.py", "print('hi')")]
    gh.fetch_branches.return_value = [{"name": "main", "commit_sha": "aaa111"}]
    gh.fetch_open_prs.return_value = []
    gh.compare_commits.return_value = 0
    gh.fetch_html_docs.return_value = docs_return.get("docs", [])
    gh.fetch_markdown_docs.return_value = docs_return.get("md_docs", [])
    return gh


def test_context_carries_pushed_at_and_html_docs():
    gh = _ctx_gh(docs=[("docs/html/guide.html", "<h1>Guide</h1>")])
    ctx = context.build_context(
        _repo_meta(pushed_at="2026-06-14T00:00:00Z"), owner="davidbmar", gh=gh
    )
    assert ctx.pushed_at == "2026-06-14T00:00:00Z"
    assert ctx.html_docs == [("docs/html/guide.html", "<h1>Guide</h1>")]


def test_context_carries_markdown_docs():
    gh = _ctx_gh(md_docs=[("docs/md/roadmap.md", "# Roadmap")])
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.md_docs == [("docs/md/roadmap.md", "# Roadmap")]


def test_context_tolerates_gh_without_fetch_html_docs():
    """A gh double predating the docs feature must not break context building."""
    gh = types.SimpleNamespace(
        fetch_readme=lambda o, r: "# Demo\n\nReal content.",
        fetch_top_files=lambda o, r, **k: [("main.py", "x")],
        fetch_branches=lambda o, r: [{"name": "main", "commit_sha": "a"}],
        fetch_open_prs=lambda o, r: [],
        compare_commits=lambda o, r, b, h: 0,
    )
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.html_docs == []
    assert ctx.md_docs == []  # defensively absent too


# ---------------------------------------------------------------------------
# record_gen — title humanization + new generator-owned fields
# ---------------------------------------------------------------------------

_LLM_FIELDS = {
    "title": "Demo Project", "one_liner": "o", "what_it_is": "w",
    "how_its_built": "h", "how_to_apply": "a", "quickstart": "", "features": [],
    "diagram_architecture": "flowchart LR; A-->B",
    "diagram_sequence": "sequenceDiagram; A->>B: hi", "capabilities": [],
    "components": [], "tech": [], "depends_on": [], "integrates_with": [],
    "patterns": [], "reuse_tags": [],
}


def _rc(**overrides) -> RepoContext:
    base = dict(
        slug="demo", owner="davidbmar", repo_url="u", visibility="public",
        default_branch="main", head_sha="abc1234", description="d", language="Python",
        topics=[], readme="# Demo\n\nx", source_files=[("main.py", "x")],
        branch_status=[], open_prs=[], thin=False,
    )
    base.update(overrides)
    return RepoContext(**base)


class _Client:
    model = "fake"

    def __init__(self, fields):
        self._fields = fields

    def complete_json(self, system, user):
        return dict(self._fields)


def test_title_humanized_when_llm_echoes_slug():
    rec = record_gen.generate_record(
        _rc(slug="generate_title_headline_hooks"),
        _Client(dict(_LLM_FIELDS, title="generate_title_headline_hooks")),
    )
    assert rec["title"] == "Generate Title Headline Hooks"


def test_title_humanized_when_llm_blank():
    rec = record_gen.generate_record(_rc(slug="my_repo"), _Client(dict(_LLM_FIELDS, title="")))
    assert rec["title"] == "My Repo"


def test_good_llm_title_preserved():
    rec = record_gen.generate_record(
        _rc(slug="generate_title_headline_hooks"),
        _Client(dict(_LLM_FIELDS, title="Headline Hooks")),
    )
    assert rec["title"] == "Headline Hooks"


def test_record_includes_docs_and_pushed_at():
    ctx = _rc(pushed_at="2026-06-14T00:00:00Z", html_docs=[("docs/html/r.html", "<p>hi</p>")])
    rec = record_gen.generate_record(ctx, _Client(dict(_LLM_FIELDS)))
    assert rec["pushed_at"] == "2026-06-14T00:00:00Z"
    assert rec["docs"] == [{"path": "docs/html/r.html", "html": "<p>hi</p>"}]


def test_record_includes_markdown_docs_kept_as_raw_source():
    ctx = _rc(
        html_docs=[("docs/html/r.html", "<p>hi</p>")],
        md_docs=[("docs/md/roadmap.md", "# Roadmap\n\nPlan.")],
    )
    rec = record_gen.generate_record(ctx, _Client(dict(_LLM_FIELDS)))
    by_path = {d["path"]: d for d in rec["docs"]}
    # html entries keep their existing shape (no kind key)
    assert by_path["docs/html/r.html"] == {"path": "docs/html/r.html", "html": "<p>hi</p>"}
    # markdown entries carry kind + raw source (rendered later, at publish time)
    md = by_path["docs/md/roadmap.md"]
    assert md["kind"] == "md"
    assert md["markdown"] == "# Roadmap\n\nPlan."


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _record(**overrides) -> dict:
    base = {
        "slug": "demo", "title": "Demo", "repo_url": "https://github.com/davidbmar/demo",
        "visibility": "public", "status": "shipped", "thin": False, "one_liner": "o",
        "what_it_is": "w", "how_its_built": "h", "how_to_apply": "a", "quickstart": "",
        "screenshot_url": "", "diagram_architecture": "flowchart", "diagram_sequence": "sequenceDiagram",
        "capabilities": [], "features": [], "components": [], "tech": [], "depends_on": [],
        "integrates_with": [], "patterns": [], "reuse_tags": [], "todos": [],
        "generated_at": "2026-06-13T00:00:00Z", "source_commit": "abc", "model": "m",
    }
    base.update(overrides)
    return base


def test_render_page_shows_docs_link_when_docs_present():
    out = render.render_page(_record(slug="demo", docs=[{"path": "docs/a.html", "html": "x"}]))
    assert 'href="demo/docs/"' in out
    assert "Project documentation" in out


def test_render_page_no_docs_link_when_absent():
    assert 'class="docs-link"' not in render.render_page(_record(docs=[]))


def test_render_daily_page_lists_days_with_headlines_and_repos():
    days = [
        {"date": "2026-06-20", "headline": "Big Shipping Day", "summary": "Did stuff.",
         "takeaways": ["Reuse the search index pattern", "Copy the nav component"],
         "total_commits": 3,
         "repos": [{"name": "alpha", "commits": 2, "messages": ["add widget", "fix bug"]},
                   {"name": "beta", "commits": 1, "messages": ["tune perf"]}]},
        {"date": "2026-06-19", "headline": "Quieter Day", "summary": "One fix.",
         "takeaways": [], "total_commits": 1,
         "repos": [{"name": "alpha", "commits": 1, "messages": ["x"]}]},
    ]
    out = render.render_daily_page(days)
    assert 'class="site-bar"' in out                 # unified nav
    assert "Big Shipping Day" in out and "Quieter Day" in out
    assert "2026-06-20" in out
    assert "Did stuff." in out
    assert "alpha" in out and "beta" in out           # repo chips
    assert out.index("2026-06-20") < out.index("2026-06-19")  # newest first
    # tooltip clarifies what the number means
    assert "commits in alpha" in out or 'title="2 commits' in out
    # click-to-expand detail (native <details>) with apply-takeaways + commits
    assert "<details" in out
    assert "apply" in out.lower()                     # "How you can apply this"
    assert "Reuse the search index pattern" in out    # takeaway shown
    assert "add widget" in out                        # commit message shown in detail


def test_render_daily_page_empty_state():
    out = render.render_daily_page([])
    assert 'class="site-bar"' in out
    assert "muted" in out                             # empty-state message


def test_static_pages_share_unified_site_nav():
    """Every static page carries the same top nav so the site feels integrated
    with the SPA: brand + Search + Projects + Clusters."""
    page = render.render_page(_record(slug="demo"))
    index = render.render_index_page([_record(slug="demo")])
    docs = render.render_docs_index_page({"slug": "demo", "title": "Demo"}, ["a.html"])
    for out in (page, index, docs):
        assert 'class="site-bar"' in out
        assert 'href="/projects/"' in out          # Projects
        assert 'href="/#/search"' in out           # back into the search SPA
        assert ">davidbmar.com<" in out            # brand


def test_mermaid_strips_empty_parens_that_break_flowchart():
    # "run_turn()" inside a [..] label trips Mermaid's parser (the red error icon)
    out = render._mermaid("flowchart TD\n  A[run_turn()] --> B[StateManager]")
    assert "run_turn()" not in out
    assert "run_turn" in out and "StateManager" in out


def test_hygiene_panel_pins_dark_text_for_dark_mode():
    # Panel hardcodes a light background; without a pinned colour, dark-mode
    # paints the text white -> white-on-light. Guard the fix.
    out = render.render_page(
        _record(todos=[{"kind": "unmerged_branch", "detail": "x is 1 commit ahead"}])
    )
    assert "color: #1a1f29" in out


def test_docs_index_lists_docs_with_absolute_links():
    out = render.render_docs_index_page(
        {"slug": "demo", "title": "Demo"}, ["business/roadmap.html", "a.html"]
    )
    # Root-absolute so the page works at both /docs/ and the flat /docs (docs.html)
    assert 'href="/projects/demo/docs/business/roadmap.html"' in out
    assert "Roadmap" in out                       # humanized from filename
    assert 'href="/projects/demo.html"' in out    # back to project page (absolute)


def test_docs_index_groups_html_and_md_with_kind_listings():
    out = render.render_docs_index_page(
        {"slug": "demo", "title": "Demo"},
        ["a.html"],                # html docs (under /docs/)
        ["roadmap.html"],          # md docs (rendered, under /docs/md/)
    )
    assert 'href="/projects/demo/docs/a.html"' in out          # html doc
    assert 'href="/projects/demo/docs/md/roadmap.html"' in out  # md doc (namespaced)
    assert 'href="/projects/demo/docs/html"' in out            # html listing page
    assert 'href="/projects/demo/docs/md"' in out              # md listing page


def test_docs_kind_page_lists_only_that_kind():
    html_page = render.render_docs_kind_page(
        {"slug": "demo", "title": "Demo"}, "html", ["a.html", "sub/b.html"]
    )
    assert 'href="/projects/demo/docs/a.html"' in html_page
    assert 'href="/projects/demo/docs/sub/b.html"' in html_page
    assert 'href="/projects/demo/docs/"' in html_page          # back to combined index

    md_page = render.render_docs_kind_page(
        {"slug": "demo", "title": "Demo"}, "md", ["roadmap.html"]
    )
    assert 'href="/projects/demo/docs/md/roadmap.html"' in md_page
    assert "Roadmap" in md_page


def test_render_markdown_doc_page_wraps_body_with_nav():
    out = render.render_markdown_doc_page(
        {"slug": "demo", "title": "Demo", "repo_url": "https://github.com/x/demo"},
        "roadmap.html",
        "<h1>Road</h1><p>Plan.</p>",
    )
    assert "<h1>Road</h1>" in out and "Plan." in out
    assert 'href="/projects/demo/docs/"' in out     # back to docs index
    assert 'href="/projects/demo.html"' in out      # back to project
    assert "github.com/x/demo" in out               # link to source repo


def test_index_grid_orders_newest_first():
    older = _record(slug="old", title="Old", pushed_at="2020-01-01T00:00:00Z")
    newer = _record(slug="new", title="New", pushed_at="2026-06-14T00:00:00Z")
    out = render.render_index_page([older, newer])
    assert out.index('href="new.html"') < out.index('href="old.html"')
    assert "2026-06-14" in out                    # date shown on card
    assert 'data-sort="newest"' in out            # sort control present


# ---------------------------------------------------------------------------
# generate.publish_all — writes docs + index, rejects path traversal
# ---------------------------------------------------------------------------

def test_publish_writes_repo_docs_and_rejects_traversal(tmp_path):
    records = tmp_path / "projects"
    records.mkdir(parents=True)
    rec = _record(
        slug="demo",
        pushed_at="2026-06-14T00:00:00Z",
        docs=[
            {"path": "docs/html/business/roadmap.html", "html": "<h1>Roadmap</h1>"},
            {"path": "docs/html/../../evil.html", "html": "nope"},  # traversal → dropped
        ],
    )
    (records / "demo.record.json").write_text(json.dumps(rec))

    generate.publish_all(
        records_dir=str(records),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
    )

    proj = tmp_path / "web" / "projects"
    assert (proj / "demo" / "docs" / "business" / "roadmap.html").read_text() == "<h1>Roadmap</h1>"
    assert (proj / "demo" / "docs" / "index.html").exists()
    # flat copy so the no-trailing-slash URL (/projects/demo/docs -> docs.html) works
    flat = (proj / "demo" / "docs.html")
    assert flat.exists()
    assert "/projects/demo/docs/business/roadmap.html" in flat.read_text()
    assert 'href="demo/docs/"' in (proj / "demo.html").read_text()
    # the traversal entry must not escape the docs dir
    assert not (tmp_path / "web" / "evil.html").exists()
    assert not (proj / "evil.html").exists()


def test_publish_renders_markdown_docs_and_kind_listings(tmp_path):
    records = tmp_path / "projects"
    records.mkdir(parents=True)
    rec = _record(
        slug="demo",
        pushed_at="2026-06-14T00:00:00Z",
        docs=[
            {"path": "docs/html/guide.html", "html": "<h1>Guide</h1>"},
            {"path": "docs/md/roadmap.md", "kind": "md",
             "markdown": "# Roadmap\n\nShip **Part 2**."},
            {"path": "docs/md/../../evil.md", "kind": "md",
             "markdown": "nope"},  # traversal → dropped
        ],
    )
    (records / "demo.record.json").write_text(json.dumps(rec))

    generate.publish_all(
        records_dir=str(records),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
    )

    proj = tmp_path / "web" / "projects"
    # html doc unchanged location
    assert (proj / "demo" / "docs" / "guide.html").exists()
    # markdown rendered to HTML under docs/md/
    md_page = (proj / "demo" / "docs" / "md" / "roadmap.html").read_text()
    assert "<h1>Roadmap</h1>" in md_page
    assert "<strong>Part 2</strong>" in md_page       # markdown rendered, not raw
    # per-kind listing pages
    assert (proj / "demo" / "docs" / "html.html").exists()
    assert (proj / "demo" / "docs" / "md.html").exists()
    # combined index references both kinds
    index = (proj / "demo" / "docs" / "index.html").read_text()
    assert "/projects/demo/docs/guide.html" in index
    assert "/projects/demo/docs/md/roadmap.html" in index
    # traversal md entry dropped
    assert not (tmp_path / "web" / "evil.md").exists()
    assert not (proj / "demo" / "docs" / "md" / "evil.html").exists()
