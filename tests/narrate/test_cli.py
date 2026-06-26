from click.testing import CliRunner
from ghps import cli
from ghps.narrate import pipeline
import ghps.docsgen.llm_client as llm_client_mod


def test_narrate_client_uses_get_client(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(llm_client_mod, "get_client", lambda provider=None: sentinel)
    assert cli._narrate_client("dashscope", "qwen-plus") is sentinel


def test_narrate_client_honors_model_override(monkeypatch):
    import ghps.docsgen.llm_client as llm
    monkeypatch.setattr(llm, "get_client", lambda provider=None: object())
    monkeypatch.delenv("DASHSCOPE_MODEL", raising=False)
    cli._narrate_client("dashscope", "qwen-custom-7")
    import os
    assert os.environ["DASHSCOPE_MODEL"] == "qwen-custom-7"


def test_narrate_invokes_pipeline(monkeypatch, tmp_path):
    captured = {}

    def fake_run(owner, repos, store, client, embedder, out_dir, **kw):
        captured.update(owner=owner, repos=repos)
        return {"prs": 2, "themes_matured": 1, "pages": ["x/index.html"]}

    monkeypatch.setattr(pipeline, "run", fake_run)
    # Avoid loading heavy clients:
    monkeypatch.setattr(cli, "_narrate_client", lambda provider, model: object(), raising=False)
    monkeypatch.setattr(cli, "_narrate_embedder", lambda: object(), raising=False)
    res = CliRunner().invoke(cli.main, ["narrate", "--owner", "davidbmar",
                                        "--repos", "riff", "--out", str(tmp_path),
                                        "--state", str(tmp_path / "s")])
    assert res.exit_code == 0
    assert captured["owner"] == "davidbmar" and captured["repos"] == ["riff"]
    assert "themes_matured" in res.output or "1" in res.output
