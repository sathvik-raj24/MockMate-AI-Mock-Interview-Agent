"""Final report, rebuilt purely from the saved session files (reproducible)."""

from __future__ import annotations

from . import memory


def build_report(sessions: list[tuple[dict, list[dict]]]) -> str:
    if not sessions:
        return "No saved sessions yet. Run an interview first."
    scores = [r["card"]["score"] for _, recs in sessions for r in recs]
    stats = memory.aggregate(sessions)
    lines = [
        "=== MockMate report (from workspace/sessions) ===",
        f"Sessions: {len(sessions)}   Answers: {len(scores)}   Average: {sum(scores) / len(scores):.1f}/10",
        "",
        "Per session:",
    ]
    for meta, recs in sessions:
        avg = sum(r["card"]["score"] for r in recs) / len(recs)
        lines.append(
            f"  {meta.get('date', '?')}  {meta.get('thread', '?'):<12} {meta.get('round', '?')} "
            f"({meta.get('difficulty', '?')}): {len(recs)} answers, avg {avg:.1f}"
        )
    weak = [s for s in stats if s.avg < memory.WEAK_THRESHOLD][:3]
    lines.append("")
    if weak:
        lines.append("Weakest topics:")
        lines += [f"  - {s.topic} ({s.round}): avg {s.avg:.1f} over {s.attempts} attempt(s)" for s in weak]
    else:
        lines.append("No weak topics: every topic averages 6.0 or above.")
    return "\n".join(lines)
