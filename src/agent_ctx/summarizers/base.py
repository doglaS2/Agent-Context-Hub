"""Módulo base compartilhado para sumarizadores de diff."""

from __future__ import annotations

import json
import logging
import re

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers import DiffSummarizer

logger = logging.getLogger(__name__)

_MAX_DIFF_TOKENS_ESTIMATE = 100_000
_SUMMARY_MAX_TOKENS = 2_048
_SYSTEM_PROMPT = (
    "Você é um engenheiro sênior que resume diffs de código para handover entre "
    "agentes de IA. Dado um diff bruto, produza APENAS um objeto JSON com as chaves "
    "summary (string concisa), impact_areas (lista de strings), intent (string) e "
    "token_count_diff (int, estimativa de tokens economizados em relação ao "
    "diff bruto). Foque no porquê e no impacto funcional, não apenas em linhas "
    "adicionadas/removidas."
)


def estimate_tokens(text: str) -> int:
    """Estimativa rápida de tokens (~4 chars por token)."""
    return max(1, len(text) // 4)


def local_summary(raw_diff: str, intent_hint: str) -> SemanticSummary:
    """Fallback 100% local quando o LLM não está disponível."""
    lines = [line for line in raw_diff.splitlines() if line.strip()]
    changed_files = sorted({
        match.group(1)
        for line in lines
        if (match := re.search(r"^[+-]{3} (.+)", line))
    })
    added = sum(
        1 for line in lines if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in lines if line.startswith("-") and not line.startswith("---")
    )

    if not changed_files:
        summary = "Nenhuma alteração identificada no diff fornecido."
    else:
        summary = (
            f"Alteração local detectada em {len(changed_files)} arquivo(s): "
            f"{', '.join(changed_files[:5])}{'...' if len(changed_files) > 5 else ''}. "
            f"Aproximadamente {added} adições e {removed} remoções."
        )

    token_saving = max(0, estimate_tokens(raw_diff) - estimate_tokens(summary))
    return SemanticSummary(
        summary=summary,
        impact_areas=changed_files[:20],
        intent=intent_hint,
        token_count_diff=token_saving,
    )


class BaseDiffSummarizer(DiffSummarizer):
    """Classe base com utilitários de parsing e build de resumo."""

    @staticmethod
    def parse_json(text: str) -> dict | None:
        fences = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        candidates = [*fences, text.strip()]
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def build_summary(data: dict, raw_diff: str) -> SemanticSummary:
        summary = str(data.get("summary", "")).strip()
        if not summary:
            summary = "Resumo não fornecido pelo modelo."

        impact = data.get("impact_areas")
        if isinstance(impact, list):
            impact_areas = [str(item) for item in impact if item]
        else:
            impact_areas = []

        intent = str(data.get("intent", "")).strip()
        token_count_diff = data.get("token_count_diff")
        try:
            token_count_diff = (
                int(token_count_diff) if token_count_diff is not None else 0
            )
        except (TypeError, ValueError):
            token_count_diff = 0

        if token_count_diff <= 0:
            raw_tokens = estimate_tokens(raw_diff)
            summary_tokens = estimate_tokens(summary)
            token_count_diff = max(0, raw_tokens - summary_tokens)

        return SemanticSummary(
            summary=summary,
            impact_areas=impact_areas[:50],
            intent=intent,
            token_count_diff=token_count_diff,
        )
