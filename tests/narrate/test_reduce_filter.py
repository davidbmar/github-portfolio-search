from ghps.narrate.reduce import is_signal_file, select_evidence, manifest

def test_ignore_lockfiles_and_generated():
    assert not is_signal_file("package-lock.json")
    assert not is_signal_file("web/data/projects.json")
    assert not is_signal_file("dist/app.min.js")
    assert is_signal_file("src/ghps/daily.py")

def test_select_evidence_prioritizes_tests(tmp_files=None):
    files = [
        {"path": "src/a.py", "status": "modified", "adds": 2, "dels": 0, "patch": "x" * 5000},
        {"path": "tests/test_a.py", "status": "added", "adds": 50, "dels": 0, "patch": "assert"},
        {"path": "package-lock.json", "status": "modified", "adds": 999, "dels": 0, "patch": "noise"},
    ]
    ev = select_evidence(files, max_files=2, max_patch_chars=100)
    paths = [e["path"] for e in ev]
    assert "tests/test_a.py" in paths            # test prioritized
    assert "package-lock.json" not in paths      # ignored
    assert all(len(e["excerpt"]) <= 100 for e in ev)

def test_manifest_includes_all_with_lang():
    files = [{"path": "a.py", "status": "modified", "adds": 1, "dels": 0, "patch": ""}]
    m = manifest(files)
    assert m[0]["lang"] == "python"
