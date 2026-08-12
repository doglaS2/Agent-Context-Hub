"""Schema Universal (Common Schema JSON) — contratos Pydantic v2 (PRD v3.0, seção 3).

É a fonte da verdade da transferência de estado entre agentes: extractors
produzem ``HandoverPayload`` e injectors o consomem. Dados nunca saem da máquina.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Identificadores canônicos das fontes/destinos suportadas (PRD v3.0).
AgentId = Literal["claude-code", "cursor", "vscode", "antigravity", "generic"]

# Textos não vazios com teto de tamanho — protege o banco de payloads monstruosos.
NonEmptyStr = Annotated[str, StringConstraints(min_length=1, max_length=200_000)]


class RecentFile(BaseModel):
    """Arquivo modificado recentemente, capturado pelo file scanner (por mtime)."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1, max_length=4096)
    diff: str | None = Field(default=None, max_length=500_000)
    mtime: datetime | None = Field(default=None)


class ConversationLog(BaseModel):
    """Turno recente da conversa do agente de origem."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant", "system", "tool"]
    content: NonEmptyStr


class HandoverPayload(BaseModel):
    """Contrato JSON Universal de um handover entre agentes."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    source_agent: AgentId
    target_agent: AgentId
    project_path: str = Field(min_length=1, max_length=4096)
    intent_summary: str = Field(min_length=1, max_length=20_000)
    recent_files: list[RecentFile] = Field(default_factory=list)
    last_conversation_logs: list[ConversationLog] = Field(default_factory=list)
