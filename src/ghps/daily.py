"""Daily headline digest: aggregate each day's commits across the portfolio and
generate a headline + summary per day.

Two stages, decoupled:
  * generate (this module + an LLM engine) -> web/data/daily.json
  * render   (docsgen.render.render_daily_page) -> /daily page

The LLM engine is pluggable and resolved in order: codex (default, reliable) ->
local MLX server -> deterministic (no LLM, always available).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from ghps.docsgen._util import utc_z

logger = logging.getLogger(__name__)

# Fixed instruction shared by the LLM engines. The model sees the day's commit
# lines and must emit ONLY a JSON object — no tools, no invented facts.
_SYSTEM = (
    "You are a tech changelog editor writing for builders who want to REUSE the "
    "work. Given a single day's git commits across a developer's portfolio, "
    "produce: a catchy accurate headline (max 12 words); a 2-sentence summary; and "
    "'takeaways' — 2 to 4 short, concrete bullet points framed as what was built "
    "and how another developer could apply or reuse it. Respond with ONLY a JSON "
    'object {"headline":"...","summary":"...","takeaways":["...","..."]} and '
    "nothing else. Do not invent facts; ground every point in the commits."
)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_by_day(repo_commits: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Bucket commits by UTC calendar day.

    *repo_commits* maps repo name -> list of ``{sha, message, date}``. Returns
    ``{YYYY-MM-DD: [{repo, sha, message}]}``; commits without a date are dropped.
    """
    days: dict[str, list[dict]] = defaultdict(list)
    for repo, commits in repo_commits.items():
        for c in commits:
            date = (c.get("date") or "")[:10]
            if len(date) != 10:
                continue
            days[date].append(
                {"repo": repo, "sha": c.get("sha", ""), "message": c.get("message", "")}
            )
    return dict(days)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

def _user_prompt(date: str, lines: list[str]) -> str:
    body = "\n".join(f"- {ln}" for ln in lines)
    return f"Date: {date}\nCommits:\n{body}"


class DeterministicEngine:
    """No-LLM fallback so /daily always renders."""

    def generate(self, date: str, lines: list[str]) -> dict:
        repos = {ln.split(":", 1)[0].strip() for ln in lines if ln}
        n, r = len(lines), len(repos)
        headline = f"{n} commit{'' if n == 1 else 's'} across {r} repo{'' if r == 1 else 's'}"
        sample = "; ".join(lines[:3])
        return {"headline": headline, "summary": f"Activity on {date}: {sample}.",
                "takeaways": []}


