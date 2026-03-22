# Vision: GitHub Portfolio Search

## Problem Statement

Developers who build prolifically accumulate dozens or hundreds of GitHub repositories, each containing reusable patterns, solved problems, and proven architectures. But there's no way to search across them semantically — you can't ask "how did I handle WebRTC streaming?" or "what auth patterns do I have?" without manually remembering which repo has what. The result: developers rebuild solutions that already exist in their own portfolio, wasting time and losing institutional knowledge.

## Target Audience

The primary user is a prolific solo developer or small-team lead with 50-200+ GitHub repos spanning multiple domains (voice/audio, infrastructure, browser tools, AI/ML, deployment). They know they've solved a problem before but can't remember where. Secondary users are collaborators exploring the portfolio by capability rather than repo name.

## Key Differentiators

- **Semantic search, not keyword grep** — understands "upload pattern with presigned URLs" even if no repo uses that exact phrase
- **Code-level indexing** — searches inside READMEs AND source files, returning specific functions and patterns, not just repo names
- **Capability clustering** — automatically groups repos by what they DO (voice, auth, deployment) rather than what they're named
- **Browser-native option** — can run entirely offline with transformers.js embeddings and WASM vector search, leveraging patterns already proven in the developer's own repos
- **Portfolio-aware** — understands the developer's full technology landscape, enabling recombination suggestions ("you have a presigned URL uploader AND a transcription pipeline — combine them")

## Solution Overview

GitHub Portfolio Search is a semantic search tool that indexes all repositories for a GitHub user, embedding README content and key source files into a vector store. Users type natural language queries and get ranked results showing which repos match, with relevant code snippets highlighted. The tool can run as a static web page (browser-native embeddings via transformers.js + SQLite-vec WASM) or as a lightweight server with faster indexing. It integrates with the Afterburner dashboard for developers already in that ecosystem, and can also serve as a standalone deployed page on S3/CloudFront.

## Success Criteria

1. Natural language query returns relevant repos in <2 seconds
2. Covers all ~90 repos with README + top-level source file content indexed
3. Works offline (browser-native) or with minimal server footprint
4. Capability clustering surfaces related repos even without a search query
5. Re-indexing happens automatically when repos are updated (daily cron or webhook)
6. A new developer can find "how auth is handled" across the portfolio in one search, not 20 minutes of clicking through repos

