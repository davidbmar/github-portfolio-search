from __future__ import annotations

import fnmatch

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
