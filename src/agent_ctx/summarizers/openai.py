"""Sumarizador semântico usando OpenAI GPT (gpt-4o ou gpt-4o-mini)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers.base import (
    _MAX_DIFF_TOKENS_ESTIMATE,
    _SUMMARY_MAX_TOKENS,
    _SYSTEM_PROMPT,
    BaseDiffSummarizer,
    local_summary,
)

if TYPE_CHECKING:
    from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIDiffSummarizer(BaseDiffSummarizer):
    """Sumarizador que usa OpenAI GPT, com fallback heurístico."""

    def __init__(
        self, api_key: str | None = None, model: str = "gpt-4o-mini"
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = model
        self._client: OpenAI | None = None

    def _load_client(self) -> OpenAI | None:
        if not self._api_key:
            return None
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                logger.warning("openai não instalado; usando fallback local.")
                return None
            self._client = OpenAI(api_key=self._api_key)
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
            logger.info("OpenAI indisponível; retornando sumarização local.")
            return local_summary(raw_diff, intent_hint)

        trimmed = raw_diff[:_MAX_DIFF_TOKENS_ESTIMATE]
        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=_SUMMARY_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Contexto/intenção: {intent_hint or 'não informado'}\n\n"
                            f"```diff\n{trimmed}\n```"
                        ),
                    },
                ],
            )
        except Exception as exc:
            logger.warning("Erro ao chamar OpenAI: %s; usando fallback local.", exc)
            return local_summary(raw_diff, intent_hint)

        content = response.choices[0].message.content or ""
        parsed = self.parse_json(content)
        if parsed is None:
            logger.warning("OpenAI retornou JSON inválido; usando fallback local.")
            return local_summary(raw_diff, intent_hint)

        return self.build_summary(parsed, raw_diff)
