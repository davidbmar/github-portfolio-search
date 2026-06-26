from __future__ import annotations

import fnmatch

from .schema import files_hash, validate_pr_record, NarrateValidationError

IGNORE_GLOBS = (
    "*-lock.json", "*.lock", "package-lock.json", "yarn.lock", "poetry.lock",
    "web/data/*", "dist/*", "build/*", "*.min.js", "*.min.css",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico",
    "*.snap", "vendor/*", "node_modules/*", "*.generated.*",
)
_LANG = {"py": "python", "js": "javascript", "ts": "typescript", "go": "go",
         "rs": "rust", "md": "markdown", "yml": "yaml", "yaml": "yaml",
         "html": "html", "css": "css", "json": "json", "sh": "shell"}


def _lang(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _LANG.get(ext, ext or "unknown")


def is_signal_file(path: str) -> bool:
    return not any(fnmatch.fnmatch(path, g) for g in IGNORE_GLOBS)


def _is_test(path: str) -> bool:
    return "test" in path.lower()


def _is_public_iface(path: str) -> bool:
    p = path.lower()
    return any(t in p for t in ("__init__.py", "cli.py", "api", "schema", "client", "server"))


def manifest(files: list[dict]) -> list[dict]:
    return [{"path": f["path"], "status": f.get("status", ""),
             "adds": f.get("adds", 0), "dels": f.get("dels", 0),
             "lang": _lang(f["path"])} for f in files]


def select_evidence(files: list[dict], *, max_files: int = 6, max_patch_chars: int = 1500) -> list[dict]:
    signal = [f for f in files if is_signal_file(f["path"])]

    def rank(f):
        return (0 if _is_test(f["path"]) else 1 if _is_public_iface(f["path"]) else 2,
                -(f.get("adds", 0) + f.get("dels", 0)),
                f["path"])

    signal.sort(key=rank)
    out = []
    for f in signal[:max_files]:
        out.append({"path": f["path"], "excerpt": (f.get("patch", "") or "")[:max_patch_chars]})
    return out


PR_FACT_SYSTEM = (
    "You are a senior engineer extracting REUSABLE facts from one merged pull request. "
    "Output ONE JSON object with EXACTLY these keys: problem (string), approach (string), "
    "components (array of short strings), apis_changed (array), tests_changed (array), "
    "reusable_pattern (boolean: does this PR introduce a pattern another dev could reuse?), "
    "risks (array). Ground every field in the diff; do not invent. No markdown, JSON only."
)
_LLM_KEYS = ("problem", "approach", "components", "apis_changed",
             "tests_changed", "reusable_pattern", "risks")


def build_pr_messages(pr: dict, evidence: list[dict]) -> tuple[str, str]:
    ev = "\n\n".join(f"--- {e['path']} ---\n{e['excerpt']}" for e in evidence)
    user = (f"PR #{pr['number']}: {pr.get('title','')}\n"
            f"Labels: {', '.join(pr.get('labels', [])) or '(none)'}\n"
            f"Description:\n{(pr.get('body') or '')[:2000]}\n\n"
            f"Changed-file evidence (truncated):\n{ev or '(none)'}\n")
    return PR_FACT_SYSTEM, user


def build_pr_record(pr: dict, files: list[dict], client, *, model: str) -> dict:
    evidence = select_evidence(files)
    system, user = build_pr_messages(pr, evidence)
    last = None
    for _ in range(2):
        try:
            llm = client.complete_json(system, user)
            part = {k: llm[k] for k in _LLM_KEYS if k in llm}
            rec = {
                "pr_number": pr["number"], "repo": pr.get("repo", pr.get("repo_name", "")),
                "merged_at": pr["merged_at"], "title": pr.get("title", ""),
                "body": (pr.get("body") or "")[:2000], "labels": pr.get("labels", []),
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "files": manifest(files), "files_hash": files_hash(manifest(files)),
                "evidence": evidence, "model": model,
                **part,
            }
            validate_pr_record(rec)
            return rec
        except (KeyError, NarrateValidationError) as e:
            last = e
    raise NarrateValidationError(f"PR #{pr['number']}: {last}")