def _parse_json_object(text: str) -> dict:
    """Extract the first ``{...}`` JSON object from an LLM response.

    Strips any ``<think>...</think>`` reasoning block first (Qwen-style models),
    so the JSON answer is found even when the model reasons aloud beforehand.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?|```", "", text)  # strip markdown code fences
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in response")
    blob = text[start : end + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        # Common LLM glitches: trailing commas before } or ]. Repair and retry.
        repaired = re.sub(r",\s*([}\]])", r"\1", blob)
        obj = json.loads(repaired)
    takeaways = obj.get("takeaways") or []
    if not isinstance(takeaways, list):
        takeaways = [str(takeaways)]
    return {"headline": str(obj.get("headline", "")).strip(),
            "summary": str(obj.get("summary", "")).strip(),
            "takeaways": [str(t).strip() for t in takeaways if str(t).strip()]}


class CodexEngine:
    """Generate via the codex CLI (`codex exec`, read-only sandbox)."""

    def __init__(self, model: str | None = None, timeout: int = 120):
        self._model = model
        self._timeout = timeout

    def generate(self, date: str, lines: list[str]) -> dict:
        prompt = f"{_SYSTEM}\n\n{_user_prompt(date, lines)}"
        with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=True) as out:
            cmd = ["codex", "exec", "--skip-git-repo-check",
                   "--sandbox", "read-only", "--output-last-message", out.name]
            if self._model:
                cmd += ["-m", self._model]
            cmd.append(prompt)
            subprocess.run(cmd, check=True, timeout=self._timeout,
                           capture_output=True, text=True)
            return _parse_json_object(Path(out.name).read_text())


class MlxEngine:
    """Generate via a local ``mlx_lm.server`` (OpenAI-compatible)."""

    def __init__(self, base_url: str = "http://localhost:8080",
                 model: str = "mlx-community/gemma-3-12b-it-4bit", timeout: int = 180):
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._model = model
        self._timeout = timeout

    def generate(self, date: str, lines: list[str]) -> dict:
        import urllib.request

        payload = json.dumps({
            "model": self._model,
            "messages": [{"role": "system", "content": _SYSTEM},
                         {"role": "user", "content": _user_prompt(date, lines)}],
            "max_tokens": 300, "temperature": 0.5,
        }).encode()
        req = urllib.request.Request(
            self._url, data=payload, headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=self._timeout).read())
        return _parse_json_object(resp["choices"][0]["message"]["content"])


class MlxLocalEngine:
    """In-process MLX generation (no HTTP server) — free local engine, robust for
    batch backfills. Loads the model once; reuses it for every day.
    """

    DEFAULT_MODEL = "mlx-community/Qwen3.5-4B-MLX-4bit"

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 600):
        from mlx_lm import load  # imported lazily so non-MLX runs don't need it

        self._model_obj, self._tokenizer = load(model)
        self._max_tokens = max_tokens

    def generate(self, date: str, lines: list[str]) -> dict:
        from mlx_lm import generate as _gen

        messages = [{"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _user_prompt(date, lines)}]
        # Disable Qwen "thinking" so the model emits the JSON directly (kwarg is
        # ignored by templates that don't support it).
        try:
            prompt = self._tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False,
                enable_thinking=False)
        except TypeError:
            prompt = self._tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False)
        text = _gen(self._model_obj, self._tokenizer, prompt=prompt,
                    max_tokens=self._max_tokens, verbose=False)
        return _parse_json_object(text)


def resolve_engine(name: str = "auto"):
    """Pick an engine. ``auto`` = codex -> mlx (if reachable) -> deterministic."""
    if name == "codex":
        return CodexEngine()
    if name == "mlx":
        return MlxEngine()
    if name == "mlx-local":
        return MlxLocalEngine()
    if name == "deterministic":
        return DeterministicEngine()
    # auto
    import shutil
    if shutil.which("codex"):
        return CodexEngine()
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8080/v1/models", timeout=3)
        return MlxEngine()
    except Exception:
        return DeterministicEngine()


# ---------------------------------------------------------------------------
# Digest assembly
# ---------------------------------------------------------------------------

def _generate_resilient(engine, date, lines, *, retries=2, fallback=None):
    """Call *engine*, retrying on any error, then falling back deterministically.

    A single malformed LLM response must never abort a long batch — so each day
    is retried, and as a last resort gets a deterministic (no-LLM) digest.
    """
    last_err = None
    for _ in range(retries + 1):
        try:
            return engine.generate(date, lines)
        except Exception as exc:  # noqa: BLE001 — any engine/parse failure is recoverable
            last_err = exc
    logger.warning("engine failed for %s after %d attempts (%s); using fallback",
                   date, retries + 1, last_err)
    return (fallback or DeterministicEngine()).generate(date, lines)


def _commit_sig(commits: list[dict]) -> str:
    """Stable signature of a day's commit set (sorted repo:sha), for caching."""
    key = "\n".join(sorted(f"{c['repo']}:{c['sha']}" for c in commits))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def build_digests(repo_commits: dict[str, list[dict]], engine,
                  *, retries: int = 2, prior: dict | None = None) -> list[dict]:
    """Assemble per-day digest records, newest first, using *engine* for text.

    Each day is generated resiliently: on engine/parse failure it retries, then
    falls back to a deterministic digest, so one bad response can't drop the batch.

    If *prior* (a ``{date: day_record}`` map from an earlier run) is given, any day
    whose commit set is unchanged (same ``commit_sig``) is reused verbatim — the
    engine is not called, so re-runs only pay for days that actually changed.
    """
    prior = prior or {}
    days = aggregate_by_day(repo_commits)
    out: list[dict] = []
    cached = 0
    for date in sorted(days, reverse=True):
        commits = days[date]
        sig = _commit_sig(commits)
        previous = prior.get(date)
        if previous and previous.get("commit_sig") == sig:
            out.append(previous)  # unchanged -> reuse, no engine call
            cached += 1
            continue

        per_repo: dict[str, list[str]] = defaultdict(list)
        for c in commits:
            per_repo[c["repo"]].append(c["message"])
        lines = [f"{c['repo']}: {c['message']}" for c in commits]
        gen = _generate_resilient(engine, date, lines, retries=retries)
        out.append({
            "date": date,
            "headline": gen["headline"],
            "summary": gen["summary"],
            "takeaways": gen.get("takeaways", []),
            "total_commits": len(commits),
            "repos": [{"name": r, "commits": len(m), "messages": m}
                      for r, m in sorted(per_repo.items())],
            "commit_sig": sig,
        })
    if prior:
        logger.info("daily: reused %d cached days, generated %d",
                    cached, len(out) - cached)
    return out


def write_daily(days: list[dict], output_path: str) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": utc_z(), "count": len(days), "days": days}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    return str(out)


def collect(owner: str, gh, since: str | None = None) -> dict[str, list[dict]]:
    """Fetch commits for every repo *owner* has, dropping repos with none."""
    repo_commits: dict[str, list[dict]] = {}
    for repo in gh.fetch_repos(owner):
        name = repo.get("name") if isinstance(repo, dict) else repo
        if not name:
            continue
        commits = gh.fetch_commits(owner, name, since=since)
        if commits:
            repo_commits[name] = commits
    return repo_commits
