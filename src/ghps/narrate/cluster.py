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
