"""The interview as a LangGraph state machine.

    begin -> ask -> wait (interrupt) -> grade -> save -> compress -+-> ask ...
                                                                   +-> finalize -> [approve (interrupt)] -> report

* `wait` pauses the graph after exactly one question, so the model cannot ask three at once
  or answer its own question.
* `approve` pauses before weak-topics.md is overwritten (approve / edit / reject).
* A checkpointer + thread_id persists state at every step, so quitting and restarting resumes.

Nodes only return a `say` string; the CLI does all printing. Nodes that call `interrupt()`
contain no side effects before it (a node re-runs from its start when resumed).
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import context as ctx
from . import memory
from .grading import grade_answer, render_card
from .questions import choose_topic, generate_question
from .report import build_report
from .sessions import load_all, render_session, session_path
from .skills import load_skill
from .workspace import WEAK_FILE, Workspace


class State(TypedDict, total=False):
    # input
    profile: dict  # role, round, difficulty
    thread: str
    total: int
    started: str  # YYYY-MM-DD
    # progress
    q_index: int
    weak: list[str]
    next_topic: str
    topic: str
    question: str
    asked: list[str]
    answer: str
    records: list[dict]
    recent: list[dict]
    summary: str
    session_file: str
    # end of interview
    proposed: str
    needs_approval: bool
    final: str
    # text for the CLI to print
    say: str


def build_graph(settings, llm, ws: Workspace) -> StateGraph:
    def begin(state: State):
        profile = state["profile"]
        stats = memory.parse(ws.read_text(WEAK_FILE)) if ws.exists(WEAK_FILE) else []
        weak = memory.weak_for_round(stats, profile["round"])
        lines = [
            f"Starting a {profile['round']} interview for {profile['role']} "
            f"({profile['difficulty']}), {state['total']} questions."
        ]
        if weak:
            lines.append(f"Loaded weak topics from workspace/{WEAK_FILE}: {', '.join(weak[:3])}. Starting there.")
        return {
            "q_index": 0,
            "asked": [],
            "recent": [],
            "records": [],
            "summary": "",
            "weak": weak,
            "next_topic": "",
            "session_file": session_path(state["started"], state["thread"]),
            "say": "\n".join(lines),
        }

    def ask(state: State):
        i, profile = state["q_index"], state["profile"]
        focus = choose_topic(state["weak"], state["next_topic"], i)
        q = generate_question(
            llm,
            profile,
            focus,
            state["asked"],
            ctx.render_context(profile, state["summary"], state["recent"]),
            skill=load_skill(profile["round"]),
        )
        return {
            "topic": q.topic,
            "question": q.question,
            "say": f"Question {i + 1} of {state['total']}  [{q.topic}]\n{q.question}",
        }

    def wait(state: State):
        answer = interrupt(
            {"type": "answer", "index": state["q_index"] + 1, "total": state["total"], "question": state["question"]}
        )
        return {"answer": str(answer)}

    def grade(state: State):
        profile = state["profile"]
        card = grade_answer(
            llm,
            profile,
            state["question"],
            state["answer"],
            context=ctx.render_context(profile, state["summary"], state["recent"]),
            skill=load_skill(profile["round"]),
        )
        record = {
            "index": state["q_index"] + 1,
            "topic": state["topic"],
            "question": state["question"],
            "answer": state["answer"],
            "card": card.model_dump(),
        }
        return {
            "records": state["records"] + [record],
            "recent": state["recent"] + [record],
            "next_topic": card.next_topic,
            "say": render_card(card),
        }

    def save(state: State):
        profile = state["profile"]
        meta = {**profile, "thread": state["thread"], "date": state["started"]}
        ws.write_file(state["session_file"], render_session(meta, state["records"]))
        return {
            "q_index": state["q_index"] + 1,
            "asked": state["asked"] + [state["question"]],
            "say": f"Saved workspace/{state['session_file']}",
        }

    def compress(state: State):
        summary, recent, n = ctx.trim(llm, state["summary"], state["recent"])
        say = f"[context] folded {n} earlier answer(s) into a running summary; keeping the last {len(recent)}." if n else ""
        return {"summary": summary, "recent": recent, "say": say}

    def route_after_compress(state: State):
        return "ask" if state["q_index"] < state["total"] else "finalize"

    def finalize(state: State):
        proposed = memory.render(memory.aggregate(load_all(ws)))
        if not ws.exists(WEAK_FILE):
            ws.write_file(WEAK_FILE, proposed)  # first creation: nothing to overwrite
            return {"proposed": proposed, "needs_approval": False, "say": f"Created workspace/{WEAK_FILE}."}
        changed = ws.read_text(WEAK_FILE).strip() != proposed.strip()
        return {"proposed": proposed, "needs_approval": changed, "say": ""}

    def route_after_finalize(state: State):
        return "approve" if state["needs_approval"] else "report"

    def approve(state: State):
        decision = interrupt(
            {
                "type": "approval",
                "action": "overwrite",
                "path": WEAK_FILE,
                "diff": memory.make_diff(ws.read_text(WEAK_FILE), state["proposed"]),
            }
        )
        kind = decision.get("decision", "reject") if isinstance(decision, dict) else "reject"
        if kind == "approve":
            ws.write_file(WEAK_FILE, state["proposed"], approved=True)
            return {"say": f"Updated workspace/{WEAK_FILE}."}
        if kind == "edit":
            edited = memory.drop_topics(state["proposed"], decision.get("drop", []))
            ws.write_file(WEAK_FILE, edited, approved=True)
            return {"say": f"Updated workspace/{WEAK_FILE} with your edits."}
        return {"say": f"Rejected. workspace/{WEAK_FILE} was left unchanged."}

    def report(state: State):
        return {"final": "done", "say": "\n" + build_report(load_all(ws))}

    g = StateGraph(State)
    for name, fn in [
        ("begin", begin),
        ("ask", ask),
        ("wait", wait),
        ("grade", grade),
        ("save", save),
        ("compress", compress),
        ("finalize", finalize),
        ("approve", approve),
        ("report", report),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "begin")
    g.add_edge("begin", "ask")
    g.add_edge("ask", "wait")
    g.add_edge("wait", "grade")
    g.add_edge("grade", "save")
    g.add_edge("save", "compress")
    g.add_conditional_edges("compress", route_after_compress, {"ask": "ask", "finalize": "finalize"})
    g.add_conditional_edges("finalize", route_after_finalize, {"approve": "approve", "report": "report"})
    g.add_edge("approve", "report")
    g.add_edge("report", END)
    return g
