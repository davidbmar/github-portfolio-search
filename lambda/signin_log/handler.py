"""Lambda function to log sign-in events to S3.

Appends each sign-in as a JSON line to:
  s3://BUCKET/PREFIX/YYYY-MM.jsonl

Uses a shared logging bucket with prefix-based organization:
  logs/
    signin/2026-03.jsonl      ← this Lambda writes here
    search/2026-03.jsonl      ← future: search analytics
    access/2026-03.jsonl      ← future: access requests

Environment variables:
  S3_BUCKET        — shared logging bucket (e.g., "davidbmar-logs")
  S3_PREFIX        — prefix/directory (default: "logs/signin")
  ALLOWED_ORIGINS  — comma-separated (e.g., "https://davidbmar.com,http://localhost:8000")
"""

import json
import os
from datetime import datetime, timezone


def handler(event, context):
    # CORS
    allowed = os.environ.get("ALLOWED_ORIGINS", "https://davidbmar.com").split(",")
    headers = event.get("headers", {}) or {}
    req_origin = headers.get("origin", headers.get("Origin", ""))
    origin = req_origin if req_origin in allowed else ""

    cors_headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
    }

    if event.get("httpMethod") == "OPTIONS" or event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}

    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Invalid body"})}

    now = datetime.now(timezone.utc)
    record = {
        "timestamp": now.isoformat(),
        "email": body.get("email", ""),
        "name": body.get("name", ""),
        "provider": body.get("provider", ""),
        "githubUsername": body.get("githubUsername", ""),
        "ip": headers.get("x-forwarded-for", headers.get("X-Forwarded-For", "")),
    }

    # Append to monthly JSONL file in S3
    import boto3
    s3 = boto3.client("s3")
    bucket = os.environ.get("S3_BUCKET", "davidbmar-logs")
    prefix = os.environ.get("S3_PREFIX", "logs/signin")
    key = f"{prefix}/{now.strftime('%Y-%m')}.jsonl"

    # Read existing file, append, write back
    existing = ""
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        existing = obj["Body"].read().decode("utf-8")
    except s3.exceptions.NoSuchKey:
        pass
    except Exception:
        pass

    new_content = existing + json.dumps(record) + "\n"
    s3.put_object(Bucket=bucket, Key=key, Body=new_content.encode("utf-8"), ContentType="application/x-ndjson")

    return {
        "statusCode": 200,
        "headers": cors_headers,
        "body": json.dumps({"ok": True}),
    }
