import pytest
from conftest import make_record

from mockmate.config import ConfigError, load_settings
from mockmate.context import KEEP_RECENT, render_context, trim
from mockmate.llm import FakeLLM

PROFILE = {"role": "ML engineer", "round": "ML fundamentals", "difficulty": "hard"}


def records(n):
    return [make_record(i + 1, f"Topic{i}", 5) for i in range(n)]


def test_short_history_is_untouched():
    summary, recent, n = trim(FakeLLM(), "", records(KEEP_RECENT))
    assert (summary, n) == ("", 0) and len(recent) == KEEP_RECENT


def test_long_history_is_summarised_and_trimmed():
    summary, recent, n = trim(FakeLLM(), "", records(7))
    assert n == 4 and len(recent) == KEEP_RECENT and summary
    assert [r["index"] for r in recent] == [5, 6, 7]


def test_role_and_round_still_present_late_in_session():
    summary, recent, _ = trim(FakeLLM(), "", records(20))
    ctx = render_context(PROFILE, summary, recent)
    assert "ML engineer" in ctx and "ML fundamentals" in ctx and "hard" in ctx


def test_failed_summary_falls_back_instead_of_crashing():
    class Broken:
        def invoke(self, *_a, **_k):
            raise RuntimeError("network down")

    summary, recent, n = trim(Broken(), "", records(6))
    assert n == 3 and "Topic0" in summary


def test_settings_defaults_to_nvidia_model():
    s = load_settings({"NVIDIA_API_KEY": "nvapi-real"})
    assert s.provider == "nvidia" and s.model == "meta/llama-3.3-70b-instruct" and s.api_key == "nvapi-real"


def test_settings_missing_key_is_a_clear_error():
    with pytest.raises(ConfigError, match="NVIDIA_API_KEY"):
        load_settings({"MODEL_PROVIDER": "nvidia"})


def test_settings_placeholder_key_rejected():
    with pytest.raises(ConfigError):
        load_settings({"NVIDIA_API_KEY": "nvapi-your-key-here"})


def test_settings_other_provider_needs_model_name():
    with pytest.raises(ConfigError, match="MODEL_NAME"):
        load_settings({"MODEL_PROVIDER": "openai", "OPENAI_API_KEY": "sk-x"})


def test_settings_fake_needs_no_key_and_questions_are_clamped():
    s = load_settings({"MODEL_PROVIDER": "fake", "QUESTIONS_PER_SESSION": "999"})
    assert s.provider == "fake" and s.questions == 20


def test_settings_bad_question_count():
    with pytest.raises(ConfigError):
        load_settings({"MODEL_PROVIDER": "fake", "QUESTIONS_PER_SESSION": "many"})
