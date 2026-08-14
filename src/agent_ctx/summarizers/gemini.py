"""Sumarizador semântico usando Google Gemini."""

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
    pass

logger = logging.getLogger(__name__)


class GeminiDiffSummarizer(BaseDiffSummarizer):
    """Sumarizador que usa Google Gemini, com fallback heurístico."""

    def __init__(
        self, api_key: str | None = None, model: str = "gemini-1.5-flash"
    ) -> None:
        self._api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self._model = model
        self._configured = False

    def _configure_client(self) -> bool:
        if not self._api_key:
            return False
        if not self._configured:
            try:
                import google.generativeai as genai
            except ImportError:
                logger.warning(
                    "google-generativeai não instalado; usando fallback local."
                )
                return False
            genai.configure(api_key=self._api_key)
            self._configured = True
        return True

    def summarize(self, raw_diff: str, intent_hint: str = "") -> SemanticSummary:
        if not raw_diff.strip():
            return SemanticSummary(
                summary="Diff vazio: nenhuma alteração para sumarizar.",
                impact_areas=[],
                intent=intent_hint,
                token_count_diff=0,
            )

        if not self._configure_client():
            logger.info("Gemini indisponível; retornando sumarização local.")
            return local_summary(raw_diff, intent_hint)

        trimmed = raw_diff[:_MAX_DIFF_TOKENS_ESTIMATE]
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel(
                model_name=self._model,
                system_instruction=_SYSTEM_PROMPT,
            )
            prompt = (
                f"Contexto/intenção: {intent_hint or 'não informado'}\n\n"
                f"```diff\n{trimmed}\n```"
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=_SUMMARY_MAX_TOKENS,
                    temperature=0.2,
                ),
            )
            content = response.text or ""
        except Exception as exc:
            logger.warning("Erro ao chamar Gemini: %s; usando fallback local.", exc)
            return local_summary(raw_diff, intent_hint)

        parsed = self.parse_json(content)
        if parsed is None:
            logger.warning("Gemini retornou JSON inválido; usando fallback local.")
            return local_summary(raw_diff, intent_hint)

        return self.build_summary(parsed, raw_diff)
