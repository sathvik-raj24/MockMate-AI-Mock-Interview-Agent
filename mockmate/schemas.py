"""Validated structures. The model never gets to print a free-form score."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


class Scorecard(BaseModel):
    """One graded answer: score out of ten, two strengths, two gaps, one hint, next topic."""

    score: int = Field(ge=0, le=10)
    strengths: list[str] = Field(min_length=2, max_length=2)
    gaps: list[str] = Field(min_length=2, max_length=2)
    hint: str = Field(min_length=3)
    next_topic: str = Field(min_length=2)

    @field_validator("score", mode="before")
    @classmethod
    def _coerce_score(cls, v):
        # Models sometimes write "7/10" or 7.0. Accept those, reject nonsense.
        if isinstance(v, str):
            m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:/\s*10)?\s*", v)
            if m:
                v = float(m.group(1))
        if isinstance(v, float):
            v = round(v)
        return v

    @field_validator("strengths", "gaps")
    @classmethod
    def _items_not_blank(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v]
        if any(not s for s in cleaned):
            raise ValueError("list items must not be blank")
        return cleaned

    @field_validator("hint", "next_topic")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class QuestionOut(BaseModel):
    """One interview question plus the topic it probes (used for weak-topic tracking)."""

    topic: str = Field(min_length=2)
    question: str = Field(min_length=10)

    @field_validator("topic", "question")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()
