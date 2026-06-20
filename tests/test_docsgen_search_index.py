"""Unit tests for building the projects search index (projects-search.json).

The search index is the single source of truth for the web SPA's client-side
search. It is a projection of the docsgen project records — so private projects
(e.g. ``riff``), which the GitHub-API indexer never sees, are searchable too.
"""

from __future__ import annotations

import json

from ghps.docsgen import search_index


def _project(slug="riff", **overrides):
    rec = {
        "slug": slug,
        "title": slug.title(),
        "one_liner": "Voice agent platform from plain English.",
        "what_it_is": "A deterministic FSM-driven voice agent generator.",
        "how_its_built": "Python, FastAPI, a state-machine compiler.",
        "how_to_apply": "Describe your business; it emits an agent.",
        "features": ["Plain-English authoring", "Deterministic FSM"],
        "tech": ["Python", "FastAPI"],
        "reuse_tags": ["voice-agent", "fsm"],
        "visibility": "private",
        "thin": False,
    }
    rec.update(overrides)
    return rec


def test_entry_is_keyed_by_slug_with_title_and_one_liner():
    entry = search_index.build_search_index([_project()])[0]
    assert entry["repo"] == "riff"
    assert entry["title"] == "Riff"
    assert entry["one_liner"].startswith("Voice agent platform")


def test_keywords_are_lowercased_tech_plus_reuse_tags_deduped():
    entry = search_index.build_search_index(
        [_project(tech=["Python", "FSM"], reuse_tags=["fsm", "voice-agent"])]
    )[0]
    # lowercased, tech first then reuse_tags, duplicate "fsm" collapsed
    assert entry["keywords"] == ["python", "fsm", "voice-agent"]


def test_chunks_cover_prose_fields_with_their_source():
    entry = search_index.build_search_index([_project()])[0]
    sources = {c["source"]: c["text"] for c in entry["chunks"]}
    assert "what_it_is" in sources and "FSM-driven" in sources["what_it_is"]
    assert "how_its_built" in sources and "FastAPI" in sources["how_its_built"]
    assert "one_liner" in sources


def test_features_list_is_joined_into_one_chunk():
    entry = search_index.build_search_index([_project()])[0]
    feat = next(c["text"] for c in entry["chunks"] if c["source"] == "features")
    assert "Plain-English authoring" in feat and "Deterministic FSM" in feat


def test_title_text_is_searchable_as_a_chunk():
    entry = search_index.build_search_index([_project(slug="riff")])[0]
    assert any(c["source"] == "title" and "Riff" in c["text"] for c in entry["chunks"])


def test_empty_text_fields_produce_no_chunk():
    entry = search_index.build_search_index(
        [_project(what_it_is="", how_its_built=None, features=[])]
    )[0]
    sources = {c["source"] for c in entry["chunks"]}
    assert "what_it_is" not in sources
    assert "how_its_built" not in sources
    assert "features" not in sources


def test_projects_without_slug_are_skipped():
    entries = search_index.build_search_index(
        [_project(slug="riff"), {"title": "No Slug", "one_liner": "x"}]
    )
    assert [e["repo"] for e in entries] == ["riff"]


def test_private_project_is_included():
    """Regression: a private project like riff must be in the search corpus."""
    entries = search_index.build_search_index([_project(visibility="private")])
    assert entries[0]["repo"] == "riff"


def test_write_search_index_emits_payload(tmp_path):
    out = tmp_path / "data" / "projects-search.json"
    search_index.write_search_index([_project(), _project(slug="other")], str(out))
    payload = json.loads(out.read_text())
    assert payload["count"] == 2
    assert "generated_at" in payload
    assert [e["repo"] for e in payload["entries"]] == ["riff", "other"]
