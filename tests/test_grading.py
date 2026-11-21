import json

import pytest
from pydantic import ValidationError

from mockmate.grading import apply_guards, grade_answer, render_card
from mockmate.llm import FakeLLM
from mockmate.llmjson import LLMOutputError, extract_json
from mockmate.schemas import Scorecard

PROFILE = {"role": "ML engineer", "round": "ML fundamentals", "difficulty": "medium"}
GOOD = {
    "score": 6,
    "strengths": ["named shrinkage", "right intuition"],
    "gaps": ["no link to variance", "no example"],
    "hint": "Think about what the penalty does to the weights.",
    "next_topic": "Bias-variance",
}
LONG_ANSWER = "L2 adds a penalty on squared weights to the loss so weights shrink and variance drops because the model is smoother."


class Scripted:
    """Returns canned replies in order and records how often it was called."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def invoke(self, messages, **_):
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1

        class M:
            content = reply if isinstance(reply, str) else json.dumps(reply)

        return M()


def test_valid_scorecard():
    card = grade_answer(Scripted(GOOD), PROFILE, "Q?", LONG_ANSWER)
    assert card.score == 6 and len(card.strengths) == 2 and len(card.gaps) == 2


def test_invalid_then_valid_is_retried_not_printed():
    llm = Scripted("here is some prose, no json", {**GOOD, "score": 11}, GOOD)
    card = grade_answer(llm, PROFILE, "Q?", LONG_ANSWER)
    assert llm.calls == 3 and card.score == 6


def test_always_invalid_raises():
    llm = Scripted("nope")
    with pytest.raises(LLMOutputError):
        grade_answer(llm, PROFILE, "Q?", LONG_ANSWER)
    assert llm.calls == 3


def test_json_inside_code_fence_and_prose():
    text = "Sure!\n```json\n" + json.dumps(GOOD) + "\n```\nHope that helps."
    assert json.loads(extract_json(text))["score"] == 6


def test_score_formats_coerced():
    assert Scorecard(**{**GOOD, "score": "7/10"}).score == 7
    assert Scorecard(**{**GOOD, "score": 7.0}).score == 7


@pytest.mark.parametrize("bad", [{"score": -1}, {"score": 11}, {"strengths": ["only one"]}, {"gaps": ["a", "b", "c"]}, {"hint": ""}])
def test_schema_rejects_bad_values(bad):
    with pytest.raises(ValidationError):
        Scorecard(**{**GOOD, **bad})


def test_guard_caps_tiny_answers_even_if_model_inflates():
    inflated = Scorecard(**{**GOOD, "score": 9})
    assert apply_guards(inflated, "idk").score == 2
    assert apply_guards(inflated, "it just makes the model simpler I think").score == 5
    assert apply_guards(inflated, LONG_ANSWER).score == 9


def test_fake_llm_gives_low_score_to_bad_answer_and_higher_to_good():
    bad = grade_answer(FakeLLM(), PROFILE, "Q?", "idk")
    good = grade_answer(FakeLLM(), PROFILE, "Q?", LONG_ANSWER)
    assert bad.score <= 2 < good.score


def test_render_card_has_all_parts():
    out = render_card(Scorecard(**GOOD))
    assert "6/10" in out and "Landed" in out and "Missed" in out and "Hint" in out
