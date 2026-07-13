---
name: reuse-check
description: Use right after a design/spec/plan/ADR doc is written — OFFER to check that design against past portfolio work before building. Ask first; only search if the user says yes. Triggers on "I wrote a design doc", "check this design", "vet this against past work", finishing a spec/plan.
---

# Reuse Check — ask after a design, search only on yes

The trigger is **a design doc, then an ask** — not building, not every prompt.
This keeps it cheap: the search runs only when the user opts in.

1. **When a design/spec/plan/ADR doc has just been written**, ASK the user one
   question: *"Want me to check this design against past work
   (reuse / extend / link / inspired)?"* Do NOT run the search yet.
2. **Only if they say yes**, call
   `portfolio_reuse_check(building=<path to that design doc>)` (ghps MCP server —
   pass the PATH, not the pasted text, so it stays token-cheap; it searches the
   whole portfolio regardless of current repo).
3. Present the top matches with provenance ("surfaced X because your design
   mentions Y; reuse_tags [...]"). Decide: **reuse** (as-is) · **extend** (build on
   top) · **link** (companion) · **inspired** (borrow the pattern) · **new** (nothing fit).
4. Record it: `portfolio_record_reuse(built=<slug>, reused=[...], relation=<one>, note=<one line>)`.
   For `new`, pass `reused=[]` and a note on why nothing fit.

If the user says no, do nothing — that's the point. Requires the `ghps` MCP server.
See ADR-0001 in github-portfolio-search.
