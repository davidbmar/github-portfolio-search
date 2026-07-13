#!/usr/bin/env bash
# Ask-gate for reuse-aware building. Fires on PostToolUse(Write|Edit): if the file
# just written looks like a design/spec/plan/ADR doc, it asks the agent to OFFER a
# portfolio reuse-check — it does NOT run the search. The expensive retrieval only
# happens if the user says yes. Reads the hook JSON on stdin.
input=$(cat)
read -r tool path < <(printf '%s' "$input" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get('tool_name',''), d.get('tool_input',{}).get('file_path',''))
" 2>/dev/null)

case "$tool" in Write|Edit) ;; *) exit 0 ;; esac

# A file counts as a design doc by path/name.
if printf '%s' "$path" | grep -iqE '(^|/)(design|spec|proposal|rfc)[^/]*\.md$|/(specs?|plans?|designs?|adr)/[^/]*\.md$|(^|/)(DESIGN|SPEC|PLAN|PROPOSAL|RFC)\.md$|(^|/)ADR-[^/]*\.md$'; then
  msg="A design doc was just written ($path). ASK the user: \"Want me to check this design against past work (reuse / extend / link / inspired)?\" Only if they say yes, call portfolio_reuse_check(building='$path'), present the candidates, and record the decision with portfolio_record_reuse. Do NOT run the search unless they opt in."
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":%s}}' \
    "$(printf '%s' "$msg" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
fi
