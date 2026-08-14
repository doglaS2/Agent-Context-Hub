"""Sumarizador semântico de diffs usando Claude Sonnet com fallback local.

A camada de LLM é opcional: se ``ANTHROPIC_API_KEY`` não estiver configurada,
o sumarizador usa heurísticas locais para não quebrar o fluxo local-first.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import TYPE_CHECKING

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers import DiffSummarizer

if TYPE_CHECKING:
    from anthropic import Anthropic

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


def _estimate_tokens(text: str) -> int:
    """Estimativa rápida de tokens (~4 chars por token)."""
    return max(1, len(text) // 4)


def _local_summary(raw_diff: str, intent_hint: str) -> SemanticSummary:
    """Fallback 100% local quando o Claude não está disponível."""
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

    token_saving = max(0, _estimate_tokens(raw_diff) - _estimate_tokens(summary))
    return SemanticSummary(
        summary=summary,
        impact_areas=changed_files[:20],
        intent=intent_hint,
        token_count_diff=token_saving,
    )


class ClaudeDiffSummarizer(DiffSummarizer):
    """Sumarizador que usa Claude Sonnet, com fallback heurístico."""

    def __init__(
        self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model
        self._client: Anthropic | None = None

    def _load_client(self) -> Anthropic | None:
        if not self._api_key:
            return None
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                logger.warning("anthropic não instalado; usando fallback local.")
                return None
            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def summarize(self, raw_diff: str, intent_hint: str = "") -> SemanticSummary:
        if not raw_diff.strip():
            return SemanticSummary(
                summary="Diff vazio: nenhuma alteração para sumarizar.",
                impact_areas=[],
                intent=intent_hint,
                token_count_diff=0,
            )

        client = self._load_client()
        if client is None:
            logger.info("Claude indisponível; retornando sumarização local.")
            return _local_summary(raw_diff, intent_hint)

        trimmed = raw_diff[:_MAX_DIFF_TOKENS_ESTIMATE]
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=_SUMMARY_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Contexto/intenção: {intent_hint or 'não informado'}\n\n"
                            f"```diff\n{trimmed}\n```"
                        ),
                    }
                ],
            )
        except Exception as exc:
            logger.warning("Erro ao chamar Claude: %s; usando fallback local.", exc)
            return _local_summary(raw_diff, intent_hint)

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        parsed = self._parse_json(content)
        if parsed is None:
            logger.warning("Claude retornou JSON inválido; usando fallback local.")
            return _local_summary(raw_diff, intent_hint)

        return self._build_summary(parsed, raw_diff)

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        # Tenta extrair JSON de code fences ou do texto puro.
        fences = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        candidates = [*fences, text.strip()]
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _build_summary(data: dict, raw_diff: str) -> SemanticSummary:
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
            raw_tokens = _estimate_tokens(raw_diff)
            summary_tokens = _estimate_tokens(summary)
            token_count_diff = max(0, raw_tokens - summary_tokens)

        return SemanticSummary(
            summary=summary,
            impact_areas=impact_areas[:50],
            intent=intent,
            token_count_diff=token_count_diff,
        )
