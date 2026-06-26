from ghps.narrate.store import Store


def test_cursor_roundtrip(tmp_path):
    s = Store(tmp_path)
    assert s.read_cursor("riff") is None
    s.write_cursor("riff", "2026-06-20T00:00:00Z")
    assert s.read_cursor("riff") == "2026-06-20T00:00:00Z"


def test_pr_roundtrip_and_key(tmp_path):
    s = Store(tmp_path)
    s.put_pr({"repo": "riff", "pr_number": 12, "title": "x"})
    assert s.get_pr("riff", 12)["title"] == "x"
    assert len(s.all_prs()) == 1


def test_ledger_last_decision_wins(tmp_path):
    s = Store(tmp_path)
    s.append_ledger({"repo": "riff", "pr_number": 3, "theme_id": "t1"})
    s.append_ledger({"repo": "riff", "pr_number": 3, "theme_id": "t2"})
    assert s.ledger_decision("riff", 3)["theme_id"] == "t2"


def test_theme_roundtrip(tmp_path):
    s = Store(tmp_path)
    s.put_theme({"theme_id": "t1", "slug": "a"})
    assert s.get_theme("t1")["slug"] == "a"
    assert len(s.all_themes()) == 1
