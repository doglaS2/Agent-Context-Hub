"""Extrator do histórico de conversas do Claude Code (transcripts JSONL).

Os transcripts ficam em ``~/.claude/projects/<caminho-encode>/``, um arquivo
``.jsonl`` por sessão, com o caminho do projeto codificado trocando
``\\``, ``/``, ``:`` e ``.`` por ``-`` (ex.: ``C:\\Proj`` -> ``C--Proj``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_ctx.core.schema import ConversationLog
from agent_ctx.extractors.base import ExtractedContext

_PROJECTS_DIR = Path.home() / ".claude" / "projects"
_MAX_MESSAGES = 20
_MAX_SUMMARY_CHARS = 200
_MAX_CONTENT_CHARS = 20_000

# Marcadores de ruído que o Claude Code injeta no conteúdo de usuário
# (comandos locais, prompts de permissão, reminders de sistema).
_NOISE_PREFIXES = (
    "<command-name>",
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<permission-request>",
    "<system-reminder>",
)


def encode_project_path(project_path: str) -> str:
    """Codifica o caminho absoluto no nome usado por ~/.claude/projects."""
    return re.sub(r"[\\/:.]", "-", project_path)


class ClaudeCodeExtractor:
    """Lê o transcript mais recente do projeto e extrai a conversa útil."""

    def __init__(self, projects_dir: Path = _PROJECTS_DIR) -> None:
        self._projects_dir = projects_dir

    def extract(self, project_path: str) -> ExtractedContext:
        session_dir = self._projects_dir / encode_project_path(project_path)
        transcript = self._newest_transcript(session_dir)
        if transcript is None:
            return ExtractedContext(intent_summary=f"Handover de {project_path}")
        logs, summary = self._read_transcript(transcript)
        return ExtractedContext(intent_summary=summary, conversation_logs=logs)

    def _newest_transcript(self, session_dir: Path) -> Path | None:
        try:
            candidates = [p for p in session_dir.glob("*.jsonl") if p.is_file()]
        except OSError:
            return None
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime_ns)

    def _read_transcript(self, transcript: Path) -> tuple[list[ConversationLog], str]:
        try:
            lines = transcript.read_text(encoding="utf-8").splitlines()
        except OSError:
            return [], f"Handover de {transcript.parent.parent.name}"
        logs: list[ConversationLog] = []
        summary: str | None = None
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            role = entry.get("type") if isinstance(entry, dict) else None
            if role not in ("user", "assistant"):
                continue
            text = self._extract_text(entry.get("message"), role)
            if text is None:
                continue
            if role == "user" and summary is None:
                summary = text[:_MAX_SUMMARY_CHARS]
            logs.append(ConversationLog(role=role, content=text))
        default = f"Handover de {transcript.parent.parent.name}"
        return logs[-_MAX_MESSAGES:], (summary or default)

    @staticmethod
    def _extract_text(message: object, role: str) -> str | None:
        """Extrai o texto útil de ``message.content`` (str ou lista de blocos)."""
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Só blocos de texto puro: ignora tool_use/tool_result/thinking.
            texts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
                and isinstance(b.get("text"), str)
            ]
            text = "\n".join(t for t in texts if t.strip())
        else:
            return None
        text = text.strip()
        if not text:
            return None
        if role == "user" and any(text.startswith(p) for p in _NOISE_PREFIXES):
            return None
        return text[:_MAX_CONTENT_CHARS]
