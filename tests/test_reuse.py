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
