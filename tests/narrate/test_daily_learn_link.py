from ghps.docsgen.render import render_daily_page, _deep_dives_section


def test_deep_dives_section_links_to_learn():
    idx = [{"slug": "grounding-integrity-gate", "title": "Grounding Integrity Gate",
            "summary": "A validation firewall."}]
    html = render_daily_page([], learn_index=idx)
    assert 'href="/learn/grounding-integrity-gate.html"' in html
    assert "Grounding Integrity Gate" in html
    assert "Deep dives" in html


def test_no_section_without_index():
    html = render_daily_page([], learn_index=None)
    assert '<section class="deep-dives">' not in html


def test_deep_dives_escapes_content():
    idx = [{"slug": "x", "title": "<script>", "summary": "<b>"}]
    html = _deep_dives_section(idx)
    assert "<script>" not in html and "&lt;script&gt;" in html
