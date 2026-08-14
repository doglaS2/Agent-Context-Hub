"""Interface base para sumarizadores de diff."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_ctx.core.semantic_summary import SemanticSummary


class DiffSummarizer(ABC):
    """Interface para sumarização semântica de diffs."""

    @abstractmethod
    def summarize(self, raw_diff: str, intent_hint: str = "") -> SemanticSummary:
        """Processa um diff bruto e retorna o payload enriquecido."""
        ...


__all__ = ["DiffSummarizer"]
