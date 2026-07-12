#!/usr/bin/env python3
"""Export the Portfolio Constellation data file.

Adapter: reads the four data files the web UI already exports
(clusters.json, similarity.json, repos.json, projects.json) and emits
web/data/constellation.json in the shape the constellation renderer wants
(adapted from ~/src/missionmap's MISSION_DATA global).

The renderer is a dependency-free 3D canvas star atlas:
  - stars        = public repos that belong to a semantic cluster
  - constellations = clusters.json (grouping / "what it's about")
  - threads      = similarity.json cosine neighbors (bright = top-2, faint = rest)
  - star size    = score-weighted centrality (GitHub stars are ~all zero;
                   raw similarity degree is saturated at 8, so neither works)

Session: S-2026-07-12-1734-portfolio-constellation
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# missionmap's palette — one color per constellation, assigned by cluster order.
PALETTE = [
    "#38bdf8",  # sky
    "#4ade80",  # green
    "#f472b6",  # pink
    "#fbbf24",  # amber
    "#a78bfa",  # violet
    "#fb7185",  # rose
    "#5eead4",  # teal
    "#60a5fa",  # blue
]

# Similarity edges below this cosine score are dropped as noise (p10 ~= 0.32,
# median ~= 0.56 across the corpus). Top-2 neighbors are always kept + marked
# "strong" regardless, so a repo is never fully isolated.
FAINT_FLOOR = 0.38
STRONG_TOP_N = 2


def slugify(name: str) -> str:
    """Cluster name -> stable key, e.g. 'Transcription & ASR' -> 'transcription-asr'."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "cluster"


def load(data_dir: Path, name: str):
    with open(data_dir / name) as fh:
        return json.load(fh)


def build(data_dir: Path, include_private: bool) -> dict:
    clusters = load(data_dir, "clusters.json")
    similarity = load(data_dir, "similarity.json")
    repos = load(data_dir, "repos.json")
    projects_doc = load(data_dir, "projects.json")
    projects = {p["slug"]: p for p in projects_doc.get("projects", [])}
    repo_meta = {r["name"]: r for r in repos}

    # --- decide which repos become stars ---------------------------------
    # A star must belong to a cluster AND (unless overridden) be public.
    cat_of: dict[str, str] = {}
    categories: dict[str, dict] = {}
    private_excluded = 0
    for i, cluster in enumerate(clusters):
        key = slugify(cluster["name"])
        categories[key] = {"label": cluster["name"], "color": PALETTE[i % len(PALETTE)]}
        for repo in cluster["repos"]:
            meta = repo_meta.get(repo, {})
            if meta.get("private") and not include_private:
                private_excluded += 1
                continue
            cat_of[repo] = key
    included = set(cat_of)

    # --- score-weighted centrality ---------------------------------------
    # outbound[r] = how similar r is to its included neighbors (sum of scores)
    # inbound[r]  = how often r shows up in *other* repos' neighbor lists.
    # inbound is the "foundational / hub" signal; both only count included repos.
    outbound = {r: 0.0 for r in included}
    inbound = {r: 0.0 for r in included}
    for r in included:
        for nb in similarity.get(r, []):
            to, score = nb["name"], nb["score"]
            if to not in included:
                continue
            outbound[r] += score
            inbound[to] += score
    central = {r: outbound[r] + inbound[r] for r in included}

    # normalize centrality -> star radius in missionmap's ~[2.2, 8.5] range.
    lo, hi = min(central.values()), max(central.values())
    span = (hi - lo) or 1.0

    def radius(r: str) -> float:
        norm = (central[r] - lo) / span          # 0..1
        return round(2.2 + (norm ** 0.7) * 6.3, 2)  # sqrt-ish spread, biggest hubs ~8.5

    # --- assemble stars ---------------------------------------------------
    stars = []
    for r in sorted(included):
        meta = repo_meta.get(r, {})
        doc = projects.get(r, {})
        # neighbors: keep included ones above the faint floor; always keep top-2.
        ranked = sorted(
            (nb for nb in similarity.get(r, []) if nb["name"] in included),
            key=lambda n: n["score"],
            reverse=True,
        )
        strong_names = {nb["name"] for nb in ranked[:STRONG_TOP_N]}
        neighbors = [
            {"to": nb["name"], "score": round(nb["score"], 3), "strong": nb["name"] in strong_names}
            for nb in ranked
            if nb["score"] >= FAINT_FLOOR or nb["name"] in strong_names
        ]
        stars.append({
            "id": r,
            "name": doc.get("title") or r,
            "cat": cat_of[r],
            "desc": doc.get("one_liner") or meta.get("description") or "",
            "tech": doc.get("tech") or meta.get("language") or "",
            "lang": meta.get("language") or "",
            "url": doc.get("repo_url") or meta.get("url") or "",
            "size": radius(r),
            "central": round(central[r], 2),
            "reuse": {
                "how_to_apply": doc.get("how_to_apply") or "",
                "patterns": doc.get("patterns") or [],
                "reuse_tags": doc.get("reuse_tags") or [],
            },
            "neighbors": neighbors,
        })

    return {
        "generated": projects_doc.get("generated_at", ""),
        "counts": {
            "stars": len(stars),
            "constellations": len(categories),
            "private_excluded": private_excluded,
        },
        "categories": categories,
        "projects": stars,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Export web/data/constellation.json")
    ap.add_argument("--data", default="web/data", help="dir holding the source *.json files")
    ap.add_argument("--output", default="web/data/constellation.json")
    ap.add_argument("--include-private", action="store_true",
                    help="include private repos (default: exclude — this ships to a public site)")
    args = ap.parse_args()

    out = build(Path(args.data), args.include_private)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))

    c = out["counts"]
    print(f"wrote {args.output}")
    print(f"  {c['stars']} stars · {c['constellations']} constellations · "
          f"{c['private_excluded']} private excluded")
    edges = sum(len(s["neighbors"]) for s in out["projects"])
    print(f"  {edges} directed threads "
          f"({sum(1 for s in out['projects'] for n in s['neighbors'] if n['strong'])} strong)")
    top = sorted(out["projects"], key=lambda s: -s["central"])[:5]
    print("  brightest stars: " + ", ".join(f"{s['name']}({s['central']})" for s in top))


if __name__ == "__main__":
    main()
