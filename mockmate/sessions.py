"""Human-readable session files that are also machine-readable.

Each answered question is stored as readable markdown plus one single-line JSON record
between <!--mm--> markers. Reports and weak-topic files are rebuilt from those records,
so everything is reproducible from the saved files alone."""

from __future__ import annotations

import json
import re

from .workspace import Workspace

_REC = re.compile(r"<!--mm-->(.*?)<!--/mm-->", re.S)


def safe_name(thread: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", thread).strip("-") or "default"


def session_path(started: str, thread: str) -> str:
    return f"sessions/{started}_{safe_name(thread)}.md"


def render_session(meta: dict, records: list[dict]) -> str:
    lines = [
        "---",
        f"thread: {meta['thread']}",
        f"role: {meta['role']}",
        f"round: {meta['round']}",
        f"difficulty: {meta['difficulty']}",
        f"date: {meta['date']}",
        "---",
        f"# MockMate session: {meta['role']} / {meta['round']} ({meta['difficulty']})",
        "",
    ]
    for r in records:
        card = r["card"]
        lines += [
            f"## Q{r['index']} · {r['topic']}",
            f"**Question:** {r['question']}",
            "",
            "**Your answer:**",
            *[f"> {ln}" for ln in (r["answer"].splitlines() or [""])],
            "",
            f"**Score:** {card['score']}/10",
            f"- Landed: {'; '.join(card['strengths'])}",
            f"- Missed: {'; '.join(card['gaps'])}",
            f"- Hint: {card['hint']}",
            f"- Next topic: {card['next_topic']}",
            "",
            f"<!--mm-->{json.dumps(r, ensure_ascii=False)}<!--/mm-->",
            "",
        ]
    return "\n".join(lines)


def parse_session(text: str) -> tuple[dict, list[dict]]:
    meta: dict[str, str] = {}
    if text.startswith("---"):
        head = text.split("---", 2)[1]
        for ln in head.strip().splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip()
    records = [json.loads(m) for m in _REC.findall(text)]
    return meta, records


def load_all(ws: Workspace) -> list[tuple[dict, list[dict]]]:
    out = []
    for rel in ws.list_sessions():
        try:
            meta, records = parse_session(ws.read_text(rel))
        except (ValueError, KeyError):
            continue  # skip a damaged file rather than crash the app
        if records:
            out.append((meta, records))
    return out
