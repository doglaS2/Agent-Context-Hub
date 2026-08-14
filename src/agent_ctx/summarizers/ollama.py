"""Sumarizador semântico usando Ollama (modelos locais)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers.base import (
    _MAX_DIFF_TOKENS_ESTIMATE,
    _SYSTEM_PROMPT,
    BaseDiffSummarizer,
    local_summary,
)

logger = logging.getLogger(__name__)


class OllamaDiffSummarizer(BaseDiffSummarizer):
    """Sumarizador que usa Ollama local, com fallback heurístico."""

    def __init__(
        self,
        host: str | None = None,
        model: str = "llama3.2",
        timeout: float = 60.0,
    ) -> None:
        raw_host = (
            host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
        ).rstrip("/")
        self._host = raw_host if "://" in raw_host else f"http://{raw_host}"
        self._model = model
        self._timeout = timeout

    def summarize(self, raw_diff: str, intent_hint: str = "") -> SemanticSummary:
        if not raw_diff.strip():
            return SemanticSummary(
                summary="Diff vazio: nenhuma alteração para sumarizar.",
                impact_areas=[],
                intent=intent_hint,
                token_count_diff=0,
            )

        trimmed = raw_diff[:_MAX_DIFF_TOKENS_ESTIMATE]
        payload = json.dumps({
            "model": self._model,
            "prompt": (
                f"{_SYSTEM_PROMPT}\n\n"
                f"Contexto/intenção: {intent_hint or 'não informado'}\n\n"
                f"```diff\n{trimmed}\n```"
            ),
            "stream": False,
            "format": "json",
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self._host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = str(data.get("response", ""))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            logger.warning("Erro ao chamar Ollama: %s; usando fallback local.", exc)
            return local_summary(raw_diff, intent_hint)

        parsed = self.parse_json(content)
        if parsed is None:
            logger.warning("Ollama retornou JSON inválido; usando fallback local.")
            return local_summary(raw_diff, intent_hint)

        return self.build_summary(parsed, raw_diff)
