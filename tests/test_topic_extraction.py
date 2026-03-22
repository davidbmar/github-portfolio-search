"""Tests for topic extraction from README content and repo names."""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.indexer import Indexer


class TestExtractTopics:
    """Unit tests for Indexer.extract_topics()."""

    def test_aws_lambda_s3_from_readme(self):
        """Given a README containing 'AWS Lambda S3', inferred topics should include aws, lambda, s3."""
        topics = Indexer.extract_topics("my-repo", "This project uses AWS Lambda S3 for processing.")
        assert "aws" in topics
        assert "lambda" in topics
        assert "s3" in topics

    def test_keywords_from_repo_name(self):
        """Keywords in repo name (split on hyphens) should be detected."""
        topics = Indexer.extract_topics("docker-cli-tool", "")
        assert "docker" in topics
        assert "cli" in topics

    def test_keywords_from_repo_name_underscores(self):
        """Keywords in repo name (split on underscores) should be detected."""
        topics = Indexer.extract_topics("fastapi_backend", "")
        assert "fastapi" in topics
        assert "backend" in topics

    def test_case_insensitive_readme(self):
        """Keyword matching in README should be case-insensitive."""
        topics = Indexer.extract_topics("repo", "Built with REACT and TYPESCRIPT")
        assert "react" in topics
        assert "typescript" in topics

    def test_deduplication(self):
        """Topics appearing in both name and README should not be duplicated."""
        topics = Indexer.extract_topics("docker-app", "Uses Docker for containerization")
        assert topics.count("docker") == 1

    def test_empty_readme_and_generic_name(self):
        """A repo with empty README and no keyword name returns empty list."""
        topics = Indexer.extract_topics("my-project", "")
        assert topics == []

    def test_multiple_keywords_in_readme(self):
        """Multiple distinct keywords should all be extracted."""
        readme = """
        # Voice Transcription Service
        Uses whisper for STT, deployed on kubernetes with terraform.
        WebRTC streaming for real-time audio.
        """
        topics = Indexer.extract_topics("voice-app", readme)
        assert "voice" in topics
        assert "whisper" in topics
        assert "stt" in topics
        assert "kubernetes" in topics
        assert "terraform" in topics
        assert "webrtc" in topics
        assert "streaming" in topics

    def test_sorted_output(self):
        """Output should be sorted alphabetically."""
        topics = Indexer.extract_topics("repo", "python react docker")
        assert topics == sorted(topics)

    def test_hyphenated_keywords(self):
        """Hyphenated keywords like 'api-gateway' should be matched."""
        topics = Indexer.extract_topics("repo", "Configured the api-gateway and state-machine")
        assert "api-gateway" in topics
        assert "state-machine" in topics
