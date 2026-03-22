"""Tests for the static JSON data export module."""

from __future__ import annotations

import json
import os

import pytest
from click.testing import CliRunner

from ghps.export import export_static_bundle, _build_repos, _build_clusters, _build_search_index, _build_similarity, _build_suggestions


class TestExportStaticBundle:
    """Tests for the top-level export_static_bundle function."""

    def test_creates_output_directory(self, mock_store, tmp_path):
        out = str(tmp_path / "nested" / "output")
        export_static_bundle(mock_store, out)
        assert os.path.isdir(out)

    def test_generates_all_files(self, mock_store, tmp_path):
        out = str(tmp_path / "data")
        paths = export_static_bundle(mock_store, out)
        assert "repos.json" in paths
        assert "clusters.json" in paths
        assert "search-index.json" in paths
        assert "similarity.json" in paths
        assert "suggestions.json" in paths
        for name, path in paths.items():
            assert os.path.isfile(path), f"{name} was not written"

    def test_returns_absolute_paths(self, mock_store, tmp_path):
        out = str(tmp_path / "data")
        paths = export_static_bundle(mock_store, out)
        for path in paths.values():
            assert os.path.isabs(path)

    def test_all_files_are_valid_json(self, mock_store, tmp_path):
        out = str(tmp_path / "data")
        export_static_bundle(mock_store, out)
        for name in ("repos.json", "clusters.json", "search-index.json"):
            with open(os.path.join(out, name)) as f:
                data = json.load(f)
            assert isinstance(data, list), f"{name} should be a JSON array"
        # similarity.json and suggestions.json are dicts
        for name in ("similarity.json", "suggestions.json"):
            with open(os.path.join(out, name)) as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{name} should be a JSON object"


class TestBuildRepos:
    """Tests for repos.json generation."""

    def test_contains_all_repos(self, mock_store):
        repos = _build_repos(mock_store)
        names = {r["name"] for r in repos}
        assert names == {"ml-pipeline", "web-dashboard", "cli-toolkit"}

    def test_repo_has_required_fields(self, mock_store):
        repos = _build_repos(mock_store)
        required = {"name", "description", "language", "topics", "stars", "updated_at", "url", "readme_excerpt"}
        for repo in repos:
            assert required.issubset(repo.keys()), f"Missing fields in {repo['name']}"

    def test_topics_are_lists(self, mock_store):
        repos = _build_repos(mock_store)
        for repo in repos:
            assert isinstance(repo["topics"], list), f"Topics should be a list for {repo['name']}"

    def test_stars_are_integers(self, mock_store):
        repos = _build_repos(mock_store)
        for repo in repos:
            assert isinstance(repo["stars"], int), f"Stars should be int for {repo['name']}"

    def test_repos_sorted_by_relevance_score(self, mock_store):
        repos = _build_repos(mock_store)
        scores = [r["relevance_score"] for r in repos]
        assert scores == sorted(scores, reverse=True)

    def test_ml_pipeline_metadata(self, mock_store):
        repos = _build_repos(mock_store)
        ml = next(r for r in repos if r["name"] == "ml-pipeline")
        assert ml["language"] == "Python"
        assert ml["stars"] == 120
        assert "machine-learning" in ml["topics"]
        assert ml["url"] == "https://github.com/user/ml-pipeline"


class TestBuildClusters:
    """Tests for clusters.json generation."""

    def test_returns_list(self, mock_store):
        clusters = _build_clusters(mock_store)
        assert isinstance(clusters, list)

    def test_clusters_have_name_and_repos(self, mock_store):
        clusters = _build_clusters(mock_store)
        for c in clusters:
            assert "name" in c
            assert "repos" in c
            assert isinstance(c["repos"], list)
            assert len(c["repos"]) > 0

    def test_all_repos_assigned_to_cluster(self, mock_store):
        clusters = _build_clusters(mock_store)
        all_repos = set()
        for c in clusters:
            all_repos.update(c["repos"])
        assert all_repos == {"ml-pipeline", "web-dashboard", "cli-toolkit"}

    def test_no_centroid_in_output(self, mock_store):
        """Clusters export should not include centroid vectors (too large for web)."""
        clusters = _build_clusters(mock_store)
        for c in clusters:
            assert "centroid" not in c

    def test_clusters_have_unique_names(self, mock_store):
        """Every cluster must have a distinct name — no duplicates."""
        clusters = _build_clusters(mock_store)
        names = [c["name"] for c in clusters]
        assert len(names) == len(set(names)), f"Duplicate cluster names found: {names}"

    def test_clusters_meet_minimum_size(self, mock_store):
        """No cluster should have fewer than 3 repos (unless total repos < 3)."""
        clusters = _build_clusters(mock_store)
        total_repos = sum(len(c["repos"]) for c in clusters)
        if total_repos >= 3:
            for c in clusters:
                assert len(c["repos"]) >= 3 or len(clusters) == 1, (
                    f"Cluster '{c['name']}' has only {len(c['repos'])} repos"
                )


