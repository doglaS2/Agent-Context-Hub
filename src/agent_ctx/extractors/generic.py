"""Extrator para o agente ``generic`` (fallback do schema).

Sem estado local conhecido: devolve apenas um resumo do projeto.
"""

from __future__ import annotations

from agent_ctx.extractors.base import ExtractedContext


class GenericExtractor:
    """Extrator de fallback: resumo genérico, sem logs de conversa."""

    def extract(self, project_path: str) -> ExtractedContext:
        return ExtractedContext(intent_summary=f"Handover de {project_path}")
