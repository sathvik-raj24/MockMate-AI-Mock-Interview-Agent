
"""Call a chat model and return a validated Pydantic object.

Requests JSON mode when supported, extracts JSON, validates it,
and retries invalid responses with corrective feedback.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class LLMOutputError(Exception):
    """The model could not produce valid structured output after retries."""


def message_text(msg) -> str:
    """Convert a LangChain message into plain text."""

    content = getattr(msg, "content", msg)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text", ""))
            else:
                parts.append(str(part))

        return "".join(parts)

    return str(content)


def extract_json(text: str) -> str:
    """Extract the first complete JSON object from model output."""

    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            _, end = decoder.raw_decode(text[index:])
            return text[index:index + end]
        except json.JSONDecodeError:
            continue

    raise ValueError("No valid JSON object found in model reply")


def call_json(
    llm,
    messages: list,
    model_cls: type[T],
    retries: int = 3,
) -> T:
    """Request JSON output and validate it against a Pydantic schema."""

    msgs = list(messages)
    last_error: Exception | None = None

    # NVIDIA NIM supports JSON response mode for compatible models.
    # Keep a fallback for models/providers that reject this parameter.
    try:
        json_llm = llm.bind(
            response_format={"type": "json_object"}
        )
    except Exception:
        json_llm = llm

    for attempt in range(retries):
        try:
            raw = message_text(json_llm.invoke(msgs))

            parsed = extract_json(raw)

            return model_cls.model_validate_json(parsed)

        except (ValueError, ValidationError) as exc:
            last_error = exc

            short_error = str(exc).replace("\n", " ")[:300]

            msgs = msgs + [
                ("assistant", raw[:2000] if "raw" in locals() else ""),
                (
                    "human",
                    "Your previous response was invalid: "
                    f"{short_error}. "
                    "Return exactly one valid JSON object matching "
                    "the requested fields. Do not include Markdown "
                    "or explanatory text.",
                ),
            ]

        except Exception as exc:
            last_error = exc
            break

    raise LLMOutputError(
        f"Model could not return valid {model_cls.__name__} "
        f"JSON after {retries} attempts: {last_error}"
    )
