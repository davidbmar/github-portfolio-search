#!/usr/bin/env python3
"""Generate realistic sample data for the github-portfolio-search web UI.

Produces repos.json and clusters.json in the specified output directory,
using real repository metadata from davidbmar's GitHub account.
Allows the site to work without a live GitHub token.

Usage:
    python3 scripts/generate-sample-data.py [--output web/data]
"""

import argparse
import json
import os
import sys

# Real repositories from https://github.com/davidbmar, sorted by name.
# Descriptions are accurate to actual GitHub descriptions where available,
# with concise fallbacks where the original was empty.
REPOS = [
    {
        "name": "2026-FEB-21-K3-App-Builder-Claude-proto",
        "description": "k3s App Builder Platform — Describe, Preview, Publish apps using Claude on a single EC2 instance",
        "language": "Python",
        "topics": ["k3s", "claude", "app-builder", "aws"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/2026-FEB-21-K3-App-Builder-Claude-proto",
        "url": "https://github.com/davidbmar/2026-FEB-21-K3-App-Builder-Claude-proto",
        "updated_at": "2026-02-22T06:21:40Z",
    },
    {
        "name": "2026-nano-claw-voice-loop-tts-stt",
        "description": "Claw is a personal AI assistant you run on your own devices — nano edition with TTS/STT loop",
        "language": "TypeScript",
        "topics": ["voice", "tts", "stt", "ai-assistant"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/2026-nano-claw-voice-loop-tts-stt",
        "url": "https://github.com/davidbmar/2026-nano-claw-voice-loop-tts-stt",
        "updated_at": "2026-02-23T01:19:46Z",
    },
    {
        "name": "4kUpScalerWorker",
        "description": "GPU worker for 4K image upscaling using deep learning models",
        "language": "Python",
        "topics": ["gpu", "upscaling", "deep-learning", "image-processing"],
        "stars": 2,
        "html_url": "https://github.com/davidbmar/4kUpScalerWorker",
        "url": "https://github.com/davidbmar/4kUpScalerWorker",
        "updated_at": "2023-02-20T07:29:43Z",
    },
    {
        "name": "art-starry-night-flowfield",
        "description": "WebGPU-accelerated particle flow field inspired by Van Gogh's Starry Night",
        "language": "JavaScript",
        "topics": ["webgpu", "generative-art", "particles", "flow-field"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/art-starry-night-flowfield",
        "url": "https://github.com/davidbmar/art-starry-night-flowfield",
        "updated_at": "2026-02-06T05:50:28Z",
    },
    {
        "name": "audio_client_server",
        "description": "Using a web browser send a sound recording to a server",
        "language": "Python",
        "topics": ["audio", "streaming", "web", "client-server"],
        "stars": 2,
        "html_url": "https://github.com/davidbmar/audio_client_server",
        "url": "https://github.com/davidbmar/audio_client_server",
        "updated_at": "2025-02-28T04:24:03Z",
    },
    {
        "name": "bot-customerObsessed-No-Prob-Bob-afterburner",
        "description": "Conversational AI customer discovery bot with personality framework for Afterburner ecosystem",
        "language": "Python",
        "topics": ["chatbot", "ai", "customer-service", "afterburner"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/bot-customerObsessed-No-Prob-Bob-afterburner",
        "url": "https://github.com/davidbmar/bot-customerObsessed-No-Prob-Bob-afterburner",
        "updated_at": "2026-03-22T00:03:43Z",
    },
    {
        "name": "browser-RAG-retrieval-realtime-night-index-transformersjs-webgpu-web-app-vite-typescript",
        "description": "Browser-native RAG retrieval layer: offline HNSW indexing + in-browser WebGPU embeddings + local cosine similarity search",
        "language": "TypeScript",
        "topics": ["rag", "webgpu", "embeddings", "browser", "vector-search"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/browser-RAG-retrieval-realtime-night-index-transformersjs-webgpu-web-app-vite-typescript",
        "url": "https://github.com/davidbmar/browser-RAG-retrieval-realtime-night-index-transformersjs-webgpu-web-app-vite-typescript",
        "updated_at": "2026-02-12T03:57:51Z",
    },
    {
        "name": "browser-Speech-to-Text-realtime-ASR",
        "description": "Real-time speech recognition live demo with confidence scores and streaming transcription",
        "language": "TypeScript",
        "topics": ["speech-to-text", "asr", "real-time", "browser"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/browser-Speech-to-Text-realtime-ASR",
        "url": "https://github.com/davidbmar/browser-Speech-to-Text-realtime-ASR",
        "updated_at": "2026-02-01T01:59:56Z",
    },
    {
        "name": "Browser-Text-to-Speech-TTS-Realtime",
        "description": "Real-time text to speech demo running entirely in the browser using WebAssembly and ONNX models",
        "language": "TypeScript",
        "topics": ["tts", "webassembly", "onnx", "browser"],
        "stars": 1,
        "html_url": "https://github.com/davidbmar/Browser-Text-to-Speech-TTS-Realtime",
        "url": "https://github.com/davidbmar/Browser-Text-to-Speech-TTS-Realtime",
        "updated_at": "2026-02-08T04:33:32Z",
    },
    {
        "name": "browser-llm-local-ai-chat",
        "description": "Browser-based local AI chat using in-browser LLM inference",
        "language": "JavaScript",
        "topics": ["llm", "browser", "ai-chat", "local-inference"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/browser-llm-local-ai-chat",
        "url": "https://github.com/davidbmar/browser-llm-local-ai-chat",
        "updated_at": "2026-03-05T05:28:36Z",
    },
    {
        "name": "browser-voice-agent-with-TTS-STT-and-OpenSourceLLMs-demo",
        "description": "Browser-native voice agent — local LLM (WebGPU), TTS, STT. No server required.",
        "language": "TypeScript",
        "topics": ["voice-agent", "webgpu", "tts", "stt", "llm"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/browser-voice-agent-with-TTS-STT-and-OpenSourceLLMs-demo",
        "url": "https://github.com/davidbmar/browser-voice-agent-with-TTS-STT-and-OpenSourceLLMs-demo",
        "updated_at": "2026-02-12T03:45:16Z",
    },
    {
        "name": "browser-whisper-models-local-showcase",
        "description": "Local speech-to-text transcription running entirely in the browser using Whisper models",
        "language": "HTML",
        "topics": ["whisper", "speech-to-text", "browser", "wasm"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/browser-whisper-models-local-showcase",
        "url": "https://github.com/davidbmar/browser-whisper-models-local-showcase",
        "updated_at": "2026-02-06T00:56:07Z",
    },
    {
        "name": "cal-provider",
        "description": "Multi-backend calendar provider library (Google Calendar + CalDAV) with optional MCP server",
        "language": "Python",
        "topics": ["calendar", "google-calendar", "caldav", "mcp"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/cal-provider",
        "url": "https://github.com/davidbmar/cal-provider",
        "updated_at": "2026-02-25T04:57:20Z",
    },
    {
        "name": "claude-chat-workspace",
        "description": "Lightweight conversational Claude interface — clean chat UI served from a minimal Node.js container",
        "language": "Shell",
        "topics": ["claude", "chat", "nodejs", "docker"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/claude-chat-workspace",
        "url": "https://github.com/davidbmar/claude-chat-workspace",
        "updated_at": "2026-03-20T05:55:24Z",
    },
    {
        "name": "cloudflare-zero-trust-setup",
        "description": "Cloudflare Zero Trust setup wizard — interactive portal + CLI for secure localhost tunneling with identity-aware access",
        "language": "TypeScript",
        "topics": ["cloudflare", "zero-trust", "security", "tunneling"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/cloudflare-zero-trust-setup",
        "url": "https://github.com/davidbmar/cloudflare-zero-trust-setup",
        "updated_at": "2026-02-25T04:22:13Z",
    },
    {
        "name": "cognito-lambda-s3-webserver-cloudfront",
        "description": "AWS Cognito + Lambda + S3 + CloudFront web authentication stack",
        "language": "HTML",
        "topics": ["aws", "cognito", "lambda", "cloudfront", "authentication"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/cognito-lambda-s3-webserver-cloudfront",
        "url": "https://github.com/davidbmar/cognito-lambda-s3-webserver-cloudfront",
        "updated_at": "2025-08-19T04:42:21Z",
    },
    {
        "name": "eventbridge-orchestrator",
        "description": "S3 EventBridge Orchestrator for event-driven workflows",
        "language": "Shell",
        "topics": ["aws", "eventbridge", "s3", "orchestration"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/eventbridge-orchestrator",
        "url": "https://github.com/davidbmar/eventbridge-orchestrator",
        "updated_at": "2025-08-09T18:24:28Z",
    },
    {
        "name": "github-portfolio-search",
        "description": "Semantic search across your GitHub portfolio — find reusable code, patterns, and ideas across all your repos",
        "language": "Python",
        "topics": ["search", "embeddings", "portfolio", "vector-search", "github"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/github-portfolio-search",
        "url": "https://github.com/davidbmar/github-portfolio-search",
        "updated_at": "2026-03-22T15:32:12Z",
    },
    {
        "name": "grassy-knoll",
        "description": "Voice OS - generic voice-first operating system",
        "language": "Python",
        "topics": ["voice", "os", "voice-first", "ai"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/grassy-knoll",
        "url": "https://github.com/davidbmar/grassy-knoll",
        "updated_at": "2026-03-09T19:57:02Z",
    },
    {
        "name": "iphone-streaming-plus-Finite-State-Machine",
        "description": "Mac-hosted Python server streams TTS audio to iPhone Safari via WebRTC, with hybrid FSM workflow engine",
        "language": "Python",
        "topics": ["webrtc", "fsm", "iphone", "tts", "streaming"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/iphone-streaming-plus-Finite-State-Machine",
        "url": "https://github.com/davidbmar/iphone-streaming-plus-Finite-State-Machine",
        "updated_at": "2026-02-18T06:28:40Z",
    },
    {
        "name": "mcp-highlighter",
        "description": "Chrome plugin which allows a user to highlight text from an LLM in the window",
        "language": "TypeScript",
        "topics": ["mcp", "chrome-extension", "llm", "highlight"],
        "stars": 1,
        "html_url": "https://github.com/davidbmar/mcp-highlighter",
        "url": "https://github.com/davidbmar/mcp-highlighter",
        "updated_at": "2025-06-09T05:12:25Z",
    },
    {
        "name": "nvidia-parakeet",
        "description": "NVIDIA Riva ASR with Parakeet RNNT model integration",
        "language": "Shell",
        "topics": ["nvidia", "riva", "asr", "parakeet", "speech-recognition"],
        "stars": 1,
        "html_url": "https://github.com/davidbmar/nvidia-parakeet",
        "url": "https://github.com/davidbmar/nvidia-parakeet",
        "updated_at": "2025-10-29T01:06:19Z",
    },
    {
        "name": "nvidia-riva-conformer-streaming",
        "description": "Production-ready Conformer-CTC streaming ASR with NVIDIA Riva 2.19",
        "language": "Shell",
        "topics": ["nvidia", "riva", "conformer", "streaming", "asr"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/nvidia-riva-conformer-streaming",
        "url": "https://github.com/davidbmar/nvidia-riva-conformer-streaming",
        "updated_at": "2025-10-13T01:54:14Z",
    },
    {
        "name": "opensource_sound_generator_llms",
        "description": "Browser app for testing and comparing 9 open-source audio generation models (sound effects, music, speech)",
        "language": "Python",
        "topics": ["audio-generation", "open-source", "sound", "llm"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/opensource_sound_generator_llms",
        "url": "https://github.com/davidbmar/opensource_sound_generator_llms",
        "updated_at": "2026-02-20T01:23:53Z",
    },
    {
        "name": "rag-document-chat",
        "description": "Template to get RAG document chat up and running quickly",
        "language": "Python",
        "topics": ["rag", "document-chat", "llm", "vector-search"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/rag-document-chat",
        "url": "https://github.com/davidbmar/rag-document-chat",
        "updated_at": "2025-06-08T23:36:11Z",
    },
    {
        "name": "rag-document-chat-ver2",
        "description": "Improved RAG document chat with Claude Code integration",
        "language": "Python",
        "topics": ["rag", "document-chat", "claude", "vector-search"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/rag-document-chat-ver2",
        "url": "https://github.com/davidbmar/rag-document-chat-ver2",
        "updated_at": "2025-06-20T06:08:14Z",
    },
    {
        "name": "S3-presignedURL-Lambda-APIGateway-setup",
        "description": "Template to setup S3 presigned URL, Lambda and API Gateway",
        "language": "HTML",
        "topics": ["aws", "s3", "lambda", "api-gateway", "presigned-url"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/S3-presignedURL-Lambda-APIGateway-setup",
        "url": "https://github.com/davidbmar/S3-presignedURL-Lambda-APIGateway-setup",
        "updated_at": "2025-05-12T16:46:37Z",
    },
    {
        "name": "search-tool-provider",
        "description": "Unified async web search across 6+ backends with MCP server, CLI, and admin UI",
        "language": "Python",
        "topics": ["search", "mcp", "async", "web-search"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/search-tool-provider",
        "url": "https://github.com/davidbmar/search-tool-provider",
        "updated_at": "2026-02-26T04:40:29Z",
    },
    {
        "name": "sip-voice-transport",
        "description": "PSTN phone call transport for Mac-local voice AI — supports Telnyx and Twilio",
        "language": "Python",
        "topics": ["sip", "voice", "telnyx", "twilio", "pstn"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/sip-voice-transport",
        "url": "https://github.com/davidbmar/sip-voice-transport",
        "updated_at": "2026-02-27T05:35:06Z",
    },
    {
        "name": "smart-transcription-router",
        "description": "Hybrid transcription service with intelligent routing between real-time FastAPI and batch SQS processing",
        "language": "Shell",
        "topics": ["transcription", "routing", "fastapi", "sqs", "aws"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/smart-transcription-router",
        "url": "https://github.com/davidbmar/smart-transcription-router",
        "updated_at": "2025-08-24T04:48:03Z",
    },
    {
        "name": "speaker-generation-version-1",
        "description": "Speaker generation with fast-think/slow-think dual-LLM architecture",
        "language": "TypeScript",
        "topics": ["speaker", "llm", "dual-llm", "generation"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/speaker-generation-version-1",
        "url": "https://github.com/davidbmar/speaker-generation-version-1",
        "updated_at": "2026-02-12T20:59:49Z",
    },
    {
        "name": "tool-browserAutomationScripts",
        "description": "Browser automation scripts and tools",
        "language": "Shell",
        "topics": ["browser", "automation", "scripts", "tools"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/tool-browserAutomationScripts",
        "url": "https://github.com/davidbmar/tool-browserAutomationScripts",
        "updated_at": "2026-03-15T23:39:21Z",
    },
    {
        "name": "tool-s3-cloudfront-push",
        "description": "CLI tool for deploying static sites to S3 with CloudFront cache invalidation",
        "language": "Shell",
        "topics": ["aws", "s3", "cloudfront", "deployment", "cli"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/tool-s3-cloudfront-push",
        "url": "https://github.com/davidbmar/tool-s3-cloudfront-push",
        "updated_at": "2026-03-17T05:02:21Z",
    },
    {
        "name": "tool-telegram-whatsapp",
        "description": "Multi-transport project messaging for Afterburner — Telegram first, WhatsApp later. CLI, REST, MCP.",
        "language": "Shell",
        "topics": ["telegram", "whatsapp", "messaging", "mcp", "afterburner"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/tool-telegram-whatsapp",
        "url": "https://github.com/davidbmar/tool-telegram-whatsapp",
        "updated_at": "2026-03-19T06:34:41Z",
    },
    {
        "name": "transcriber-2-pass-riva-conformer-cf-s3-lambda-cognito-adapter-2025-10-14",
        "description": "Production two-pass speech recognition: NVIDIA Riva Conformer-CTC (WSS streaming) + AWS S3 chunk processing",
        "language": "Shell",
        "topics": ["transcription", "nvidia", "riva", "aws", "two-pass"],
        "stars": 1,
        "html_url": "https://github.com/davidbmar/transcriber-2-pass-riva-conformer-cf-s3-lambda-cognito-adapter-2025-10-14",
        "url": "https://github.com/davidbmar/transcriber-2-pass-riva-conformer-cf-s3-lambda-cognito-adapter-2025-10-14",
        "updated_at": "2025-12-01T03:18:46Z",
    },
    {
        "name": "transcription-realtime-whisper-cognito-s3-lambda",
        "description": "Real-time Whisper transcription with AWS Cognito authentication and S3/Lambda backend",
        "language": "HTML",
        "topics": ["whisper", "transcription", "aws", "cognito", "real-time"],
        "stars": 1,
        "html_url": "https://github.com/davidbmar/transcription-realtime-whisper-cognito-s3-lambda",
        "url": "https://github.com/davidbmar/transcription-realtime-whisper-cognito-s3-lambda",
        "updated_at": "2026-01-08T05:43:40Z",
    },
    {
        "name": "TranscriptionAPI-S3-backend",
        "description": "Upload component for a user-friendly API to upload transcription content",
        "language": "Python",
        "topics": ["transcription", "api", "s3", "upload"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/TranscriptionAPI-S3-backend",
        "url": "https://github.com/davidbmar/TranscriptionAPI-S3-backend",
        "updated_at": "2025-04-19T05:31:45Z",
    },
    {
        "name": "voice-calendar-scheduler-FSM",
        "description": "24/7 voice-driven apartment viewing scheduling assistant — Twilio/WebRTC, FSM-driven conversation, Piper TTS",
        "language": "Python",
        "topics": ["voice", "scheduler", "fsm", "twilio", "webrtc"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/voice-calendar-scheduler-FSM",
        "url": "https://github.com/davidbmar/voice-calendar-scheduler-FSM",
        "updated_at": "2026-02-26T06:08:10Z",
    },
    {
        "name": "voice-frontend-modules-auth.transport.engine",
        "description": "Shared voice AI infrastructure: transport (WebRTC/TURN/tunnel), edge-auth (pluggable providers), engine modules",
        "language": "Python",
        "topics": ["voice", "webrtc", "auth", "infrastructure", "modules"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/voice-frontend-modules-auth.transport.engine",
        "url": "https://github.com/davidbmar/voice-frontend-modules-auth.transport.engine",
        "updated_at": "2026-02-26T05:50:51Z",
    },
    {
        "name": "voice-only-UI-STT-TTS-base",
        "description": "Minimal browser-to-server voice UI: Browser mic to WebRTC to Whisper STT to Claude to Piper TTS",
        "language": "Python",
        "topics": ["voice", "stt", "tts", "webrtc", "whisper"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/voice-only-UI-STT-TTS-base",
        "url": "https://github.com/davidbmar/voice-only-UI-STT-TTS-base",
        "updated_at": "2026-03-05T05:27:51Z",
    },
    {
        "name": "voice-optimal-RAG",
        "description": "Self-contained RAG service: upload documents, get semantic vector search. Runs as a single Docker container.",
        "language": "Shell",
        "topics": ["rag", "voice", "docker", "vector-search"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/voice-optimal-RAG",
        "url": "https://github.com/davidbmar/voice-optimal-RAG",
        "updated_at": "2026-02-19T04:06:02Z",
    },
    {
        "name": "voice-print",
        "description": "Real-time speaker diarization and voice fingerprinting with multiple embedding models",
        "language": "HTML",
        "topics": ["voice", "diarization", "fingerprinting", "embeddings"],
        "stars": 0,
        "html_url": "https://github.com/davidbmar/voice-print",
        "url": "https://github.com/davidbmar/voice-print",
        "updated_at": "2026-02-18T06:47:09Z",
    },
]

CLUSTERS = [
    {
        "name": "Voice & Speech Processing",
        "repos": [
            "grassy-knoll",
            "voice-only-UI-STT-TTS-base",
            "voice-calendar-scheduler-FSM",
            "voice-frontend-modules-auth.transport.engine",
            "sip-voice-transport",
            "voice-print",
            "voice-optimal-RAG",
            "iphone-streaming-plus-Finite-State-Machine",
            "2026-nano-claw-voice-loop-tts-stt",
            "speaker-generation-version-1",
            "opensource_sound_generator_llms",
        ],
    },
    {
        "name": "Transcription & ASR",
        "repos": [
            "smart-transcription-router",
            "transcription-realtime-whisper-cognito-s3-lambda",
            "transcriber-2-pass-riva-conformer-cf-s3-lambda-cognito-adapter-2025-10-14",
            "nvidia-parakeet",
            "nvidia-riva-conformer-streaming",
            "TranscriptionAPI-S3-backend",
        ],
    },
    {
        "name": "Browser-Native AI",
        "repos": [
            "browser-voice-agent-with-TTS-STT-and-OpenSourceLLMs-demo",
            "browser-llm-local-ai-chat",
            "browser-Speech-to-Text-realtime-ASR",
            "Browser-Text-to-Speech-TTS-Realtime",
            "browser-whisper-models-local-showcase",
            "browser-RAG-retrieval-realtime-night-index-transformersjs-webgpu-web-app-vite-typescript",
        ],
    },
    {
        "name": "AI & Search Tools",
        "repos": [
            "github-portfolio-search",
            "search-tool-provider",
            "bot-customerObsessed-No-Prob-Bob-afterburner",
            "rag-document-chat",
            "rag-document-chat-ver2",
            "mcp-highlighter",
        ],
    },
    {
        "name": "AWS Infrastructure & DevOps",
        "repos": [
            "tool-s3-cloudfront-push",
            "S3-presignedURL-Lambda-APIGateway-setup",
            "cognito-lambda-s3-webserver-cloudfront",
            "eventbridge-orchestrator",
            "cloudflare-zero-trust-setup",
            "2026-FEB-21-K3-App-Builder-Claude-proto",
        ],
    },
    {
        "name": "Developer Tools & Utilities",
        "repos": [
            "tool-telegram-whatsapp",
            "tool-browserAutomationScripts",
            "claude-chat-workspace",
            "cal-provider",
            "art-starry-night-flowfield",
            "audio_client_server",
            "4kUpScalerWorker",
        ],
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

    # Sort repos by name for deterministic output
    sorted_repos = sorted(REPOS, key=lambda r: r["name"])

    repos_path = os.path.join(output_dir, "repos.json")
    clusters_path = os.path.join(output_dir, "clusters.json")

    write_json(repos_path, sorted_repos)
    print(f"Wrote {len(sorted_repos)} repos to {repos_path}")

    write_json(clusters_path, CLUSTERS)
    print(f"Wrote {len(CLUSTERS)} clusters to {clusters_path}")

    # Validate: every cluster repo must exist in repos list
    repo_names = {r["name"] for r in sorted_repos}
    for cluster in CLUSTERS:
        for repo in cluster["repos"]:
            if repo not in repo_names:
                print(f"WARNING: cluster '{cluster['name']}' references unknown repo '{repo}'", file=sys.stderr)
                sys.exit(1)

    print("Validation passed: all cluster repos exist in repos.json")


if __name__ == "__main__":
    main()
