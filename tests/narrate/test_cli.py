from click.testing import CliRunner
from ghps import cli
from ghps.narrate import pipeline


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
