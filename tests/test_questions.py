from mockmate.llm import FakeLLM
from mockmate.questions import choose_topic, generate_question, one_question
from mockmate.skills import load_skill

PROFILE = {"role": "ML engineer", "round": "ML fundamentals", "difficulty": "medium"}


def test_one_question_cuts_extra_questions():
    assert one_question("What is overfitting? And how do you fix it? Also what is bias?") == "What is overfitting?"


def test_one_question_strips_label_and_answer_leak():
    text = "Question 1: Why does L2 help?\nAnswer: it shrinks weights."
    assert one_question(text) == "Why does L2 help?"


def test_one_question_without_question_mark_takes_first_paragraph():
    assert one_question("Explain hash maps.\n\nHint: think buckets") == "Explain hash maps."


def test_choose_topic_starts_from_weak_then_follows_scorecard():
    weak = ["Regularisation", "Bias-variance", "Hash maps"]
    assert choose_topic(weak, "Whatever", 0) == "Regularisation"
    assert choose_topic(weak, "Whatever", 1) == "Bias-variance"
    assert choose_topic(weak, "Cross-validation", 2) == "Cross-validation"
    assert choose_topic([], "", 0) == ""


def test_generate_question_uses_focus_topic():
    q = generate_question(FakeLLM(), PROFILE, "Regularisation", [], "")
    assert q.topic == "Regularisation"
    assert "Regularisation" in q.question


def test_behavioural_skill_loads_only_for_behavioural_round():
    assert "STAR" in load_skill("behavioural")
    assert load_skill("Behavioural round") != ""
    assert load_skill("DSA") == ""
    assert load_skill("ML fundamentals") == ""