class TestBuildSearchIndex:
    """Tests for search-index.json generation."""

    def test_returns_list(self, mock_store):
        index = _build_search_index(mock_store)
        assert isinstance(index, list)

    def test_entry_per_repo(self, mock_store):
        index = _build_search_index(mock_store)
        repos = {e["repo"] for e in index}
        assert repos == {"ml-pipeline", "web-dashboard", "cli-toolkit"}

    def test_entry_has_keywords(self, mock_store):
        index = _build_search_index(mock_store)
        for entry in index:
            assert "keywords" in entry
            assert isinstance(entry["keywords"], list)
            assert len(entry["keywords"]) > 0

    def test_entry_has_chunks(self, mock_store):
        index = _build_search_index(mock_store)
        for entry in index:
            assert "chunks" in entry
            assert isinstance(entry["chunks"], list)
            assert len(entry["chunks"]) > 0

    def test_chunk_has_source_and_text(self, mock_store):
        index = _build_search_index(mock_store)
        for entry in index:
            for chunk in entry["chunks"]:
                assert "source" in chunk
                assert "text" in chunk

    def test_keywords_sorted_and_unique(self, mock_store):
        index = _build_search_index(mock_store)
        for entry in index:
            kw = entry["keywords"]
            assert kw == sorted(set(kw)), f"Keywords not sorted/unique for {entry['repo']}"

    def test_chunk_text_truncated(self, mock_store):
        index = _build_search_index(mock_store)
        for entry in index:
            for chunk in entry["chunks"]:
                assert len(chunk["text"]) <= 200


class TestBuildReposReadmeExcerpt:
    """Tests for readme_excerpt in repos.json."""

    def test_readme_excerpt_present(self, mock_store):
        repos = _build_repos(mock_store)
        for repo in repos:
            assert "readme_excerpt" in repo
            assert isinstance(repo["readme_excerpt"], str)

    def test_readme_excerpt_max_length(self, mock_store):
        repos = _build_repos(mock_store)
        for repo in repos:
            assert len(repo["readme_excerpt"]) <= 300

    def test_readme_excerpt_content(self, mock_store):
        repos = _build_repos(mock_store)
        ml = next(r for r in repos if r["name"] == "ml-pipeline")
        assert "machine learning" in ml["readme_excerpt"].lower()


class TestBuildSimilarity:
    """Tests for similarity.json generation."""

    def test_returns_dict(self, mock_store):
        sim = _build_similarity(mock_store)
        assert isinstance(sim, dict)

    def test_all_repos_present(self, mock_store):
        sim = _build_similarity(mock_store)
        assert set(sim.keys()) == {"ml-pipeline", "web-dashboard", "cli-toolkit"}

    def test_scores_between_0_and_1(self, mock_store):
        sim = _build_similarity(mock_store)
        for repo, similar in sim.items():
            for entry in similar:
                assert 0 <= entry["score"] <= 1.0, (
                    f"Score {entry['score']} out of range for {repo} -> {entry['name']}"
                )

    def test_at_most_8_entries_per_repo(self, mock_store):
        sim = _build_similarity(mock_store)
        for repo, similar in sim.items():
            assert len(similar) <= 8, f"{repo} has {len(similar)} similar repos (max 8)"

    def test_entries_have_name_and_score(self, mock_store):
        sim = _build_similarity(mock_store)
        for repo, similar in sim.items():
            for entry in similar:
                assert "name" in entry
                assert "score" in entry

    def test_does_not_include_self(self, mock_store):
        sim = _build_similarity(mock_store)
        for repo, similar in sim.items():
            names = [e["name"] for e in similar]
            assert repo not in names, f"{repo} listed as similar to itself"

    def test_sorted_by_score_descending(self, mock_store):
        sim = _build_similarity(mock_store)
        for repo, similar in sim.items():
            scores = [e["score"] for e in similar]
            assert scores == sorted(scores, reverse=True)

    def test_empty_store_returns_empty(self, tmp_path):
        from ghps.store import VectorStore
        store = VectorStore(":memory:")
        store.create_index()
        sim = _build_similarity(store)
        assert sim == {}
        store.close()


