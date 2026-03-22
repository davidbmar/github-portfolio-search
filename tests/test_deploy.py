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
