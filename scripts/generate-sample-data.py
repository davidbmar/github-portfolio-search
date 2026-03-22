#!/usr/bin/env python3
"""Generate realistic sample data for the github-portfolio-search web UI.

Produces repos.json and clusters.json in the specified output directory,
allowing the site to work without a live GitHub token.

Usage:
    python3 scripts/generate-sample-data.py [--output web/data]
"""

import argparse
import json
import os
import sys

REPOS = [
    {
        "name": "audio-stream-transcription",
        "description": "Real-time audio streaming and transcription pipeline using AWS services, SQS, and Whisper for scalable voice-to-text processing",
        "language": "Python",
        "topics": ["audio", "transcription", "aws", "whisper", "streaming", "sqs"],
        "stars": 42,
        "html_url": "https://github.com/davidbmar/audio-stream-transcription",
        "url": "https://github.com/davidbmar/audio-stream-transcription",
        "updated_at": "2026-03-15T00:00:00Z",
    },
    {
        "name": "presigned-url-s3",
        "description": "Secure presigned URL generation for S3 uploads and downloads with Lambda-backed API Gateway",
        "language": "Python",
        "topics": ["aws", "s3", "lambda", "api-gateway", "security"],
        "stars": 28,
        "html_url": "https://github.com/davidbmar/presigned-url-s3",
        "url": "https://github.com/davidbmar/presigned-url-s3",
        "updated_at": "2026-02-20T00:00:00Z",
    },
    {
        "name": "grassyknoll",
        "description": "Audio analysis and signal processing toolkit for forensic-style audio investigation",
        "language": "Python",
        "topics": ["audio", "signal-processing", "analysis", "forensics"],
        "stars": 15,
        "html_url": "https://github.com/davidbmar/grassyknoll",
        "url": "https://github.com/davidbmar/grassyknoll",
        "updated_at": "2025-11-10T00:00:00Z",
    },
    {
        "name": "FSM-generic",
        "description": "Generic finite state machine library for modeling workflows, protocols, and event-driven systems",
        "language": "Python",
        "topics": ["state-machine", "fsm", "workflow", "design-patterns"],
        "stars": 19,
        "html_url": "https://github.com/davidbmar/FSM-generic",
        "url": "https://github.com/davidbmar/FSM-generic",
        "updated_at": "2025-09-05T00:00:00Z",
    },
    {
        "name": "tool-telegram-whatsapp",
        "description": "Unified messaging bot framework supporting Telegram and WhatsApp with shared command handlers",
        "language": "Python",
        "topics": ["telegram", "whatsapp", "chatbot", "messaging", "automation"],
        "stars": 22,
        "html_url": "https://github.com/davidbmar/tool-telegram-whatsapp",
        "url": "https://github.com/davidbmar/tool-telegram-whatsapp",
        "updated_at": "2026-01-18T00:00:00Z",
    },
    {
        "name": "bot-customerobsessed",
        "description": "AI-powered customer service chatbot using LLMs for contextual, empathetic responses",
        "language": "Python",
        "topics": ["chatbot", "ai", "customer-service", "llm", "nlp"],
        "stars": 31,
        "html_url": "https://github.com/davidbmar/bot-customerobsessed",
        "url": "https://github.com/davidbmar/bot-customerobsessed",
        "updated_at": "2026-03-01T00:00:00Z",
    },
    {
        "name": "traceable-searchable-adr-memory-index",
        "description": "Project memory framework with ADR tracking, session logs, sprint orchestration, and searchable decision history",
        "language": "Python",
        "topics": ["adr", "project-management", "documentation", "sprint", "memory"],
        "stars": 8,
        "html_url": "https://github.com/davidbmar/traceable-searchable-adr-memory-index",
        "url": "https://github.com/davidbmar/traceable-searchable-adr-memory-index",
        "updated_at": "2026-03-20T00:00:00Z",
    },
    {
        "name": "github-portfolio-search",
        "description": "Semantic search engine for GitHub portfolio repositories using embeddings and vector similarity",
        "language": "Python",
        "topics": ["search", "embeddings", "portfolio", "vector-search", "github"],
        "stars": 12,
        "html_url": "https://github.com/davidbmar/github-portfolio-search",
        "url": "https://github.com/davidbmar/github-portfolio-search",
        "updated_at": "2026-03-22T00:00:00Z",
    },
    {
        "name": "tool-s3-cloudfront-push",
        "description": "CLI tool for deploying static sites to S3 with CloudFront cache invalidation",
        "language": "Bash",
        "topics": ["aws", "s3", "cloudfront", "deployment", "cli", "devops"],
        "stars": 11,
        "html_url": "https://github.com/davidbmar/tool-s3-cloudfront-push",
        "url": "https://github.com/davidbmar/tool-s3-cloudfront-push",
        "updated_at": "2025-12-01T00:00:00Z",
    },
    {
        "name": "everyone-ai",
        "description": "Democratized AI platform making machine learning accessible to non-technical users with guided workflows",
        "language": "JavaScript",
        "topics": ["ai", "machine-learning", "web-app", "accessibility", "education"],
        "stars": 35,
        "html_url": "https://github.com/davidbmar/everyone-ai",
        "url": "https://github.com/davidbmar/everyone-ai",
        "updated_at": "2026-02-10T00:00:00Z",
    },
]

CLUSTERS = [
    {
        "name": "Voice & Audio Processing",
        "repos": ["audio-stream-transcription", "grassyknoll"],
    },
    {
        "name": "Infrastructure & DevOps",
        "repos": ["presigned-url-s3", "tool-s3-cloudfront-push", "FSM-generic"],
    },
    {
        "name": "AI & Search",
        "repos": [
            "github-portfolio-search",
            "bot-customerobsessed",
            "everyone-ai",
            "traceable-searchable-adr-memory-index",
        ],
    },
    {
        "name": "Web Applications",
        "repos": ["tool-telegram-whatsapp", "everyone-ai"],
    },
]


def write_json(path: str, data: object) -> None:
    """Write data as formatted JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample data for the web UI")
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "web", "data"),
        help="Output directory for JSON files (default: web/data)",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    repos_path = os.path.join(output_dir, "repos.json")
    clusters_path = os.path.join(output_dir, "clusters.json")

    write_json(repos_path, REPOS)
    print(f"Wrote {len(REPOS)} repos to {repos_path}")

    write_json(clusters_path, CLUSTERS)
    print(f"Wrote {len(CLUSTERS)} clusters to {clusters_path}")

    # Validate: every cluster repo must exist in repos list
    repo_names = {r["name"] for r in REPOS}
    for cluster in CLUSTERS:
        for repo in cluster["repos"]:
            if repo not in repo_names:
                print(f"WARNING: cluster '{cluster['name']}' references unknown repo '{repo}'", file=sys.stderr)
                sys.exit(1)

    print("Validation passed: all cluster repos exist in repos.json")


if __name__ == "__main__":
    main()
