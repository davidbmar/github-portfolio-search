"""Lambda function to exchange GitHub OAuth code for access token.

Deployed behind API Gateway. The client sends { "code": "xxx" } and
receives { "access_token": "gho_xxx" }.

Environment variables:
  GITHUB_CLIENT_ID     — from GitHub OAuth App
  GITHUB_CLIENT_SECRET — from GitHub OAuth App
  ALLOWED_ORIGINS      — comma-separated (e.g., "https://davidbmar.com,http://localhost:8000")
"""

import json
import os
import urllib.request
import urllib.parse


def handler(event, context):
    # CORS headers
    allowed = os.environ.get("ALLOWED_ORIGINS", "https://davidbmar.com").split(",")
    origin = ""
    headers = event.get("headers", {}) or {}
    req_origin = headers.get("origin", headers.get("Origin", ""))
    if req_origin in allowed:
        origin = req_origin

    cors_headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
    }

    # Handle OPTIONS preflight
    if event.get("httpMethod") == "OPTIONS" or event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    # Parse request body
    try:
        body = json.loads(event.get("body", "{}"))
        code = body.get("code")
    except (json.JSONDecodeError, TypeError):
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "Invalid request body"}),
        }

    if not code:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": "Missing code parameter"}),
        }

    # Exchange code for token
    client_id = os.environ.get("GITHUB_CLIENT_ID", "")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")

    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }).encode()

    req = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=payload,
        headers={"Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_data = json.loads(resp.read().decode())
    except Exception as e:
        return {
            "statusCode": 502,
            "headers": cors_headers,
            "body": json.dumps({"error": f"GitHub token exchange failed: {e}"}),
        }

    if "error" in token_data:
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({"error": token_data.get("error_description", token_data["error"])}),
        }

    return {
        "statusCode": 200,
        "headers": cors_headers,
        "body": json.dumps({"access_token": token_data.get("access_token", "")}),
    }
