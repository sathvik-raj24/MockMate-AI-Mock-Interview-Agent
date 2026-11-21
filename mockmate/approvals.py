"""Console approval prompts (approve / edit / reject) for destructive file operations."""

from __future__ import annotations


def ask_overwrite_approval(payload: dict, input_fn=input, output=print) -> dict:
    output("\n[approval needed] MockMate wants to overwrite workspace/weak-topics.md")
    output(payload.get("diff") or "(no diff available)")
    choice = input_fn("[a]pprove / [e]dit (drop topics) / [r]eject > ").strip().lower()
    if choice.startswith("a"):
        return {"decision": "approve"}
    if choice.startswith("e"):
        raw = input_fn("Topics to drop from the new file (comma-separated): ")
        return {"decision": "edit", "drop": [t.strip() for t in raw.split(",") if t.strip()]}
    return {"decision": "reject"}


def confirm_delete(name: str, input_fn=input) -> bool:
    return input_fn(f"[approval needed] Delete {name}? This cannot be undone. [y/N] > ").strip().lower() in ("y", "yes")
