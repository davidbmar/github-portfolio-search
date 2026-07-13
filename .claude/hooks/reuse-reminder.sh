#!/usr/bin/env bash
# Injects a reuse-check reminder when the user's prompt looks like build-intent.
# Reads the hook JSON on stdin; emits additionalContext (non-blocking) on a match.
input=$(cat)
prompt=$(printf '%s' "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
# Build-intent = a build verb reasonably near a "thing we build" noun. A little
# slack (.{0,30}) lets modifiers sit between them ("build a new *transcription*
# service"). This is a non-blocking nudge, so a rare false positive is fine.
if printf '%s' "$prompt" | grep -qiE "\b(build|create|implement|add|write)\b.{0,30}\b(feature|component|service|tool|script|endpoint|module|app|api|pipeline|integration|page|dashboard)\b"; then
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Reuse check: before building this, run portfolio_reuse_check(building=...) and record the decision with portfolio_record_reuse (see the reuse-check skill / ADR-0001)."}}'
fi
