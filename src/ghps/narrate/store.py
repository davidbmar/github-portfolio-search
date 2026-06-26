from __future__ import annotations

import json
import os
from pathlib import Path


class Store:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        (self.root / "pr_records").mkdir(parents=True, exist_ok=True)
        (self.root / "theme_records").mkdir(parents=True, exist_ok=True)
        self._cursor = self.root / "cursor.json"
        self._ledger = self.root / "membership.jsonl"

    def _write_json(self, path: Path, obj) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

    def read_cursor(self, repo: str) -> str | None:
        if not self._cursor.exists():
            return None
        return json.loads(self._cursor.read_text()).get(repo)

    def write_cursor(self, repo: str, merged_at: str) -> None:
        data = json.loads(self._cursor.read_text()) if self._cursor.exists() else {}
        data[repo] = merged_at
        self._write_json(self._cursor, data)

    def _pr_path(self, repo: str, pr_number: int) -> Path:
        safe_repo = repo.replace("/", "__")
        return self.root / "pr_records" / f"{safe_repo}__{pr_number}.json"

    def put_pr(self, rec: dict) -> None:
        self._write_json(self._pr_path(rec["repo"], rec["pr_number"]), rec)

    def get_pr(self, repo: str, pr_number: int) -> dict | None:
        p = self._pr_path(repo, pr_number)
        return json.loads(p.read_text()) if p.exists() else None

    def all_prs(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((self.root / "pr_records").glob("*.json"))]

    def put_theme(self, rec: dict) -> None:
        safe_theme_id = rec['theme_id'].replace("/", "__")
        self._write_json(self.root / "theme_records" / f"{safe_theme_id}.json", rec)

    def get_theme(self, theme_id: str) -> dict | None:
        p = self.root / "theme_records" / f"{theme_id}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def all_themes(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((self.root / "theme_records").glob("*.json"))]

    def append_ledger(self, entry: dict) -> None:
        with self._ledger.open("a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def ledger_decision(self, repo: str, pr_number: int) -> dict | None:
        if not self._ledger.exists():
            return None
        found = None
        for line in self._ledger.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("repo") == repo and e.get("pr_number") == pr_number:
                found = e
        return found
