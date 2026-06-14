"""Unit tests for L2 docs search (pure, no network)."""

from __future__ import annotations

import json

from ghps.docsgen import search_docs


def _projects():
    return [
        {
            "slug": "headline-gen", "title": "Headline Generator",
            "one_liner": "Integrity-checked headline generation.",
            "repo_url": "https://github.com/u/headline-gen",
            "capabilities": ["headline generation"], "tech": ["python", "fastapi"],
            "patterns": ["fail-closed gate"], "reuse_tags": ["llm-provider-isolation"],
            "components": ["LLMClient seam"], "integrates_with": ["Qwen"],
            "features": ["multi-provider"], "what_it_is": "x", "how_its_built": "y",
            "how_to_apply": "z",
        },
        {
            "slug": "voice-loop", "title": "Voice Loop",
            "one_liner": "Local voice agent.",
            "repo_url": "https://github.com/u/voice-loop",
            "capabilities": ["speech to text"], "tech": ["typescript", "webrtc"],
            "patterns": [], "reuse_tags": ["browser-stt"], "components": [],
            "integrates_with": [], "features": [], "what_it_is": "", "how_its_built": "",
            "how_to_apply": "",
        },
    ]


def test_empty_query_returns_nothing():
    assert search_docs.search_docs(_projects(), "") == []


def test_matches_by_tech_tag():
    hits = search_docs.search_docs(_projects(), "fastapi")
    assert [h["slug"] for h in hits] == ["headline-gen"]
    assert "tech" in hits[0]["matched"]


def test_matches_by_reuse_tag_and_reports_field():
    hits = search_docs.search_docs(_projects(), "llm-provider-isolation")
    assert hits[0]["slug"] == "headline-gen"
    assert "reuse_tags" in hits[0]["matched"]


def test_ranks_more_relevant_first():
    # "voice" only appears in voice-loop; "python" only in headline-gen
    assert search_docs.search_docs(_projects(), "voice")[0]["slug"] == "voice-loop"


def test_no_match_returns_empty():
    assert search_docs.search_docs(_projects(), "kubernetes blockchain") == []


def test_stopwords_do_not_skew_ranking():
    # "to" is a stopword; the speech repo must win on "speech"/"text", not lose
    # to a prose-heavy repo that merely contains "to" many times.
    projects = [
        {"slug": "speechy", "title": "Speechy", "one_liner": "Speech to text engine.",
         "capabilities": ["speech to text"], "tech": [], "patterns": [],
         "reuse_tags": [], "components": [], "integrates_with": [], "features": [],
         "what_it_is": "", "how_its_built": "", "how_to_apply": ""},
        {"slug": "prosey", "title": "Prosey", "one_liner": "",
         "capabilities": [], "tech": [], "patterns": [], "reuse_tags": [],
         "components": [], "integrates_with": [], "features": [],
         "what_it_is": "you need to add this to that to do the thing to win",
         "how_its_built": "", "how_to_apply": ""},
    ]
    hits = search_docs.search_docs(projects, "speech to text")
    assert hits[0]["slug"] == "speechy"


def test_query_of_only_stopwords_returns_nothing():
    assert search_docs.search_docs(_projects(), "how do i use the") == []


def test_limit_caps_results():
    hits = search_docs.search_docs(_projects(), "generation speech", limit=1)
    assert len(hits) == 1


def test_load_feed_reads_projects(tmp_path):
    feed = tmp_path / "projects.json"
    feed.write_text(json.dumps({"count": 1, "projects": [{"slug": "a"}]}))
    assert search_docs.load_feed(str(feed)) == [{"slug": "a"}]


def test_load_feed_missing_file_returns_empty(tmp_path):
    assert search_docs.load_feed(str(tmp_path / "nope.json")) == []
