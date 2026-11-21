import pytest

from mockmate.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path / "workspace")


def make_record(index, topic, score, answer="some answer here"):
    return {
        "index": index,
        "topic": topic,
        "question": f"Question about {topic}?",
        "answer": answer,
        "card": {
            "score": score,
            "strengths": ["a", "b"],
            "gaps": ["c", "d"],
            "hint": "think about it",
            "next_topic": "Next",
        },
    }
