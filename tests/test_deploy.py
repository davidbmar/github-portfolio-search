"""Tests for deploy.sh — verify it exists, is executable, and has correct config."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SCRIPT = PROJECT_ROOT / "deploy.sh"


class TestDeployScript:
    def test_deploy_script_exists(self):
        """deploy.sh must exist in the project root."""
        assert DEPLOY_SCRIPT.exists(), f"deploy.sh not found at {DEPLOY_SCRIPT}"

    def test_deploy_script_is_executable(self):
        """deploy.sh must have the executable bit set."""
        mode = DEPLOY_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "deploy.sh is not executable (missing user execute bit)"

    def test_deploy_script_has_correct_bucket(self):
        """deploy.sh must reference the correct S3 bucket."""
        content = DEPLOY_SCRIPT.read_text()
        assert "davidbmar-com" in content, "deploy.sh does not reference the davidbmar-com bucket"

    def test_deploy_script_has_cloudfront_distribution(self):
        """deploy.sh must reference the CloudFront distribution ID."""
        content = DEPLOY_SCRIPT.read_text()
        assert "E3RCY6XA80ANRT" in content, "deploy.sh missing CloudFront distribution ID"

    def test_deploy_script_checks_web_directory(self):
        """deploy.sh should check for the web/ directory before deploying."""
        content = DEPLOY_SCRIPT.read_text()
        assert "web/" in content, "deploy.sh does not reference web/ directory"

    def test_deploy_script_excludes_pyc(self):
        """deploy.sh should exclude .pyc files from the S3 sync."""
        content = DEPLOY_SCRIPT.read_text()
        assert "*.pyc" in content, "deploy.sh does not exclude .pyc files"

    def test_deploy_script_generates_deploy_manifest(self):
        """deploy.sh must generate web/deploy-manifest.json before S3 sync."""
        content = DEPLOY_SCRIPT.read_text()
        assert "deploy-manifest.json" in content, "deploy.sh does not generate deploy-manifest.json"
        # Manifest generation must appear before the S3 sync command
        manifest_pos = content.index("deploy-manifest.json")
        sync_pos = content.index("aws s3 sync")
        assert manifest_pos < sync_pos, "deploy-manifest.json must be generated before S3 sync"

    def test_deploy_script_generates_health_json(self):
        """deploy.sh must generate web/health.json before S3 sync."""
        content = DEPLOY_SCRIPT.read_text()
        assert "health.json" in content, "deploy.sh does not generate health.json"
        health_pos = content.index("health.json")
        sync_pos = content.index("aws s3 sync")
        assert health_pos < sync_pos, "health.json must be generated before S3 sync"

    def test_deploy_script_appends_deploy_log(self):
        """deploy.sh must append to .sprint/history/deploy-log.jsonl after deploy."""
        content = DEPLOY_SCRIPT.read_text()
        assert "deploy-log.jsonl" in content, "deploy.sh does not write to deploy-log.jsonl"
        # Deploy log must appear after S3 sync
        log_pos = content.index("deploy-log.jsonl")
        sync_pos = content.index("aws s3 sync")
        assert log_pos > sync_pos, "deploy-log.jsonl must be written after S3 sync"

    def test_deploy_manifest_has_required_fields(self):
        """deploy-manifest.json generation must include all required fields."""
        content = DEPLOY_SCRIPT.read_text()
        for field in ["project", "commit", "branch", "deployedAt", "repoCount", "clusterCount", "fileCount"]:
            assert field in content, f"deploy.sh missing '{field}' in deploy manifest"

    def test_health_json_has_required_fields(self):
        """health.json generation must include all required fields."""
        content = DEPLOY_SCRIPT.read_text()
        for field in ["status", "commit", "last_deploy", "repos"]:
            assert field in content, f"deploy.sh missing '{field}' in health.json"

    def test_deploy_script_prints_summary(self):
        """deploy.sh must print a summary with commit, repo count, and cluster count."""
        content = DEPLOY_SCRIPT.read_text()
        assert "Deployed commit" in content, "deploy.sh does not print deploy summary"
