from conftest import make_record
from mockmate import memory
from mockmate.report import build_report
from mockmate.sessions import load_all, parse_session, render_session, safe_name, session_path

META = {"thread": "t1", "role": "ML engineer", "round": "ML fundamentals", "difficulty": "medium", "date": "2026-11-21"}


def sessions():
    return [
        (META, [make_record(1, "Regularisation", 3), make_record(2, "Hash maps", 8)]),
        ({**META, "thread": "t2", "date": "2026-11-22"}, [make_record(1, "regularisation", 5)]),
    ]


def test_session_roundtrip_with_tricky_answer():
    answer = "line one\n```python\nprint('hi')\n```\nünïcode ✓ <!-- not a marker -->"
    recs = [make_record(1, "Regularisation", 4, answer)]
    meta, parsed = parse_session(render_session(META, recs))
    assert meta["role"] == "ML engineer" and meta["round"] == "ML fundamentals"
    assert parsed == recs


def test_session_file_records_role_and_round():
    text = render_session(META, [make_record(1, "X", 5)])
    assert "role: ML engineer" in text and "round: ML fundamentals" in text


def test_aggregate_merges_topics_case_insensitively():
    stats = {s.topic.lower(): s for s in memory.aggregate(sessions())}
    assert stats["regularisation"].attempts == 2
    assert stats["regularisation"].avg == 4.0
    assert stats["regularisation"].last_seen == "2026-11-22"


def test_weak_topics_roundtrip_and_threshold():
    text = memory.render(memory.aggregate(sessions()))
    parsed = memory.parse(text)
    assert [s.topic for s in parsed] == ["Regularisation", "Hash maps"]  # sorted worst first
    assert memory.weak_for_round(parsed, "ML fundamentals") == ["Regularisation"]
    assert memory.weak_for_round(parsed, "DSA") == []


def test_render_is_deterministic():
    assert memory.render(memory.aggregate(sessions())) == memory.render(memory.aggregate(sessions()))


def test_drop_topics_for_edit_choice():
    text = memory.render(memory.aggregate(sessions()))
    edited = memory.drop_topics(text, ["regularisation"])
    assert "Regularisation" not in edited and "Hash maps" in edited


def test_diff_shows_change():
    assert "+" in memory.make_diff("a\nb", "a\nc")


def test_report_reproducible_from_files(ws):
    for meta, recs in sessions():
        ws.write_file(session_path(meta["date"], meta["thread"]), render_session(meta, recs))
    first = build_report(load_all(ws))
    second = build_report(load_all(ws))
    assert first == second
    assert "Sessions: 2" in first and "Answers: 3" in first and "Regularisation" in first


def test_damaged_session_file_is_skipped(ws):
    ws.write_file("sessions/bad.md", "---\nthread: x\n---\n<!--mm-->{not json<!--/mm-->")
    assert load_all(ws) == []


def test_session_name_is_sanitised():
    assert safe_name("../../evil name") == "evil-name"
    assert session_path("2026-11-21", "my thread") == "sessions/2026-11-21_my-thread.md"
