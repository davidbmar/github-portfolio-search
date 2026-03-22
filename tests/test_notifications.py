"""Tests for notifications module and approve-access CLI."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ghps.notifications import (
    format_access_request_message,
    format_access_request_message_with_links,
    notify_access_request,
    send_telegram_message,
)


# ---------------------------------------------------------------------------
# Notification formatting tests
# ---------------------------------------------------------------------------


class TestFormatAccessRequestMessage:
    def test_basic_format(self):
        msg = format_access_request_message("Alice", "alice@example.com", "Need access")
        assert "Alice" in msg
        assert "alice@example.com" in msg
        assert "Need access" in msg
        assert "\U0001f514" in msg  # bell emoji

    def test_special_characters_in_reason(self):
        msg = format_access_request_message("Bob", "bob@co.uk", "R&D project — urgent")
        assert "bob@co.uk" in msg
        assert "R&D project" in msg


class TestFormatAccessRequestMessageWithLinks:
    def test_includes_approve_deny_links(self):
        msg = format_access_request_message_with_links(
            "Alice", "alice@example.com", "Need access", "https://api.example.com"
        )
        assert "Approve" in msg
        assert "Deny" in msg
        assert "https://api.example.com/access/approve?email=alice%40example.com" in msg
        assert "https://api.example.com/access/deny?email=alice%40example.com" in msg

    def test_email_is_url_encoded(self):
        msg = format_access_request_message_with_links(
            "Bob", "bob+test@example.com", "testing", "https://api.test"
        )
        assert "bob%2Btest%40example.com" in msg


# ---------------------------------------------------------------------------
# Telegram send tests
# ---------------------------------------------------------------------------


class TestSendTelegramMessage:
    def test_no_credentials_logs_and_returns_false(self, caplog):
        """When no env vars set, should log and return False."""
        env = {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            os.environ.pop("TELEGRAM_CHAT_ID", None)
            result = send_telegram_message("test message")
        assert result is False

    @patch("ghps.notifications.urllib.request.urlopen")
    def test_successful_send(self, mock_urlopen):
        """When credentials set and API responds 200, return True."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        env = {"TELEGRAM_BOT_TOKEN": "fake-token", "TELEGRAM_CHAT_ID": "12345"}
        with patch.dict(os.environ, env):
            result = send_telegram_message("hello")

        assert result is True
        mock_urlopen.assert_called_once()

    @patch("ghps.notifications.urllib.request.urlopen")
    def test_api_error_returns_false(self, mock_urlopen):
        """Network error should return False, not raise."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        env = {"TELEGRAM_BOT_TOKEN": "fake-token", "TELEGRAM_CHAT_ID": "12345"}
        with patch.dict(os.environ, env):
            result = send_telegram_message("hello")
        assert result is False


class TestNotifyAccessRequest:
    @patch("ghps.notifications.send_telegram_message")
    def test_without_api_base_url(self, mock_send):
        mock_send.return_value = True
        result = notify_access_request("Alice", "alice@example.com", "Need access")
        assert result is True
        msg = mock_send.call_args[0][0]
        assert "Approve" not in msg

    @patch("ghps.notifications.send_telegram_message")
    def test_with_api_base_url(self, mock_send):
        mock_send.return_value = True
        result = notify_access_request(
            "Alice", "alice@example.com", "Need access", "https://api.test"
        )
        assert result is True
        msg = mock_send.call_args[0][0]
        assert "Approve" in msg
        assert "Deny" in msg


# ---------------------------------------------------------------------------
# Access list management tests (approve-access.py)
# ---------------------------------------------------------------------------

# Import the script functions
from importlib.util import spec_from_file_location, module_from_spec

_spec = spec_from_file_location(
    "approve_access",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "approve-access.py"),
)
_approve_access = module_from_spec(_spec)
_spec.loader.exec_module(_approve_access)

approve_user = _approve_access.approve_user
deny_user = _approve_access.deny_user
list_users = _approve_access.list_users
main = _approve_access.main


class TestAccessListManagement:
    @pytest.fixture
    def access_file(self, tmp_path):
        return tmp_path / "access.json"

    def test_approve_new_user(self, access_file):
        result = approve_user("alice@example.com", path=access_file)
        assert "Approved" in result
        data = json.loads(access_file.read_text())
        assert data["users"]["alice@example.com"]["status"] == "approved"

    def test_deny_new_user(self, access_file):
        result = deny_user("bob@example.com", path=access_file)
        assert "Denied" in result
        data = json.loads(access_file.read_text())
        assert data["users"]["bob@example.com"]["status"] == "denied"

    def test_approve_then_deny(self, access_file):
        approve_user("alice@example.com", path=access_file)
        deny_user("alice@example.com", path=access_file)
        data = json.loads(access_file.read_text())
        assert data["users"]["alice@example.com"]["status"] == "denied"

    def test_list_empty(self, access_file):
        result = list_users(path=access_file)
        assert "No access requests" in result

    def test_list_with_users(self, access_file):
        approve_user("alice@example.com", path=access_file)
        deny_user("bob@example.com", path=access_file)
        result = list_users(path=access_file)
        assert "alice@example.com" in result
        assert "approved" in result
        assert "bob@example.com" in result
        assert "denied" in result

    def test_list_preserves_multiple_users(self, access_file):
        approve_user("a@test.com", path=access_file)
        approve_user("b@test.com", path=access_file)
        deny_user("c@test.com", path=access_file)
        data = json.loads(access_file.read_text())
        assert len(data["users"]) == 3


class TestApproveAccessCLI:
    def test_approve_cli(self, capsys, tmp_path):
        access_file = tmp_path / "access.json"
        with patch.object(_approve_access, "ACCESS_FILE", access_file):
            main(["approve", "user@test.com"])
        out = capsys.readouterr().out
        assert "Approved" in out

    def test_deny_cli(self, capsys, tmp_path):
        access_file = tmp_path / "access.json"
        with patch.object(_approve_access, "ACCESS_FILE", access_file):
            main(["deny", "user@test.com"])
        out = capsys.readouterr().out
        assert "Denied" in out

    def test_list_cli(self, capsys, tmp_path):
        access_file = tmp_path / "access.json"
        with patch.object(_approve_access, "ACCESS_FILE", access_file):
            main(["list"])
        out = capsys.readouterr().out
        assert "No access requests" in out

    def test_approve_without_email_errors(self):
        with pytest.raises(SystemExit):
            main(["approve"])
