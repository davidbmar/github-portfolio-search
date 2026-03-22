"""Telegram notification support for access requests."""

import json
import logging
import os
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)


def _get_telegram_config():
    """Return (bot_token, chat_id) from env, or (None, None) if not configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    return token, chat_id


def format_access_request_message(name: str, email: str, reason: str) -> str:
    """Format an access request notification message."""
    return f"\U0001f514 Access Request: {name} ({email}) \u2014 {reason}"


def format_access_request_message_with_links(
    name: str, email: str, reason: str, api_base_url: str
) -> str:
    """Format an access request message with approve/deny links."""
    encoded_email = urllib.parse.quote(email)
    msg = format_access_request_message(name, email, reason)
    msg += (
        f"\n\n[Approve]({api_base_url}/access/approve?email={encoded_email})"
        f"  |  [Deny]({api_base_url}/access/deny?email={encoded_email})"
    )
    return msg


def send_telegram_message(text: str, parse_mode: str = "Markdown") -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    token, chat_id = _get_telegram_config()
    if not token or not chat_id:
        logger.info("Telegram not configured — logging message instead: %s", text)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    ).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("Failed to send Telegram message: %s", exc)
        return False


def notify_access_request(
    name: str, email: str, reason: str, api_base_url: str = ""
) -> bool:
    """Send a Telegram notification for a new access request.

    If api_base_url is provided, approve/deny links are included.
    Falls back to logging if Telegram is not configured.
    """
    if api_base_url:
        text = format_access_request_message_with_links(
            name, email, reason, api_base_url
        )
    else:
        text = format_access_request_message(name, email, reason)

    return send_telegram_message(text)
