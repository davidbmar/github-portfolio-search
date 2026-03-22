"""Tests for auth module and auth/access API endpoints."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.auth import (
    _load_access_data,
    _save_access_data,
    add_pending_request,
    approve_email,
    deny_email,
    get_pending_requests,
    is_approved,
    verify_token,
)


# ---------------------------------------------------------------------------
# Unit tests for auth.py functions
# ---------------------------------------------------------------------------

class TestAccessList:
    """Tests for access-list CRUD operations using a temp file."""

    @pytest.fixture(autouse=True)
    def access_file(self, tmp_path):
        self.path = tmp_path / "access.json"

    def test_empty_access_file(self):
        data = _load_access_data(self.path)
        assert data == {"approved": [], "pending": []}

    def test_approve_email(self):
        approve_email("alice@example.com", self.path)
        assert is_approved("alice@example.com", self.path)

    def test_approve_is_case_insensitive(self):
        approve_email("Alice@Example.com", self.path)
        assert is_approved("alice@example.com", self.path)

    def test_approve_no_duplicates(self):
        approve_email("alice@example.com", self.path)
        approve_email("alice@example.com", self.path)
        data = _load_access_data(self.path)
        assert len(data["approved"]) == 1

    def test_deny_removes_from_pending(self):
        add_pending_request("bob@example.com", "Bob", "please", self.path)
        assert len(get_pending_requests(self.path)) == 1
        deny_email("bob@example.com", self.path)
        assert len(get_pending_requests(self.path)) == 0

    def test_add_pending_request(self):
        add_pending_request("bob@example.com", "Bob", "I want access", self.path)
        pending = get_pending_requests(self.path)
        assert len(pending) == 1
        assert pending[0]["email"] == "bob@example.com"
        assert pending[0]["name"] == "Bob"
        assert pending[0]["reason"] == "I want access"
        assert "requested_at" in pending[0]

    def test_pending_no_duplicates(self):
        add_pending_request("bob@example.com", "Bob", "reason1", self.path)
        add_pending_request("bob@example.com", "Bob", "reason2", self.path)
        assert len(get_pending_requests(self.path)) == 1

    def test_approve_removes_from_pending(self):
        add_pending_request("carol@example.com", "Carol", "reason", self.path)
        assert len(get_pending_requests(self.path)) == 1
        approve_email("carol@example.com", self.path)
        assert is_approved("carol@example.com", self.path)
        assert len(get_pending_requests(self.path)) == 0

    def test_is_approved_false_for_unknown(self):
        assert not is_approved("unknown@example.com", self.path)

    def test_persistence(self):
        approve_email("alice@example.com", self.path)
        add_pending_request("bob@example.com", "Bob", "reason", self.path)
        # Re-load from disk
        data = _load_access_data(self.path)
        assert "alice@example.com" in data["approved"]
        assert len(data["pending"]) == 1


class TestVerifyToken:
    """Tests for Google JWT token verification (mocked)."""

    def test_valid_token(self):
        mock_idinfo = {
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "sub": "12345",
        }
        with patch("ghps.auth.id_token.verify_oauth2_token", return_value=mock_idinfo):
            result = verify_token("fake-jwt-token")
            assert result["email"] == "user@example.com"
            assert result["name"] == "Test User"
            assert result["sub"] == "12345"

    def test_invalid_token(self):
        with patch(
            "ghps.auth.id_token.verify_oauth2_token",
            side_effect=ValueError("Token expired"),
        ):
            with pytest.raises(ValueError, match="Invalid token"):
                verify_token("expired-token")


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

ADMIN_TOKEN = "test-admin-secret"


@pytest.fixture
def auth_client(tmp_path):
    """TestClient for the real FastAPI app with auth endpoints, using a temp access file."""
    access_file = tmp_path / "access.json"

    # Patch the auth module to use our temp file and mock token verification
    with patch.dict(os.environ, {"GHPS_ADMIN_TOKEN": ADMIN_TOKEN}):
        # Re-import to pick up the env var
        import ghps.api as api_module
        api_module.ADMIN_TOKEN = ADMIN_TOKEN

        # Patch auth functions to use temp path
        original_is_approved = api_module.auth.is_approved
        original_add_pending = api_module.auth.add_pending_request
        original_get_pending = api_module.auth.get_pending_requests
        original_approve = api_module.auth.approve_email
        original_deny = api_module.auth.deny_email

        api_module.auth.is_approved = lambda email: original_is_approved(email, access_file)
        api_module.auth.add_pending_request = lambda e, n, r: original_add_pending(e, n, r, access_file)
        api_module.auth.get_pending_requests = lambda: original_get_pending(access_file)
        api_module.auth.approve_email = lambda email: original_approve(email, access_file)
        api_module.auth.deny_email = lambda email: original_deny(email, access_file)

        client = TestClient(api_module.app, raise_server_exceptions=False)
        yield client

        # Restore originals
        api_module.auth.is_approved = original_is_approved
        api_module.auth.add_pending_request = original_add_pending
        api_module.auth.get_pending_requests = original_get_pending
        api_module.auth.approve_email = original_approve
        api_module.auth.deny_email = original_deny


class TestAuthVerifyEndpoint:
    def test_valid_token_not_approved(self, auth_client):
        mock_idinfo = {
            "email": "new@example.com",
            "name": "New User",
            "picture": "",
            "sub": "99",
        }
        with patch("ghps.auth.id_token.verify_oauth2_token", return_value=mock_idinfo):
            resp = auth_client.post("/api/auth/verify", json={"token": "valid-jwt"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["ok"] is True
            assert body["data"]["user"]["email"] == "new@example.com"
            assert body["data"]["approved"] is False

    def test_invalid_token(self, auth_client):
        with patch(
            "ghps.auth.id_token.verify_oauth2_token",
            side_effect=ValueError("bad token"),
        ):
            resp = auth_client.post("/api/auth/verify", json={"token": "bad"})
            assert resp.status_code == 401


class TestAccessRequestEndpoint:
    def test_submit_request(self, auth_client):
        resp = auth_client.post(
            "/api/access/request",
            json={"email": "requester@example.com", "name": "Requester", "reason": "please"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_pending_requires_admin(self, auth_client):
        resp = auth_client.get("/api/access/pending")
        assert resp.status_code == 403
        assert resp.json()["ok"] is False

    def test_pending_with_admin_token(self, auth_client):
        # Submit a request first
        auth_client.post(
            "/api/access/request",
            json={"email": "requester@example.com", "name": "Requester", "reason": "please"},
        )
        resp = auth_client.get(
            "/api/access/pending",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert len(body["data"]["pending"]) == 1


class TestAccessApproveEndpoint:
    def test_approve_requires_admin(self, auth_client):
        resp = auth_client.post(
            "/api/access/approve", json={"email": "someone@example.com"}
        )
        assert resp.json()["ok"] is False

    def test_approve_flow(self, auth_client):
        # Submit request
        auth_client.post(
            "/api/access/request",
            json={"email": "carol@example.com", "name": "Carol", "reason": "testing"},
        )
        # Approve
        resp = auth_client.post(
            "/api/access/approve",
            json={"email": "carol@example.com"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Pending should be empty now
        resp = auth_client.get(
            "/api/access/pending",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert len(resp.json()["data"]["pending"]) == 0


class TestAccessDenyEndpoint:
    def test_deny_requires_admin(self, auth_client):
        resp = auth_client.post(
            "/api/access/deny", json={"email": "someone@example.com"}
        )
        assert resp.json()["ok"] is False

    def test_deny_removes_pending(self, auth_client):
        auth_client.post(
            "/api/access/request",
            json={"email": "dave@example.com", "name": "Dave", "reason": "testing"},
        )
        resp = auth_client.post(
            "/api/access/deny",
            json={"email": "dave@example.com"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        resp = auth_client.get(
            "/api/access/pending",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert len(resp.json()["data"]["pending"]) == 0
