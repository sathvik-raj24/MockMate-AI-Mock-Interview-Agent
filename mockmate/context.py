"""Context discipline: keep only the last few answers verbatim and fold older ones into a
short running summary. Role, round and difficulty live in state and are re-injected into
every prompt, so they are still known on question 20."""

from __future__ import annotations

from .llmjson import message_text

KEEP_RECENT = 3
MAX_SUMMARY_CHARS = 1200

SUMMARISE_SYSTEM = (
    "Compress the interview history below into at most 120 words. Keep: which topics were asked, "
    "the scores, and recurring gaps. Output plain text only."
)


def render_context(profile: dict, summary: str, recent: list[dict]) -> str:
    lines = [f"Role: {profile['role']} | Round: {profile['round']} | Difficulty: {profile['difficulty']}"]
    if summary:
        lines.append(f"Summary of earlier answers: {summary}")
    for r in recent:
        lines.append(f"Q{r['index']} [{r['topic']}] scored {r['card']['score']}/10. Gaps: {'; '.join(r['card']['gaps'])}")
    return "\n".join(lines)


def _fallback_summary(summary: str, older: list[dict]) -> str:
    bits = [f"Q{r['index']} {r['topic']}={r['card']['score']}/10" for r in older]
    return (summary + " | " if summary else "") + ", ".join(bits)


def summarise(llm, summary: str, older: list[dict]) -> str:
    body = "\n".join(
        f"Q{r['index']} [{r['topic']}] score {r['card']['score']}/10; gaps: {'; '.join(r['card']['gaps'])}"
        for r in older
    )
    prompt = f"Existing summary: {summary or '(none)'}\n\nNew items:\n{body}"
    try:
        text = message_text(llm.invoke([("system", SUMMARISE_SYSTEM), ("human", prompt)])).strip()
        if not text:
            raise ValueError("empty summary")
    except Exception:  # a failed summary must never break the interview
        text = _fallback_summary(summary, older)
    return text[:MAX_SUMMARY_CHARS]


def trim(llm, summary: str, recent: list[dict], keep: int = KEEP_RECENT) -> tuple[str, list[dict], int]:
    """Returns (new_summary, new_recent, number_of_answers_folded_into_the_summary)."""
    if len(recent) <= keep:
        return summary, recent, 0
    older, kept = recent[:-keep], recent[-keep:]
    return summarise(llm, summary, older), kept, len(older)
