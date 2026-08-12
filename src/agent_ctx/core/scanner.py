"""Scanner de arquivos recentemente modificados no diretório do projeto.

Percorre o diretório do projeto ignorando pastas irrelevantes, verifica o mtime
de cada arquivo e, se alterado dentro da janela de minutos configurada, anexa
um preview do conteúdo como "diff" (PRD, Fase 2).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .schema import RecentFile

# Pastas que nunca contribuem com contexto de handover.
_IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".agent-ctx",
}

MAX_FILES = 50
_MAX_PREVIEW_BYTES = 50_000
_NULL_BYTE = b"\x00"


class Scanner:
    """Captura arquivos alterados numa janela de tempo.

    `now` injetável torna o comportamento determinístico em testes.
    """

    def __init__(
        self, minutes: int = 15, max_files: int = MAX_FILES, now: datetime | None = None
    ) -> None:
        self._window = timedelta(minutes=minutes)
        self._max_files = max_files
        self._now = now

    def recent_files(self, project_path: Path) -> list[RecentFile]:
        """Retorna arquivos modificados na janela, mais recentes primeiro."""
        root = project_path.resolve()
        if not root.is_dir():
            return []

        cutoff = (self._now or datetime.now(UTC)) - self._window
        candidates: list[RecentFile] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]
            for name in filenames:
                path = Path(dirpath) / name
                mtime = self._mtime_utc(path)
                if mtime is None or mtime < cutoff:
                    continue
                preview = self._diff_preview(path)
                if preview is None:
                    continue
                candidates.append(RecentFile(path=str(path), diff=preview, mtime=mtime))

        candidates.sort(
            key=lambda rf: rf.mtime or datetime.min.replace(tzinfo=UTC), reverse=True
        )
        return candidates[: self._max_files]

    @staticmethod
    def _mtime_utc(path: Path) -> datetime | None:
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return None
        return datetime.fromtimestamp(mtime_ns / 1e9, tz=UTC)

    @staticmethod
    def _diff_preview(path: Path) -> str | None:
        """Lê um preview do conteúdo; retorna None para binários/ilegíveis."""
        try:
            with path.open("rb") as fh:
                data = fh.read(_MAX_PREVIEW_BYTES)
        except OSError:
            return None
        if _NULL_BYTE in data:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None
