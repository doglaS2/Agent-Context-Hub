"""Extrator do histórico de chat do VS Code (Copilot Chat).

Sessões ficam em ``User/workspaceStorage/<hash>/chatSessions/<id>.json`` com
``requests[].message.parts[].text`` para prompts de usuário. As respostas do
assistente não são persistidas de forma estável nesta versão do VS Code — o
lado conversa é user-only.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_ctx.core.schema import ConversationLog
from agent_ctx.extractors.base import ExtractedContext
from agent_ctx.extractors.state_vscdb import find_workspace_dir

_DEFAULT_ROOT = Path.home() / "AppData" / "Roaming" / "Code"
_MAX_MESSAGES = 20
_MAX_SUMMARY_CHARS = 200
_MAX_SESSIONS = 10


class VSCodeExtractor:
    """Extrai prompts de usuário das sessões recentes de chat do projeto."""

    def __init__(self, root: Path = _DEFAULT_ROOT) -> None:
        self._root = root

    def extract(self, project_path: str) -> ExtractedContext:
        workspace = find_workspace_dir(self._root, project_path)
        if workspace is None:
            return ExtractedContext(intent_summary=f"Handover de {project_path}")
        prompts, summary = self._read_sessions(workspace / "chatSessions")
        logs = [ConversationLog(role="user", content=text) for text in prompts]
        default = f"Handover de {project_path}"
        return ExtractedContext(
            intent_summary=(summary or default)[:_MAX_SUMMARY_CHARS],
            conversation_logs=logs,
        )

    @staticmethod
    def _read_sessions(chat_dir: Path) -> tuple[list[str], str | None]:
        if not chat_dir.is_dir():
            return [], None
        try:
            files = sorted(
                (p for p in chat_dir.glob("*.json") if p.is_file()),
                key=lambda p: p.stat().st_mtime_ns,
                reverse=True,
            )
        except OSError:
            return [], None
        prompts: list[str] = []
        summary: str | None = None
        for session_file in files[:_MAX_SESSIONS]:
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            requests = data.get("requests") if isinstance(data, dict) else None
            if not isinstance(requests, list):
                continue
            for req in requests:
                if not isinstance(req, dict):
                    continue
                text = _request_user_text(req)
                if text is None:
                    continue
                if summary is None:
                    summary = text
                prompts.append(text)
        return prompts[-_MAX_MESSAGES:], summary


def _request_user_text(req: dict) -> str | None:
    message = req.get("message")
    parts = message.get("parts") if isinstance(message, dict) else None
    if not isinstance(parts, list):
        return None
    texts = [
        part.get("text")
        for part in parts
        if isinstance(part, dict)
        and isinstance(part.get("text"), str)
        and part["text"].strip()
    ]
    joined = "\n".join(texts).strip()
    return joined or None
