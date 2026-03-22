# Discovery: GitHub Portfolio Semantic Search

## Problem Statement

Developer (davidbmar) has ~90 GitHub repos spanning voice/audio, transcription, browser-native AI, auth, deployment tools, bots/agents, and infrastructure. Finding reusable code, patterns, or prior solutions requires remembering which repo has what — which fails at scale. Repos get rebuilt from scratch when a prior solution already exists.

## Users

- **Primary:** The developer themselves — searching own repos for reusable code, patterns, past solutions
- **Secondary:** Collaborators or anyone wanting to explore the portfolio by capability rather than repo name

## Key Use Cases

1. **"How did I handle WebRTC streaming before?"** — natural language search across all repos, returns relevant code snippets and READMEs
2. **"What auth patterns do I have?"** — cluster repos by capability domain, surface reusable modules
3. **"I need a presigned URL upload pattern"** — find the exact file/function across 90 repos
4. **"What repos use transformers.js?"** — dependency/tech stack search
5. **"Show me everything related to voice"** — semantic grouping, not just keyword match
6. **"What did I build in February?"** — temporal search by activity

## Existing Assets (in davidbmar's portfolio)

These repos contain patterns directly reusable for this project:

- `browser-RAG-retrieval-realtime-night-index-SQLLiteWASM-and-sqllite-vec-portal-vector-db-with-filters` — SQLite-vec + WASM vector DB with filters, runs in browser
- `browser-RAG-retrieval-realtime-night-index-transformersjs-webgpu-web-app-vite-typescript` — Browser-native embeddings with transformers.js + WebGPU, offline HNSW indexing
- `search-tool-provider` — Unified async web search across 6+ backends with MCP server
- `voice-optimal-RAG` — Document ingestion pipeline for RAG
- `character-iris-kade-noir-cyberpunk-ai-browser-native-rag-llm-tts-stt` — Full browser-native RAG + LLM stack

## Portfolio Inventory (~90 repos)

### Voice/STT/TTS (~20 repos)
- Whisper variants (whisperX-runpod, whisperlive-runpod, whisperlive-salad, WhisperLive)
- NVIDIA Riva/Parakeet ASR (6 repos)
- Browser STT/TTS (Browser-Text-to-Speech-TTS-Realtime, browser-Speech-to-Text-realtime-ASR, browser-whisper-models-local-showcase)
- Voice agents (grassy-knoll, voice-only-UI-STT-TTS-base, 2026-nano-claw-voice-loop-tts-stt)
- Voice infrastructure (voice-frontend-modules-auth.transport.engine, sip-voice-transport, voice-print)

### Transcription Infrastructure (~10 repos)
- SQS/Lambda pipelines (transcription-sqs-spot-s3, transcription-realtime-whisper-cognito-s3-lambda)
- Spot instance management (spot-setup)
- S3 presigned URL patterns (S3-presignedURL-Lambda-APIGateway-setup, audio-ui-cf-s3-lambda-cognito)

### Browser-Native AI (~8 repos)
- Local LLM (browser-llm-local-ai-chat)
- Browser RAG (2 repos with vector search)
- Browser voice agent (browser-voice-agent-with-TTS-STT-and-OpenSourceLLMs-demo)
- Sound generation (opensource_sound_generator_llms)

### Auth/Identity (~6 repos)
- AWS Cognito (2026-jan-vibecodeportal, easy-cognito-nginx-gateway-auth)
- Auth0 (Auth0toS3Backend, spa_react_javascript_auth0)
- SuperTokens (supertokens_nodejs, supertokens-s3-example)
- Cloudflare Zero Trust (cloudflare-zero-trust-setup)

### Tools/Frameworks (~8 repos)
- Afterburner (traceable-searchable-adr-memory-index)
- FSM-generic, intelligence-briefing-toolkit
- search-tool-provider, cal-provider
- tool-s3-cloudfront-push, tool-telegram-whatsapp, tool-browserAutomationScripts

### Bots/Agents (~5 repos)
- No Prob Bob (bot-customerObsessed-No-Prob-Bob-afterburner)
- Speaker generation v1/v2, Iris Kade
- claude-chat-workspace

### Deployment/Infrastructure (~5 repos)
- deploy-portal, 2026-feb-File-Browser-for-EC2
- 2026-FEB-21-K3-App-Builder-Claude-proto
- browser_mobile_debug_panel
- ssh-helper

## Success Criteria

1. Type a natural language query, get ranked results with repo name + relevant code snippets
2. Results load in <2 seconds
3. Works offline (browser-native embeddings) OR with minimal server
4. Covers all ~90 repos with README + key source file content
5. Auto-refreshes when repos are updated (GitHub webhooks or periodic re-index)
6. Can be deployed as a static site (S3/CloudFront) or run locally

## Open Questions

- Browser-native only (transformers.js) vs. server-side embeddings (faster indexing)?
- How deep to index? README only vs. README + top-level source files vs. all files?
- Should this integrate with the Afterburner dashboard or be standalone?
- MCP server integration so Claude Code can search the portfolio directly?
