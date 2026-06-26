from __future__ import annotations

import math

ATTACH_HI = 0.78
ASK_LO = 0.62


def pr_embed_text(rec: dict) -> str:
    parts = [rec.get("title", ""), rec.get("problem", ""), rec.get("approach", "")]
    parts += list(rec.get("components", [])) + list(rec.get("apis_changed", []))
    return " ".join(p for p in parts if p)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def retrieve(vec: list[float], themes: list[dict], *, top: int = 5) -> list[tuple[dict, float]]:
    scored = [(t, cosine(vec, t["embedding"])) for t in themes if t.get("embedding")]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top]


from .schema import make_slug
from .store import Store

CLASSIFY_SYSTEM = (
    "Decide how a pull request relates to existing work THEMES. "
    "Output ONE JSON object: {\"action\": \"attach\"|\"create\"|\"ignore\", "
    "\"theme_id\": <id or null>, \"title\": <new theme title if create>}. "
    "attach only if the PR clearly extends an existing theme; ignore chores/deps."
)


def _unique_slug(base: str, store: Store) -> str:
    existing = {t["slug"] for t in store.all_themes()}
    slug, i = base, 2
    while slug in existing:
        slug, i = f"{base}-{i}", i + 1
    return slug


def _new_theme_id(store: Store) -> str:
    return f"t{len(store.all_themes()) + 1}"


def _attach(store: Store, theme_id: str, rec: dict) -> None:
    t = store.get_theme(theme_id)
    if rec["pr_number"] not in t["pr_numbers"]:
        t["pr_numbers"].append(rec["pr_number"])
    if rec["repo"] not in t["repos"]:
        t["repos"].append(rec["repo"])
    t["last_activity_at"] = rec["merged_at"] if "merged_at" in rec else t.get("last_activity_at")
    store.put_theme(t)


def classify_pr(rec, vec, store, client, *, model, reclassify=False) -> dict:
    prior = store.ledger_decision(rec["repo"], rec["pr_number"])
    if prior and not reclassify:
        return prior

    cands = retrieve(vec, store.all_themes(), top=5)
    top_score = cands[0][1] if cands else 0.0

    if cands and top_score >= ATTACH_HI:
        action, theme_id = "attach", cands[0][0]["theme_id"]
    else:
        allow_attach = ASK_LO <= top_score < ATTACH_HI
        ask = client.complete_json(
            CLASSIFY_SYSTEM,
            f"PR: {rec.get('title','')}\nCandidates: "
            f"{[(t['theme_id'], t.get('title','')) for t, _ in cands] if allow_attach else '(none eligible)'}",
        )
        action = ask.get("action", "ignore")
        if action == "attach" and not allow_attach:
            action = "create"
        if action == "attach":
            theme_id = ask.get("theme_id") or (cands[0][0]["theme_id"] if cands else None)
            if not theme_id:
                action = "create"
        if action == "create":
            theme_id = _new_theme_id(store)
            slug = _unique_slug(make_slug(ask.get("title") or rec.get("title", "theme")), store)
            store.put_theme({
                "theme_id": theme_id, "slug": slug, "title": ask.get("title") or rec.get("title", ""),
                "aliases": [], "status": "candidate", "repos": [], "pr_numbers": [],
                "embedding": vec, "candidate_since": rec.get("merged_at"),
                "last_activity_at": rec.get("merged_at"),
            })
        elif action == "ignore":
            theme_id = None

    if action in ("attach", "create"):
        _attach(store, theme_id, rec)

    decision = {"repo": rec["repo"], "pr_number": rec["pr_number"],
                "theme_id": theme_id, "action": action, "score": top_score,
                "classifier_model": model}
    store.append_ledger(decision)
    return decision
