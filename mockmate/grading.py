"""Grading: pinned rubric + validated Scorecard + code-level anti-inflation guard."""

from __future__ import annotations

from .llmjson import LLMOutputError, call_json
from .schemas import Scorecard

GradingError = LLMOutputError

RUBRIC = """Scoring rubric (use the whole scale; most real answers land between 3 and 7):
0-2  empty, off-topic, or fundamentally wrong
3-4  vague, partly wrong, or only buzzwords
5-6  correct core idea but missing the key reasoning, mechanism or example
7-8  correct, well reasoned, minor gaps
9-10 complete, precise, covers trade-offs or edge cases (rare)
Do not reward length. Do not give 8 or more unless you can say why nothing important is missing."""

JSON_SPEC = """Reply with ONLY one JSON object, nothing else:
{"score": <integer 0-10>, "strengths": [<exactly two short strings>], "gaps": [<exactly two short strings>], "hint": "<one short hint that nudges without giving the full answer>", "next_topic": "<topic to probe next, based on the gaps>"}
If the answer is weak, strengths may state the little that was relevant (for example "Attempted the question")."""


def grader_system(profile: dict, context: str, skill: str = "") -> str:
    parts = [
        "You are a strict, fair technical interviewer grading ONE candidate answer.",
        f"Candidate target: {profile['role']} | round: {profile['round']} | difficulty: {profile['difficulty']}",
        RUBRIC,
    ]
    if skill:
        parts.append("Round-specific rubric:\n" + skill)
    if context:
        parts.append("Interview context so far:\n" + context)
    parts.append(JSON_SPEC)
    return "\n\n".join(parts)


def apply_guards(card: Scorecard, answer: str) -> Scorecard:
    """Deterministic cap so a near-empty answer can never score high, whatever the model says."""
    words = len(answer.split())
    cap = 2 if words < 4 else 5 if words < 12 else None
    if cap is not None and card.score > cap:
        return card.model_copy(update={"score": cap})
    return card


def grade_answer(llm, profile: dict, question: str, answer: str, context: str = "", skill: str = "") -> Scorecard:
    messages = [
        ("system", grader_system(profile, context, skill)),
        ("human", f"Question: {question}\n\nCandidate answer:\n{answer}"),
    ]
    card = call_json(llm, messages, Scorecard, retries=3)
    return apply_guards(card, answer)


def render_card(card: Scorecard) -> str:
    return (
        f"Score  {card.score}/10\n"
        f"Landed {'; '.join(card.strengths)}\n"
        f"Missed {'; '.join(card.gaps)}\n"
        f"Hint   {card.hint}"
    )
