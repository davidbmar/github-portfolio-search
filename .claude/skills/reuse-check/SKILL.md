---
name: reuse-check
description: Use BEFORE building any new component, feature, service, or script — scans the portfolio for existing repos to reuse/extend/link/take inspiration from, then records the decision. Triggers on "let's build", "create a new", "add a feature", "implement".
---

# Reuse Check — scan before you build

Before writing a new component, you MUST scan what already exists.

1. Call `portfolio_reuse_check(building=<description or path to the design doc/plan>)`.
2. If `verdict == "candidates"`, present the top matches to the user with their
   provenance ("surfaced X because your design doc mentions Y; it has reuse_tags [...]").
   Ask/decide: **reuse** (use as-is) · **extend** (build on top) · **link**
   (companion/see-also) · **inspired** (borrow the pattern) · **new** (nothing fit).
3. After the decision, call
   `portfolio_record_reuse(built=<slug>, reused=[...], relation=<one of above>, note=<one line>)`.
   For `new`, pass `reused=[]` and a note saying why nothing fit — that negative
   evidence is as valuable as a positive edge.

Skip only for trivial edits with no new component. When in doubt, run the check.
