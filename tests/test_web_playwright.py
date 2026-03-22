"""Playwright tests for the web UI.

Verifies:
- Landing page shows cluster cards from clusters.json
- Search filters repos from repos.json
- Request Access section is visible with form fields
- Mobile layout works (375px viewport)
"""

from __future__ import annotations

import http.server
import os
import threading

import pytest

pytest.importorskip("playwright", reason="playwright not installed — skipping web UI tests")

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
PORT = 8787


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logs during tests


@pytest.fixture(scope="module")
def web_server():
    """Serve the web/ directory on a local port for Playwright tests."""
    handler = lambda *a, **kw: QuietHandler(*a, directory=WEB_DIR, **kw)
    server = http.server.HTTPServer(("127.0.0.1", PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{PORT}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser_context(web_server):
    """Launch a Playwright browser for the test module."""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context()
    yield context, web_server
    context.close()
    browser.close()
    pw.stop()


class TestWebUI:
    def test_landing_page_shows_clusters(self, browser_context):
        """Landing page should show cluster cards from clusters.json."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url)
        page.wait_for_selector(".cluster-card", timeout=10000)
        cards = page.query_selector_all(".cluster-card")
        assert len(cards) >= 1, "Expected at least 1 cluster card on landing page"
        page.close()

    def test_search_shows_results(self, browser_context):
        """Searching for 'audio' should return matching repos."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url)
        page.wait_for_selector(".cluster-card", timeout=10000)
        page.fill("#search-input", "audio")
        page.press("#search-input", "Enter")
        page.wait_for_selector(".repo-card", timeout=10000)
        cards = page.query_selector_all(".repo-card")
        assert len(cards) >= 1, "Expected at least 1 repo card for 'audio' search"
        page.close()

    def test_search_no_results(self, browser_context):
        """Searching for nonsense should show 'No results'."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url)
        page.wait_for_selector(".cluster-card", timeout=10000)
        page.fill("#search-input", "xyznonexistent999")
        page.press("#search-input", "Enter")
        page.wait_for_selector(".empty-state", timeout=10000)
        empty = page.query_selector(".empty-state")
        assert empty is not None, "Expected 'No results' empty state"
        text = empty.text_content()
        assert "No results" in text
        page.close()

    def test_clusters_page(self, browser_context):
        """Navigating to #/clusters should show cluster cards."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url + "#/clusters")
        page.wait_for_selector(".cluster-card", timeout=10000)
        cards = page.query_selector_all(".cluster-card")
        assert len(cards) >= 1
        page.close()

    def test_request_access_page(self, browser_context):
        """Request Access page should show form with name, email, reason fields."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url + "#/access")
        page.wait_for_selector(".access-request-page", timeout=10000)

        assert page.query_selector("#access-name") is not None, "Name input missing"
        assert page.query_selector("#access-email") is not None, "Email input missing"
        assert page.query_selector("#access-reason") is not None, "Reason textarea missing"
        assert page.query_selector("#access-submit") is not None, "Submit button missing"

        tier_info = page.query_selector(".access-tier-info")
        assert tier_info is not None
        assert "Public tier" in tier_info.text_content()
        page.close()

    def test_request_access_form_submit(self, browser_context):
        """Submitting the access form should show coming soon message."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url + "#/access")
        page.wait_for_selector(".access-request-page", timeout=10000)

        page.fill("#access-name", "Test User")
        page.fill("#access-email", "test@example.com")
        page.fill("#access-reason", "Testing the form")
        page.click("#access-submit")

        msg = page.wait_for_selector(".form-message.visible", timeout=5000)
        assert "Coming soon" in msg.text_content()
        page.close()

    def test_mobile_layout_375px(self, browser_context):
        """At 375px viewport, nav and content should still be visible."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(base_url)
        page.wait_for_selector(".cluster-card", timeout=10000)

        nav = page.query_selector(".site-nav")
        assert nav is not None, "Navigation should be visible at 375px"
        assert nav.is_visible()

        cards = page.query_selector_all(".cluster-card")
        assert len(cards) >= 1, "Cluster cards should render at 375px"
        page.close()

    def test_navigation_links(self, browser_context):
        """All nav links should be present."""
        ctx, base_url = browser_context
        page = ctx.new_page()
        page.goto(base_url)
        page.wait_for_selector(".site-nav", timeout=10000)

        links = page.query_selector_all(".nav-link")
        link_texts = [link.text_content().strip() for link in links]
        assert "Home" in link_texts
        assert "Search" in link_texts
        assert "Clusters" in link_texts
        assert "Request Access" in link_texts
        page.close()
