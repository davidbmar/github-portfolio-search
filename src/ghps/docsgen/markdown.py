"""A minimal, escape-safe Markdown -> HTML renderer (zero dependencies).

Docs are republished from untrusted repos, so this renderer NEVER passes raw
HTML through: every text run is HTML-escaped first, then a small known-safe tag
subset is emitted. Supports the constructs that actually show up in project
docs (roadmaps, design notes): ATX headings, fenced code, ordered/unordered
lists, blockquotes, horizontal rules, paragraphs, and inline emphasis / code /
links. It is intentionally not CommonMark-complete — just safe and readable.
"""

from __future__ import annotations

import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|_(.+?)_")
_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SAFE_URL = re.compile(r"^(https?:|mailto:|/|#|\.{0,2}/)", re.IGNORECASE)


def _safe_href(url: str) -> str | None:
    """Return an escaped href if the URL scheme is safe, else None."""
    url = url.strip()
    if _SAFE_URL.match(url) or (":" not in url.split("/", 1)[0]):
        return html.escape(url, quote=True)
    return None


def _inline(text: str) -> str:
    """Render inline markdown on an already-trusted *escaped* segment.

    Text is escaped up front; we then splice in safe tags. Code spans are pulled
    out first so their contents are never treated as emphasis.
    """
    placeholders: list[str] = []

    def _stash(rendered: str) -> str:
        placeholders.append(rendered)
        return f"\x00{len(placeholders) - 1}\x00"

    # Code spans first (escape contents, exempt from further inline parsing).
    def _code_sub(m: re.Match) -> str:
        return _stash(f"<code>{html.escape(m.group(1))}</code>")

    text = _CODE.sub(_code_sub, text)

    # Links: [text](url) — escape text, validate + escape href.
    def _link_sub(m: re.Match) -> str:
        label = html.escape(m.group(1))
        href = _safe_href(m.group(2))
        if href is None:
            return html.escape(m.group(0))
        return _stash(f'<a href="{href}" rel="nofollow noopener">{label}</a>')

    text = _LINK.sub(_link_sub, text)

    # Remaining text is escaped, then emphasis applied.
    text = html.escape(text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(
        lambda m: f"<em>{m.group(1) if m.group(1) is not None else m.group(2)}</em>",
        text,
    )

    # Restore stashed safe HTML.
    return re.sub(r"\x00(\d+)\x00", lambda m: placeholders[int(m.group(1))], text)


def render(md: str) -> str:
    """Render Markdown source to a safe HTML fragment."""
    if not md or not md.strip():
        return ""

    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    def _flush_para(buf: list[str]) -> None:
        if buf:
            out.append("<p>" + _inline(" ".join(buf).strip()) + "</p>")
            buf.clear()

    para: list[str] = []
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            _flush_para(para)
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        # Blank line ends a paragraph
        if not stripped:
            _flush_para(para)
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            _flush_para(para)
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(\*\s*){3,}$|^(-\s*){3,}$|^(_\s*){3,}$", stripped):
            _flush_para(para)
            out.append("<hr>")
            i += 1
            continue

        # Blockquote (consume consecutive '>' lines)
        if stripped.startswith(">"):
            _flush_para(para)
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + _inline(" ".join(quote).strip()) + "</blockquote>")
            continue

        # Unordered list
        if re.match(r"^[-*+]\s+", stripped):
            _flush_para(para)
            items: list[str] = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*+]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            _flush_para(para)
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # Default: accumulate into a paragraph
        para.append(stripped)
        i += 1

    _flush_para(para)
    return "\n".join(out)
