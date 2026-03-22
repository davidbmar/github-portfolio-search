#!/usr/bin/env python3
"""CLI tool to manage access requests for GitHub Portfolio Search.

Usage:
    python3 scripts/approve-access.py approve user@example.com
    python3 scripts/approve-access.py deny user@example.com
    python3 scripts/approve-access.py list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ACCESS_FILE = Path.home() / ".ghps" / "access.json"


def _load_access_list(path: Optional[Path] = None) -> dict:
    """Load the access list from disk."""
    p = path or ACCESS_FILE
    if not p.exists():
        return {"users": {}}
    with open(p) as f:
        return json.load(f)


def _save_access_list(data: dict, path: Optional[Path] = None) -> None:
    """Save the access list to disk."""
    p = path or ACCESS_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def approve_user(email: str, path: Optional[Path] = None) -> str:
    """Approve a user's access request. Returns status message."""
    data = _load_access_list(path)
    now = datetime.now(timezone.utc).isoformat()
    if email in data["users"]:
        data["users"][email]["status"] = "approved"
        data["users"][email]["updated_at"] = now
    else:
        data["users"][email] = {"status": "approved", "updated_at": now}
    _save_access_list(data, path)
    return f"Approved: {email}"


def deny_user(email: str, path: Optional[Path] = None) -> str:
    """Deny a user's access request. Returns status message."""
    data = _load_access_list(path)
    now = datetime.now(timezone.utc).isoformat()
    if email in data["users"]:
        data["users"][email]["status"] = "denied"
        data["users"][email]["updated_at"] = now
    else:
        data["users"][email] = {"status": "denied", "updated_at": now}
    _save_access_list(data, path)
    return f"Denied: {email}"


def list_users(path: Optional[Path] = None) -> str:
    """List all users and their access status. Returns formatted string."""
    data = _load_access_list(path)
    users = data.get("users", {})
    if not users:
        return "No access requests found."
    lines = []
    for email, info in sorted(users.items()):
        status = info.get("status", "unknown")
        updated = info.get("updated_at", "")
        lines.append(f"  {email}: {status} (updated: {updated})")
    return "Access list:\n" + "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage access requests for GitHub Portfolio Search"
    )
    parser.add_argument(
        "action",
        choices=["approve", "deny", "list"],
        help="Action to perform",
    )
    parser.add_argument(
        "email",
        nargs="?",
        help="User email (required for approve/deny)",
    )
    args = parser.parse_args(argv)

    if args.action in ("approve", "deny") and not args.email:
        parser.error(f"{args.action} requires an email argument")

    if args.action == "approve":
        print(approve_user(args.email))
    elif args.action == "deny":
        print(deny_user(args.email))
    elif args.action == "list":
        print(list_users())

    return 0


if __name__ == "__main__":
    sys.exit(main())
