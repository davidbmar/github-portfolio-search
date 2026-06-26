from pathlib import Path
from ghps.narrate.render import write_tutorial_prose, render_learn_html, write_learn_pages


class _Client:
    def complete_json(self, system, user):
        return {"summary": "S", "narrative": "<b>N</b>", "principles": ["p1"],
                "patterns": ["pat"], "applied_examples": ["ex"], "pitfalls": ["pit"]}


def _theme():
    return {"theme_id": "t1", "slug": "llm-judge-routing", "title": "LLM Judge Routing",
            "status": "mature", "repos": ["riff"], "pr_numbers": [1]}


def test_write_tutorial_prose_fills_fields():
    t = write_tutorial_prose(_theme(), [], _Client(), model="qwen3.7-plus")
    assert t["summary"] == "S" and t["principles"] == ["p1"]


def test_render_escapes_html():
    t = _theme(); t.update({"summary": "S", "narrative": "<script>x</script>",
                            "principles": [], "patterns": [], "applied_examples": [], "pitfalls": []})
    html = render_learn_html(t)
    assert "<script>x</script>" not in html and "&lt;script&gt;" in html


def test_write_learn_pages_creates_index(tmp_path):
    t = _theme(); t.update({"summary": "S", "narrative": "N", "principles": [],
                            "patterns": [], "applied_examples": [], "pitfalls": []})
    paths = write_learn_pages([t], tmp_path)
    assert (Path(tmp_path) / "llm-judge-routing.html").exists()
    assert (Path(tmp_path) / "index.html").exists()
