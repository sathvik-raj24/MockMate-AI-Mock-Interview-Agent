"""Question generation. Exactly one question; no answer or hint in the question text."""

from __future__ import annotations

import re

from .llmjson import call_json
from .schemas import QuestionOut

SYSTEM = """You are a technical interviewer. Ask exactly ONE interview question.
Do not include the answer, a hint, a sample solution or any follow-up question.
Candidate target: {role} | round: {round} | difficulty: {difficulty}
Match the difficulty: easy = definitions and intuition, medium = reasoning and trade-offs, hard = edge cases and design.
{skill}
Already asked (never repeat or rephrase these):
{asked}

Focus topic: {focus}

Interview context so far:
{context}

Reply with ONLY one JSON object: {{"topic": "<2-5 word topic name>", "question": "<the single question>"}}"""


def one_question(text: str) -> str:
    """Enforce 'one question' in code: strip labels, cut anything after the first '?'."""
    t = re.sub(r"^\s*question\s*\d*\s*[:.\-]\s*", "", text.strip(), flags=re.I)
    t = re.split(r"\n\s*(?:answer|hint|solution|expected)\s*[:\-]", t, flags=re.I)[0]
    i = t.find("?")
    t = t[: i + 1] if i != -1 else t.strip().split("\n\n")[0]
    return " ".join(t.split())


def choose_topic(weak: list[str], next_topic: str, index: int) -> str:
    """Adaptive focus: start from saved weak topics, then follow the last scorecard's next_topic."""
    if index < min(2, len(weak)):
        return weak[index]
    return next_topic.strip()


def generate_question(
    llm, profile: dict, focus: str, asked: list[str], context: str, skill: str = ""
) -> QuestionOut:
    system = SYSTEM.format(
        role=profile["role"],
        round=profile["round"],
        difficulty=profile["difficulty"],
        skill=("Round-specific guidance:\n" + skill) if skill else "",
        asked="\n".join(f"- {q}" for q in asked) or "(none yet)",
        focus=focus or "(none: pick a fitting topic from this round that has not been covered)",
        context=context or "(start of interview)",
    )
    out = call_json(llm, [("system", system), ("human", "Ask the next question.")], QuestionOut)
    return QuestionOut(topic=out.topic, question=one_question(out.question))
