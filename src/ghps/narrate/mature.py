from __future__ import annotations

from .store import Store


def score_theme(theme: dict, prs: list[dict]) -> tuple[int, str]:
    member_keys = set(theme.get("pr_numbers", []))
    members = [p for p in prs if f"{p['repo']}#{p['pr_number']}" in member_keys]
    reasons, score = [], 0
    pr_pts = min(len(members) * 2, 6)
    score += pr_pts; reasons.append(f"{len(members)} PRs (+{pr_pts})")
    if any(p.get("tests_changed") for p in members):
        score += 2; reasons.append("tests (+2)")
    if any(p.get("apis_changed") for p in members):
        score += 2; reasons.append("public API (+2)")
    if any(any(f.get("path", "").lower().endswith((".md", "readme"))
               for f in p.get("files", [])) for p in members):
        score += 1; reasons.append("docs (+1)")
    if any(p.get("reusable_pattern") for p in members):
        score += 2; reasons.append("reusable pattern (+2)")
    if members and all(
        any(l in ("chore", "deps", "dependencies") for l in p.get("labels", [])) for p in members
    ):
        score -= 3; reasons.append("chore/deps only (-3)")
    return score, ", ".join(reasons)


def apply_lifecycle(store: Store, *, mature_at: int = 7) -> list[dict]:
    prs = store.all_prs()
    matured = []
    for theme in store.all_themes():
        score, reason = score_theme(theme, prs)
        theme["maturity_score"] = score
        theme["maturity_reason"] = reason
        if theme["status"] == "candidate" and score >= mature_at:
            theme["status"] = "mature"
        store.put_theme(theme)
        if theme["status"] in ("mature", "published"):
            matured.append(theme)
    return matured
