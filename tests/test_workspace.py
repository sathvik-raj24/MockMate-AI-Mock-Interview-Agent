import os

import pytest

from mockmate.workspace import ApprovalRequired, WorkspaceError


def test_relative_parent_escape_refused(ws):
    with pytest.raises(WorkspaceError):
        ws.write_file("../secrets.txt", "x")
    assert not (ws.root.parent / "secrets.txt").exists()


def test_absolute_path_refused(ws):
    with pytest.raises(WorkspaceError):
        ws.write_file("/tmp/outside.txt", "x")


def test_absolute_path_to_real_outside_file_refused(ws, tmp_path):
    target = tmp_path / "outside.txt"
    with pytest.raises(WorkspaceError):
        ws.write_file(str(target), "x")
    assert not target.exists()


def test_nested_escape_refused(ws):
    with pytest.raises(WorkspaceError):
        ws.write_file("sessions/../../outside.txt", "x")


def test_symlink_escape_refused(ws, tmp_path):
    outside = tmp_path / "outside_dir"
    outside.mkdir()
    try:
        os.symlink(outside, ws.root / "link")
    except OSError:
        pytest.skip("symlinks not available on this platform")
    with pytest.raises(WorkspaceError):
        ws.write_file("link/x.txt", "x")
    assert not (outside / "x.txt").exists()


def test_empty_path_refused(ws):
    with pytest.raises(WorkspaceError):
        ws.write_file("  ", "x")


def test_normal_write_inside_workspace(ws):
    ws.write_file("sessions/a.md", "hello")
    assert ws.read_text("sessions/a.md") == "hello"


def test_first_weak_file_write_needs_no_approval_but_overwrite_does(ws):
    ws.write_file("weak-topics.md", "v1")
    with pytest.raises(ApprovalRequired):
        ws.write_file("weak-topics.md", "v2")
    assert ws.read_text("weak-topics.md") == "v1"  # rejection leaves the file untouched
    ws.write_file("weak-topics.md", "v2", approved=True)
    assert ws.read_text("weak-topics.md") == "v2"


def test_delete_needs_approval(ws):
    ws.write_file("sessions/a.md", "x")
    with pytest.raises(ApprovalRequired):
        ws.delete_file("sessions/a.md")
    assert ws.exists("sessions/a.md")
    ws.delete_file("sessions/a.md", approved=True)
    assert not ws.exists("sessions/a.md")


def test_delete_outside_refused_even_when_approved(ws, tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me")
    with pytest.raises(WorkspaceError):
        ws.delete_file("../victim.txt", approved=True)
    assert victim.exists()