class TestBuildSuggestions:
    """Tests for suggestions.json generation."""

    def test_returns_dict_with_correct_keys(self, mock_store):
        sug = _build_suggestions(mock_store)
        assert isinstance(sug, dict)
        assert "repos" in sug
        assert "topics" in sug
        assert "queries" in sug

    def test_repos_list_contents(self, mock_store):
        sug = _build_suggestions(mock_store)
        assert set(sug["repos"]) == {"ml-pipeline", "web-dashboard", "cli-toolkit"}

    def test_topics_are_sorted_strings(self, mock_store):
        sug = _build_suggestions(mock_store)
        assert isinstance(sug["topics"], list)
        assert sug["topics"] == sorted(sug["topics"])
        for t in sug["topics"]:
            assert isinstance(t, str)

    def test_queries_is_list(self, mock_store):
        sug = _build_suggestions(mock_store)
        assert isinstance(sug["queries"], list)

    def test_works_without_analytics_db(self, mock_store, monkeypatch):
        """Suggestions should work even when analytics DB doesn't exist."""
        monkeypatch.setattr("os.path.exists", lambda p: False if "analytics" in p else os.path.exists(p))
        sug = _build_suggestions(mock_store)
        assert isinstance(sug["queries"], list)
        assert sug["queries"] == []

    def test_topics_include_known_values(self, mock_store):
        sug = _build_suggestions(mock_store)
        assert "machine-learning" in sug["topics"]
        assert "react" in sug["topics"]


class TestExportCLI:
    """Tests for the ghps export CLI command."""

    def test_export_missing_db(self, tmp_path):
        from ghps.cli import main
        runner = CliRunner()
        result = runner.invoke(main, ["export", "--db", str(tmp_path / "missing.db")])
        assert result.exit_code != 0
        assert "Index not found" in result.output or "Index not found" in (result.stderr or "")

    def test_export_produces_files(self, mock_store, tmp_path):
        """End-to-end CLI export using an in-memory store."""
        from unittest.mock import patch, MagicMock
        from ghps.cli import main

        out_dir = str(tmp_path / "web" / "data")
        runner = CliRunner()

        # The CLI does a lazy `from ghps.export import export_static_bundle`
        # and `from ghps.store import VectorStore` inside the function body.
        # We patch at the module level so the lazy import picks up our mocks.
        mock_vs_cls = MagicMock(return_value=mock_store)

        def real_export(store, output_dir):
            return export_static_bundle(mock_store, output_dir)

        with patch("ghps.cli._db_exists", return_value=True), \
             patch("ghps.store.VectorStore", mock_vs_cls), \
             patch("ghps.export.export_static_bundle", side_effect=real_export):
            result = runner.invoke(
                main,
                ["export", "--db", ":memory:", "--output", out_dir],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Export complete" in result.output

    def test_export_empty_store(self, tmp_path):
        """Export with an empty database should produce valid but empty JSON files."""
        from ghps.store import VectorStore

        store = VectorStore(":memory:")
        store.create_index()
        out_dir = str(tmp_path / "empty_export")

        paths = export_static_bundle(store, out_dir)

        with open(paths["repos.json"]) as f:
            assert json.load(f) == []
        with open(paths["clusters.json"]) as f:
            assert json.load(f) == []
        with open(paths["search-index.json"]) as f:
            assert json.load(f) == []
        with open(paths["similarity.json"]) as f:
            assert json.load(f) == {}
        with open(paths["suggestions.json"]) as f:
            data = json.load(f)
            assert data["repos"] == []
            assert data["topics"] == []
            assert data["queries"] == []

        store.close()
