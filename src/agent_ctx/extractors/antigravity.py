"""Extrator do Antigravity (best-effort).

O Antigravity não expõe (nesta versão) um armazenamento local de histórico
legível e estável. O extrator entrega um resumo genérico, sem conversa.
"""

from __future__ import annotations

from agent_ctx.extractors.base import ExtractedContext


class AntigravityExtractor:
    """Extrator genérico: apenas resumo do projeto, sem logs de conversa."""

    def extract(self, project_path: str) -> ExtractedContext:
        return ExtractedContext(intent_summary=f"Handover de {project_path}")
