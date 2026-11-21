"""The workspace fence. Every file operation goes through here, so a bad path is refused by
the tool itself (not just by the system prompt), and destructive operations need approval."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

WEAK_FILE = "weak-topics.md"


class WorkspaceError(Exception):
    """A path was refused or a file operation is not possible."""


class ApprovalRequired(Exception):
    """A destructive operation was attempted without explicit approval."""


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        (self.root / "sessions").mkdir(parents=True, exist_ok=True)

    # -- fence ---------------------------------------------------------------------------
    def resolve(self, rel: str) -> Path:
        if not isinstance(rel, str) or not rel.strip() or "\x00" in rel:
            raise WorkspaceError("Refused: empty or invalid path.")
        p = Path(rel)
        if p.is_absolute() or p.anchor or p.drive:
            raise WorkspaceError(f"Refused: absolute paths are not allowed ({rel!r}).")
        full = (self.root / p).resolve()  # resolves '..' and symlinks
        if full != self.root and self.root not in full.parents:
            raise WorkspaceError(f"Refused: {rel!r} is outside the workspace.")
        return full

    # -- reads ---------------------------------------------------------------------------
    def exists(self, rel: str) -> bool:
        return self.resolve(rel).is_file()

    def read_text(self, rel: str) -> str:
        path = self.resolve(rel)
        if not path.is_file():
            raise WorkspaceError(f"No such file: {rel}")
        return path.read_text(encoding="utf-8")

    def list_sessions(self) -> list[str]:
        d = self.root / "sessions"
        return sorted(f"sessions/{p.name}" for p in d.glob("*.md"))

    # -- writes --------------------------------------------------------------------------
    def write_file(self, rel: str, content: str, *, approved: bool = False) -> Path:
        path = self.resolve(rel)
        if rel.replace("\\", "/") == WEAK_FILE and path.exists() and not approved:
            raise ApprovalRequired(f"Overwriting {WEAK_FILE} needs approval.")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return path

    def delete_file(self, rel: str, *, approved: bool = False) -> None:
        path = self.resolve(rel)
        if not approved:
            raise ApprovalRequired(f"Deleting {rel} needs approval.")
        if not path.is_file():
            raise WorkspaceError(f"No such file: {rel}")
        path.unlink()
