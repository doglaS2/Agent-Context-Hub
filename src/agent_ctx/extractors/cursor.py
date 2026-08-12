"""Extrator do histórico de chat do Cursor (state.vscdb).

Lê os prompts de usuário de ``aiService.prompts`` e o resumo do composer atual
de ``composer.composerData``. Respostas do assistente não são persistidas de
forma estável pelo Cursor — nesta versão o lado conversa é user-only.
"""

from __future__ import annotations

from pathlib import Path

from agent_ctx.core.schema import ConversationLog
from agent_ctx.extractors.base import ExtractedContext
from agent_ctx.extractors.state_vscdb import find_workspace_dir, read_cursor_chat

_DEFAULT_ROOT = Path.home() / "AppData" / "Roaming" / "Cursor"
_MAX_SUMMARY_CHARS = 200


class CursorExtractor:
    """Extrai prompts e resumo do workspace do projeto no Cursor."""

    def __init__(self, root: Path = _DEFAULT_ROOT) -> None:
        self._root = root

    def extract(self, project_path: str) -> ExtractedContext:
        workspace = find_workspace_dir(self._root, project_path)
        if workspace is None:
            return ExtractedContext(intent_summary=f"Handover de {project_path}")
        chat = read_cursor_chat(workspace / "state.vscdb")
        logs = [
            ConversationLog(role="user", content=text) for text in chat.user_prompts
        ]
        default = f"Handover de {project_path}"
        summary = chat.summary or (logs[0].content if logs else default)
        return ExtractedContext(
            intent_summary=summary[:_MAX_SUMMARY_CHARS],
            conversation_logs=logs,
        )
