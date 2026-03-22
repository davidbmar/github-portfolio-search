agentA-search-fix — Sprint 9

Sprint-Level Context

Goal
- CRITICAL: Fix F-005 — web search fails on multi-word queries ("voice processing" returns 0 results)
- Fix B-012 — .venv symlinks break after agent merges
- Add "Request Access" page skeleton for future gated tier
- Improve search result quality for recruiters

Constraints
- No two agents may modify the same files
- agentA owns web search fix (web/js/search.js, web/js/app.js)
- agentB owns access page and meta improvements (web/index.html, web/css/style.css)
- agentC owns infrastructure fixes (scripts/, .sprint/, Makefile, tests/)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Fix multi-word search so "voice processing" returns voice repos

Tasks
- In web/js/search.js, update the search/filter logic:
  - Split the query into individual terms on whitespace
  - A repo matches if ANY term appears in its name, description, or topics (OR logic)
  - Score repos higher when MORE terms match (rank by match count)
  - Keep existing exact-phrase match as highest priority (if full phrase matches, rank first)
  - Case-insensitive matching
- In web/js/app.js, update the search result count to show "N results for term1, term2" when multi-word
- Add fuzzy tolerance: if a term is >5 chars, also match if the term is a substring of a word (e.g., "process" matches "processing")
- Test cases to verify manually:
  - "voice processing" → returns voice repos (voice matches)
  - "s3 upload" → returns S3-presignedURL repo (s3 matches)
  - "presigned" → returns presigned-url repo (substring match)
  - "aws lambda" → returns repos with aws OR lambda topics
  - Single word "voice" → still works as before (9 results)

Acceptance Criteria
- Search "voice processing" returns voice-related repos (not 0 results)
- Search "s3 upload" returns S3/infrastructure repos
- Search "presigned" returns presigned-url repo
- Single-word searches still work correctly
- No JS errors in console
