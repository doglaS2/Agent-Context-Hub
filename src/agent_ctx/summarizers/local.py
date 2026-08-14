"""Sumarizador heurístico 100% local."""

from __future__ import annotations

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers.base import BaseDiffSummarizer, local_summary


class LocalDiffSummarizer(BaseDiffSummarizer):
    """Sumarizador local sem dependências externas ou chamadas de rede."""

    def summarize(self, raw_diff: str, intent_hint: str = "") -> SemanticSummary:
        if not raw_diff.strip():
            return SemanticSummary(
                summary="Diff vazio: nenhuma alteração para sumarizar.",
                impact_areas=[],
                intent=intent_hint,
                token_count_diff=0,
            )
        return local_summary(raw_diff, intent_hint)
