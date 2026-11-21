"""Terminal front end:  uv run python main.py [--thread NAME] [--report] [--delete FILE]"""

from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys

from . import approvals
from .config import ConfigError, Settings, load_settings
from .report import build_report
from .sessions import load_all
from .workspace import ApprovalRequired, Workspace, WorkspaceError

DEFAULTS = {"role": "ML engineer (campus placement)", "round": "ML fundamentals", "difficulty": "medium"}


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def say(text: str) -> None:
    print(_c("MockMate", "1;36"), text)


def read_answer() -> str:
    """Read an answer. End a line with a backslash to continue on the next line."""
    lines = []
    prompt = _c("You     ", "1;32")
    while True:
        line = input(f"{prompt} ")
        if line.endswith("\\"):
            lines.append(line[:-1])
            prompt = "        "
            continue
        lines.append(line)
        return "\n".join(lines).strip()


def normalise_round(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("behav", "hr", "star")):
        return "behavioural"
    if any(k in t for k in ("dsa", "algo", "data struct")):
        return "DSA"
    if any(k in t for k in ("ml", "machine", "fundamental")):
        return "ML fundamentals"
    return text.strip() or DEFAULTS["round"]


def normalise_difficulty(text: str) -> str:
    t = text.lower().strip()
    return t if t in ("easy", "medium", "hard") else "medium"


def setup_profile(input_fn=input, output=say) -> dict:
    role = input_fn("What role are you preparing for? (or type 'just start') > ").strip()
    if not role or "just start" in role.lower():
        output(
            f"Starting with defaults: role = {DEFAULTS['role']}, round = {DEFAULTS['round']}, "
            f"difficulty = {DEFAULTS['difficulty']}."
        )
        return dict(DEFAULTS)
    rnd = input_fn("Which round: ML fundamentals, DSA, or behavioural? > ").strip()
    rnd = DEFAULTS["round"] if "just start" in rnd.lower() or not rnd else normalise_round(rnd)
    diff_raw = input_fn("Difficulty: easy, medium or hard? [medium] > ")
    diff = normalise_difficulty(diff_raw)
    if diff_raw.strip().lower() != diff:
        output("Difficulty not recognised or skipped, using medium.")
    return {"role": role, "round": rnd, "difficulty": diff}


def _reply_for(payload: dict):
    if payload["type"] == "answer":
        answer = read_answer()
        if answer.lower() in ("/quit", "/exit"):
            raise KeyboardInterrupt
        return answer
    return approvals.ask_overwrite_approval(payload)


def delete_session(ws: Workspace, name: str) -> int:
    rel = f"sessions/{name}"
    try:
        ws.resolve(rel)  # fence check first, so a bad path is refused before any prompt
        if not approvals.confirm_delete(rel):
            print("Rejected. File left untouched.")
            return 0
        ws.delete_file(rel, approved=True)
    except (WorkspaceError, ApprovalRequired) as exc:
        print(exc)
        return 1
    print(f"Deleted {rel}.")
    return 0


def run_interview(settings: Settings, ws: Workspace, thread: str) -> int:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.types import Command

        from .graph import build_graph
        from .llm import get_llm

        llm = get_llm(settings)
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run `uv sync` first (and `uv add langchain-<provider>` for other providers).")
        return 1

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    graph = build_graph(settings, llm, ws).compile(checkpointer=SqliteSaver(conn))
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 100}

    snap = graph.get_state(cfg)
    try:
        if not snap.values:
            profile = setup_profile()
            payload = {
                "profile": profile,
                "thread": thread,
                "total": settings.questions,
                "started": dt.date.today().isoformat(),
            }
        else:
            if snap.values.get("final") and not snap.next:
                print(f"Thread '{thread}' already finished. Use --thread NEW_NAME to start a fresh interview, or --report.")
                return 0
            v = snap.values
            say(
                f"Resuming thread '{thread}': {v['profile']['round']} for {v['profile']['role']} "
                f"({v['profile']['difficulty']}), question {v.get('q_index', 0) + 1} of {v['total']}."
            )
            pending = [i.value for t in snap.tasks for i in t.interrupts]
            if pending:
                if pending[0]["type"] == "answer":
                    say(f"Question {pending[0]['index']} of {pending[0]['total']}\n{pending[0]['question']}")
                payload = Command(resume=_reply_for(pending[0]))
            else:
                payload = None  # a step failed earlier (for example a network error): retry it

        while True:
            interrupted = None
            for chunk in graph.stream(payload, cfg, stream_mode="updates"):
                if "__interrupt__" in chunk:
                    interrupted = chunk["__interrupt__"][0].value
                    continue
                for update in chunk.values():
                    if isinstance(update, dict) and update.get("say"):
                        say(update["say"])
            if interrupted is None:
                return 0
            payload = Command(resume=_reply_for(interrupted))
    except (KeyboardInterrupt, EOFError):
        print(f"\nProgress saved. Run again with --thread {thread} to continue.")
        return 0
    except Exception as exc:  # network / API / validation failure: state is already checkpointed
        print(f"\nError: {exc}\nYour progress is saved. Run again with --thread {thread} to retry the failed step.")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mockmate", description="Terminal mock-interview agent.")
    parser.add_argument("--thread", default="default", help="interview thread id; a new id starts a fresh interview")
    parser.add_argument("--report", action="store_true", help="print a report rebuilt from workspace/sessions")
    parser.add_argument("--delete", metavar="FILE", help="delete a session file (asks for approval)")
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Config error: {exc}")
        return 2
    ws = Workspace(settings.workspace)

    if args.report:
        print(build_report(load_all(ws)))
        return 0
    if args.delete:
        return delete_session(ws, args.delete)
    return run_interview(settings, ws, args.thread)
