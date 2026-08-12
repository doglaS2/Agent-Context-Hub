"""Contratos comuns dos extractors de estado dos agentes-fonte."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_ctx.core.schema import ConversationLog


@dataclass(frozen=True)
class ExtractedContext:
    """Resultado da leitura do estado local de um agente-fonte.

    ``conversation_logs`` captura o histórico recente (role user/assistant).
    """

    intent_summary: str
    conversation_logs: list[ConversationLog] = field(default_factory=list)


class Extractor(Protocol):
    """Lê o estado local de um agente e devolve o contexto de handover."""

    def extract(self, project_path: str) -> ExtractedContext: ...
