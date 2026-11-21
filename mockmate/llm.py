
"""Model factory. Provider and model come from Settings (.env).
Packages are imported lazily so tests and the offline fake provider
need no provider SDK.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import Settings


def get_llm(settings: Settings):
    """Create the configured language model."""

    if settings.provider == "fake":
        return FakeLLM()

    if settings.provider == "nvidia":
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        llm = ChatNVIDIA(
            model=settings.model,
            api_key=settings.api_key,
            temperature=0.3,
            max_completion_tokens=2048,
        )

        # Disable Nemotron reasoning so the model produces
        # the requested answer instead of exhausting its token budget.
        return llm.with_thinking_mode(enabled=False)

    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model=settings.model,
        model_provider=settings.provider,
        api_key=settings.api_key,
        temperature=0.3,
    )


# --------------------------------------------------
# OFFLINE SCRIPTED MODEL
# Tests and demonstrations only.
# --------------------------------------------------

@dataclass
class _Msg:
    content: str


_BANK = [
    (
        "Regularisation",
        "Why does L2 regularisation help when a model overfits?",
    ),
    (
        "Bias-variance",
        "Explain the bias-variance trade-off with an example?",
    ),
    (
        "Cross-validation",
        "Why do we use k-fold cross-validation instead of a single train/test split?",
    ),
    (
        "Hash maps",
        "How does a hash map handle collisions, and what does that cost?",
    ),
    (
        "Binary search",
        "What are the preconditions and complexity of binary search?",
    ),
    (
        "Gradient descent",
        "What happens to gradient descent if the learning rate is too large?",
    ),
]

_BEHAVIOURAL = [
    (
        "Teamwork",
        "Tell me about a time you disagreed with a teammate and how you resolved it?",
    ),
    (
        "Failure",
        "Describe a project that did not go to plan and what you changed afterwards?",
    ),
    (
        "Leadership",
        "Tell me about a time you took the lead without being asked?",
    ),
]

_KEYWORDS = (
    "because",
    "variance",
    "trade-off",
    "tradeoff",
    "example",
    "complexity",
    "penal",
    "loss",
    "shrink",
)


class FakeLLM:
    """Deterministic stand-in for offline tests and demonstrations."""

    def __init__(self):
        self.asked = 0

    @staticmethod
    def _parts(messages):
        out = []

        for message in messages:
            if isinstance(message, tuple):
                role, content = message
            else:
                role = getattr(message, "type", "human")
                content = message.content

            out.append((role, content))

        return out

    def invoke(self, messages, **_):
        parts = self._parts(messages)

        system = next(
            (content for role, content in parts if role == "system"),
            "",
        )

        human = next(
            (content for role, content in parts if role in ("human", "user")),
            "",
        )

        if "grading ONE candidate answer" in system:
            return _Msg(json.dumps(self._grade(human)))

        if "Ask exactly ONE interview question" in system:
            return _Msg(json.dumps(self._question(system)))

        return _Msg("Fake summary of earlier answers.")

    def _question(self, system: str):
        match = re.search(r"Focus topic: (.+)", system)
        focus = match.group(1).strip() if match else ""

        self.asked += 1

        if focus and not focus.startswith("("):
            return {
                "topic": focus,
                "question": (
                    f"Explain {focus} and when it matters in practice."
                ),
            }

        bank = (
            _BEHAVIOURAL
            if "round: behavioural" in system.lower()
            else _BANK
        )

        topic, question = bank[
            (self.asked - 1) % len(bank)
        ]

        return {
            "topic": topic,
            "question": question,
        }

    @staticmethod
    def _grade(human: str):
        answer = human.split(
            "Candidate answer:\n",
            1,
        )[-1]

        words = len(answer.split())

        hits = sum(
            keyword in answer.lower()
            for keyword in _KEYWORDS
        )

        score = 1 if words < 6 else min(4 + hits, 8)

        return {
            "score": score,
            "strengths": [
                "Attempted the question",
                "Stayed on topic",
            ],
            "gaps": [
                "Did not explain the mechanism",
                "No concrete example",
            ],
            "hint": (
                "Connect the idea to what it changes "
                "in the loss or the error."
            ),
            "next_topic": "Bias-variance",
        }
