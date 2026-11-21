"""End-to-end run of the LangGraph flow with the offline FakeLLM (no API key, no network).
Skipped automatically if langgraph is not installed."""

import pytest

pytest.importorskip("langgraph")

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from mockmate.config import Settings  # noqa: E402
from mockmate.graph import build_graph  # noqa: E402
from mockmate.llm import FakeLLM  # noqa: E402


def make_graph(ws, checkpointer=None):
    settings = Settings("fake", "fake", "", ws.root, 2, ws.root / ".c.sqlite")
    return build_graph(settings, FakeLLM(), ws).compile(checkpointer=checkpointer or MemorySaver())


def run(graph, cfg, payload):
    says, pending = [], None
    for chunk in graph.stream(payload, cfg, stream_mode="updates"):
        if "__interrupt__" in chunk:
            pending = chunk["__interrupt__"][0].value
            continue
        for upd in chunk.values():
            if isinstance(upd, dict) and upd.get("say"):
                says.append(upd["say"])
    return says, pending


def start(thread):
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 100}
    init = {
        "profile": {"role": "ML engineer", "round": "ML fundamentals", "difficulty": "medium"},
        "thread": thread,
        "total": 2,
        "started": "2026-11-21",
    }
    return cfg, init


def test_full_interview_memory_and_approval(ws):
    graph = make_graph(ws)

    # --- session 1: exactly one question, then it waits -------------------------------
    cfg, init = start("t1")
    says, pending = run(graph, cfg, init)
    assert pending["type"] == "answer" and pending["index"] == 1
    assert sum("Question " in s for s in says) == 1 and not any("Question 2" in s for s in says)

    says, pending = run(graph, cfg, Command(resume="idk"))
    assert any("Score  " in s for s in says)  # scorecard shown
    assert pending["index"] == 2
    assert ws.exists("sessions/2026-11-21_t1.md")

    says, pending = run(graph, cfg, Command(resume="no idea"))
    assert pending is None and ws.exists("weak-topics.md")  # first creation needs no approval
    assert "Average" in says[-1]

    # --- session 2: starts from the saved weak topics, overwrite needs approval --------
    before = ws.read_text("weak-topics.md")
    cfg2, init2 = start("t2")
    says, pending = run(graph, cfg2, init2)
    assert any("Loaded weak topics" in s for s in says)
    run(graph, cfg2, Command(resume="idk"))
    says, pending = run(graph, cfg2, Command(resume="idk"))
    assert pending["type"] == "approval"
    says, pending = run(graph, cfg2, Command(resume={"decision": "reject"}))
    assert pending is None and ws.read_text("weak-topics.md") == before  # rejection changes nothing

    # --- session 3: approve really overwrites -----------------------------------------
    cfg3, init3 = start("t3")
    run(graph, cfg3, init3)
    run(graph, cfg3, Command(resume="idk"))
    _, pending = run(graph, cfg3, Command(resume="idk"))
    assert pending["type"] == "approval"
    run(graph, cfg3, Command(resume={"decision": "approve"}))
    assert ws.read_text("weak-topics.md") != before


def test_new_thread_id_starts_clean_and_same_id_resumes(ws):
    graph = make_graph(ws)
    cfg, init = start("a")
    run(graph, cfg, init)
    run(graph, cfg, Command(resume="idk"))  # now waiting on question 2

    snap = graph.get_state(cfg)
    assert snap.values["q_index"] == 1 and snap.next  # same id: state survives, mid-interview
    assert graph.get_state({"configurable": {"thread_id": "brand-new"}}).values == {}
