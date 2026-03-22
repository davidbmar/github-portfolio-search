# Use Cases: GitHub Portfolio Search

## Personal Search (Private)

### A. Pattern Recall
**Query:** "How did I handle WebRTC streaming before?"
**Returns:** Relevant repos with code snippets showing the implementation pattern.
**Why it matters:** Avoids rebuilding solutions that already exist in the portfolio.

### B. Capability Clustering
**Query:** "What auth patterns do I have?"
**Returns:** Grouped repos by domain (Cognito, Auth0, SuperTokens, Cloudflare Zero Trust) with summaries of each approach.
**Why it matters:** Surfaces the breadth of solutions for a given problem space.

### C. Exact Code Lookup
**Query:** "I need a presigned URL upload pattern"
**Returns:** Specific files and functions across repos that implement presigned URL uploads.
**Why it matters:** Copy-paste-ready code from your own proven implementations.

### D. Dependency / Tech Stack Search
**Query:** "What repos use transformers.js?"
**Returns:** Repos with that dependency, showing how it's used in each.
**Why it matters:** Understand your own technology landscape and find reference implementations.

### E. Semantic Grouping
**Query:** "Show me everything related to voice"
**Returns:** All voice-adjacent repos (STT, TTS, voice agents, SIP transport, voice print) even if they don't contain the word "voice."
**Why it matters:** Semantic understanding, not keyword grep.

### F. Temporal Search
**Query:** "What did I build in February?"
**Returns:** Repos with significant commit activity in that time period.
**Why it matters:** Context recall for recent work.

### G. Recombination / Complementary Repos
**Query:** "I have a presigned URL uploader AND a transcription pipeline — show me both"
**Returns:** Two or more repos that could be combined, with notes on how they complement each other.
**Why it matters:** Accelerates new projects by connecting existing building blocks.

### H. Architecture / Infrastructure Patterns
**Query:** "How do I set up Cognito auth with S3 access?"
**Returns:** Repos showing the infrastructure wiring pattern, not just a single function.
**Why it matters:** Infrastructure patterns span multiple files and services — need cross-file search.

### I. Maturity Ranking
**Query:** "Which of my voice repos is the most complete?"
**Returns:** Voice repos ranked by maturity signals (commit count, tests present, documentation quality, last activity).
**Why it matters:** When multiple repos solve the same problem, find the one worth building on.

### I2. Freshness Check
**Query:** Browse repos and check freshness badges.
**Returns:** Each repo shows a freshness label (today, this week, this month, stale) based on when it was last indexed.
**Why it matters:** Know at a glance whether the data for a repo is current. Automated weekly reindexing via GitHub Actions keeps data fresh without manual intervention.

### J. Negative / Exclusion Search
**Query:** "Voice repos that DON'T use AWS"
**Returns:** Filtered results excluding repos with AWS dependencies.
**Why it matters:** Constraint-based search for specific deployment targets.

## Public Portfolio (Read-Only)

### K. Portfolio Browse (No Query)
**User:** Anyone visiting the public site.
**Experience:** Landing page shows capability clusters (Voice, Auth, Browser AI, Tools, etc.) with repo counts and descriptions. No search needed — just explore.
**Why it matters:** Proves breadth and depth of work better than a bullet-point resume.

### L. Recruiter / Hiring Manager View
**Query:** "real-time voice processing"
**Returns:** Curated list of repos with descriptions, tech stacks, and activity levels. No raw code — capability proof only.
**Why it matters:** Searchable portfolio that demonstrates skills with evidence.

### M. Capability Resume
**Use:** Link from resume/LinkedIn to a searchable portfolio that proves each listed skill with actual repos.
**Why it matters:** "I know AWS Lambda" backed by 10 repos using it, searchable and browsable.

## Gated Access (Authenticated)

### N. Collaborator Deep Dive
**User:** Approved collaborator (Google OAuth + approval workflow).
**Experience:** Full semantic search with code snippets, file trees, README content. Same as personal search but read-only.
**Why it matters:** Share your code library with trusted people without making repos public.

### O. Approval Workflow
**Flow:**
1. Visitor sees public portfolio, clicks "Request Access"
2. Signs in with Google OAuth
3. Writes a note: "Hey David, exploring your voice repos for a project"
4. Status: PENDING
5. David gets notified (Telegram via tool-telegram-whatsapp)
6. David approves or denies
7. Approved user gets full search access

**Why it matters:** Controlled sharing — you decide who sees the full portfolio.

## Agent Integration

### P. AI Agent Code Reuse (Bob / Claude Code)
**Scenario:** Mid-conversation, Bob needs a pattern you've built before.
**Flow:** Bob calls `portfolio_search` MCP tool -> finds relevant repos -> suggests adapting existing code.
**Example:**
> "Bob, I need to add presigned URL uploads to this project"
> Bob finds `S3-presignedURL-Lambda-APIGateway-setup`, shows the pattern, offers to adapt it.

**Why it matters:** AI agents become more useful when they can search your entire history of solved problems. This is the highest-leverage use case — it turns 90 repos into an always-available reference library for every future project.

### Q. Private Repo Search via MCP
**Scenario:** All repos made private on GitHub, but still fully searchable via MCP (local) or authenticated REST.
**Why it matters:** Security + searchability. Repos don't need to be public to be useful to you and your agents.

## Test Cases

Each use case above implies a test. Key acceptance tests:

| Test | Input | Expected Output |
|---|---|---|
| Semantic match | "upload files securely" | Returns presigned URL repos (no exact keyword match) |
| Capability cluster | "auth" | Groups: Cognito, Auth0, SuperTokens, Cloudflare |
| Dependency search | "transformers.js" | Returns browser-RAG repos |
| Temporal | "March 2026" | Returns repos with recent commits |
| Exclusion | "voice NOT aws" | Filters out AWS-dependent voice repos |
| Recombination | "upload + transcribe" | Returns both presigned URL AND transcription repos |
| Maturity ranking | "most complete voice repo" | Ranks by commits, tests, docs |
| Public vs gated | Unauthenticated user searches | No code snippets in results |
| MCP tool call | `portfolio_search("presigned URL")` | Returns structured JSON with repo + file + snippet |
| Approval flow | Request access -> pending -> approve | User gains full search access |
| Offline/browser | Search with no server running | Results still work (browser-native embeddings) |
