"""Unit tests for the minimal, escape-safe Markdown -> HTML renderer.

Docs come from untrusted repos, so the renderer escapes all text first and only
emits a known-safe tag subset (no raw HTML passthrough).
"""

from __future__ import annotations

from ghps.docsgen import markdown as md


def test_atx_headings():
    assert "<h1>Title</h1>" in md.render("# Title")
    assert "<h3>Sub</h3>" in md.render("### Sub")


def test_paragraphs_separated_by_blank_lines():
    out = md.render("First para.\n\nSecond para.")
    assert "<p>First para.</p>" in out
    assert "<p>Second para.</p>" in out


def test_unordered_list():
    out = md.render("- one\n- two")
    assert "<ul>" in out and "<li>one</li>" in out and "<li>two</li>" in out


def test_ordered_list():
    out = md.render("1. first\n2. second")
    assert "<ol>" in out and "<li>first</li>" in out and "<li>second</li>" in out


def test_fenced_code_block_is_escaped_and_not_inline_processed():
    out = md.render("```\nconst x = `a` **b**\n<script>\n```")
    assert "<pre><code>" in out
    # inside code: no inline formatting, and HTML escaped
    assert "&lt;script&gt;" in out
    assert "<strong>" not in out
    assert "<script>" not in out


def test_inline_bold_italic_code():
    out = md.render("This is **bold**, *italic*, and `code`.")
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out
    assert "<code>code</code>" in out


def test_links_are_rendered_with_escaped_href():
    out = md.render("See [the site](https://example.com/a?b=1).")
    assert '<a href="https://example.com/a?b=1"' in out
    assert ">the site</a>" in out


def test_javascript_url_in_link_is_neutralized():
    out = md.render("[x](javascript:alert(1))")
    # The real security property: an unsafe scheme must never become an href.
    # (Rendering the literal text inertly is fine.)
    assert 'href="javascript' not in out
    assert "href='javascript" not in out
    assert "<a " not in out  # no anchor emitted at all for the unsafe URL


def test_raw_html_is_escaped_not_passed_through():
    out = md.render("<img src=x onerror=alert(1)>")
    assert "<img" not in out
    assert "&lt;img" in out


def test_blockquote_and_hr():
    out = md.render("> quoted\n\n---")
    assert "<blockquote>" in out and "quoted" in out
    assert "<hr" in out


def test_empty_input_yields_empty_string():
    assert md.render("") == ""
    assert md.render("   \n  \n") == ""
