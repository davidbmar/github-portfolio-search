"""Authentication and access-list management for GitHub Portfolio Search.

Verifies Google OAuth JWT tokens and maintains an access list of approved
emails in a JSON file at ~/.ghps/access.json.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)

# Default path for the access list JSON file
ACCESS_FILE = Path.home() / ".ghps" / "access.json"


def _load_access_data(path: Path | None = None) -> dict[str, Any]:
    """Load the access JSON file, returning a default structure if missing."""
    p = path or ACCESS_FILE
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {"approved": [], "pending": []}


def _save_access_data(data: dict[str, Any], path: Path | None = None) -> None:
    """Save the access JSON file, creating parent dirs if needed."""
    p = path or ACCESS_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)


def verify_token(token: str) -> dict[str, Any]:
    """Verify a Google OAuth JWT and return user info.

    Returns a dict with keys: email, name, picture, sub (Google user ID).
    Raises ValueError if the token is invalid or expired.
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request()
        )
        return {
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
            "sub": idinfo.get("sub", ""),
        }
    except Exception as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


def is_approved(email: str, path: Path | None = None) -> bool:
    """Check if an email is in the approved access list."""
    data = _load_access_data(path)
    return email.lower() in [e.lower() for e in data.get("approved", [])]


def approve_email(email: str, path: Path | None = None) -> None:
    """Add an email to the approved list and remove from pending."""
    data = _load_access_data(path)
    email_lower = email.lower()
    approved = data.get("approved", [])
    if email_lower not in [e.lower() for e in approved]:
        approved.append(email_lower)
    data["approved"] = approved
    # Remove from pending if present
    data["pending"] = [
        r for r in data.get("pending", [])
        if r.get("email", "").lower() != email_lower
    ]
    _save_access_data(data, path)


def deny_email(email: str, path: Path | None = None) -> None:
    """Remove an email from the pending list."""
    data = _load_access_data(path)
    data["pending"] = [
        r for r in data.get("pending", [])
        if r.get("email", "").lower() != email.lower()
    ]
    _save_access_data(data, path)


def add_pending_request(
    email: str, name: str, reason: str, path: Path | None = None
) -> None:
    """Add an access request to the pending list."""
    data = _load_access_data(path)
    pending = data.get("pending", [])
    # Don't add duplicates
    if any(r.get("email", "").lower() == email.lower() for r in pending):
        return
    pending.append({
        "email": email.lower(),
        "name": name,
        "reason": reason,
        "requested_at": int(time.time()),
    })
    data["pending"] = pending
    _save_access_data(data, path)


def get_pending_requests(path: Path | None = None) -> list[dict[str, Any]]:
    """Return all pending access requests."""
    data = _load_access_data(path)
    return data.get("pending", [])
