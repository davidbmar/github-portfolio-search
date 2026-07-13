from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.reuse import RELATIONS, load_building_text, record_reuse


def test_relations_are_exactly_five():
    assert RELATIONS == {"reuse", "extend", "link", "inspired", "new"}


def test_load_building_text_from_file(tmp_path):
    doc = tmp_path / "design.md"
    doc.write_text("streaming ASR with speaker diarization")
    text, source = load_building_text(str(doc))
    assert text == "streaming ASR with speaker diarization"
    assert source == f"doc: {doc}"


def test_load_building_text_from_description():
    text, source = load_building_text("a meeting notes summarizer")
    assert text == "a meeting notes summarizer"
    assert source == "description: a meeting notes summarizer"


def test_record_reuse_appends_jsonl(tmp_path):
    ledger = tmp_path / "reuse-ledger.jsonl"
    rec = record_reuse(
        str(ledger), built="meeting-summarizer", reused=["parakeet-asr-service"],
        relation="reuse", note="used /transcribe", session="S-x", ts="2026-07-12T00:00:00Z",
    )
    assert rec["built"] == "meeting-summarizer"
    assert rec["reused"] == ["parakeet-asr-service"]
    assert rec["relation"] == "reuse"
    lines = ledger.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == rec

    record_reuse(str(ledger), built="b2", reused=[], relation="new", note="nothing fit")
    assert len(ledger.read_text().splitlines()) == 2  # appends, not overwrites


def test_record_reuse_rejects_bad_relation(tmp_path):
    with pytest.raises(ValueError):
        record_reuse(str(tmp_path / "l.jsonl"), built="x", reused=[], relation="borrow")


def test_record_reuse_rejects_empty_built(tmp_path):
    with pytest.raises(ValueError):
        record_reuse(str(tmp_path / "l.jsonl"), built="", reused=[], relation="new")


# ---------------------------------------------------------------------------
# reuse_check — retrieval + provenance merge
# ---------------------------------------------------------------------------

import math

from ghps.store import EMBEDDING_DIM


def _fake_embedding(seed: int) -> list:
    return [math.sin(seed * 0.1 + i * 0.01) * 0.5 for i in range(EMBEDDING_DIM)]


class _FakeEmbedder:
    def embed_text(self, text: str) -> list:
        return _fake_embedding(hash(text) % 1000)


_PROJECTS = [
    {
        "slug": "parakeet-asr-service", "title": "Parakeet ASR",
        "one_liner": "Streaming speech-to-text service.",
        "repo_url": "https://github.com/u/parakeet-asr-service",
        "tech": ["python", "nemo"], "reuse_tags": ["asr", "streaming-transcription"],
        "patterns": ["websocket audio ingestion"], "how_to_apply": "POST audio to /transcribe",
    },
    {
        "slug": "web-dashboard", "title": "Web Dashboard",
        "one_liner": "React monitoring dashboard.",
        "repo_url": "https://github.com/u/web-dashboard",
        "tech": ["javascript", "react"], "reuse_tags": ["charts"],
        "patterns": [], "how_to_apply": "",
    },
]


class _FakeStore:
    """Returns canned rows so the merge logic is tested without real vectors."""
    def __init__(self, rows):
        self._rows = rows

    def search(self, query_vec, limit=10):
        return self._rows[:limit]


def _row(repo_name, distance, text):
    return {"repo_name": repo_name, "distance": distance, "text": text}


def test_reuse_check_returns_candidates_with_provenance():
    from ghps.reuse import reuse_check
    store = _FakeStore([
        _row("parakeet-asr-service", 0.2, "streaming ASR pipeline README excerpt"),
        _row("web-dashboard", 0.7, "react dashboard charts"),
    ])
    out = reuse_check(store, _FakeEmbedder(), _PROJECTS,
                      "streaming speech to text transcription", k=5, min_score=0.5)
    assert out["verdict"] == "candidates"
    assert out["source"].startswith("description:")
    top = out["candidates"][0]
    assert top["repo"] == "parakeet-asr-service"      # 1.0-0.2 = 0.8 >= 0.5
    assert top["score"] == 0.8
    assert top["reuse_tags"] == ["asr", "streaming-transcription"]
    assert top["how_to_apply"] == "POST audio to /transcribe"
    assert "snippet" in top["why"] and top["why"]["snippet"]
    assert isinstance(top["why"]["matched_fields"], list)
    # web-dashboard scored 0.3 (< min_score) → filtered out
    assert [c["repo"] for c in out["candidates"]] == ["parakeet-asr-service"]


def test_reuse_check_greenfield_when_nothing_passes_threshold():
    from ghps.reuse import reuse_check
    store = _FakeStore([_row("web-dashboard", 0.9, "react dashboard")])  # score 0.1
    out = reuse_check(store, _FakeEmbedder(), _PROJECTS, "quantum compiler", min_score=0.5)
    assert out["verdict"] == "greenfield"
    assert out["candidates"] == []
