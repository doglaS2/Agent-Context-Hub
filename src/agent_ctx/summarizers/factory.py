"""Factory para seleção do provedor de sumarização semântica."""

from __future__ import annotations

import os
from typing import Literal

from agent_ctx.summarizers import DiffSummarizer

Provider = Literal["anthropic", "openai", "gemini", "ollama", "local"]


def get_diff_summarizer(
    provider: str | None = None,
    model: str | None = None,
) -> DiffSummarizer:
    """Cria um sumarizador a partir do provedor configurado.

    Prioridade: argumento explícito > ``AGENT_CTX_SUMMARIZER_PROVIDER`` >
    detecção automática de chave disponível > fallback local (Claude sem chave).
    """
    selected = (
        provider or os.environ.get("AGENT_CTX_SUMMARIZER_PROVIDER") or ""
    ).lower()

    if not selected:
        if os.environ.get("ANTHROPIC_API_KEY"):
            selected = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            selected = "openai"
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            selected = "gemini"
        elif os.environ.get("OLLAMA_HOST"):
            selected = "ollama"
        else:
            selected = "local"

    if selected in {"anthropic", "claude"}:
        from agent_ctx.summarizers.claude import ClaudeDiffSummarizer

        return ClaudeDiffSummarizer(model=model or "claude-3-5-sonnet-20241022")
    if selected == "openai":
        from agent_ctx.summarizers.openai import OpenAIDiffSummarizer

        return OpenAIDiffSummarizer(model=model or "gpt-4o-mini")
    if selected in {"gemini", "google"}:
        from agent_ctx.summarizers.gemini import GeminiDiffSummarizer

        return GeminiDiffSummarizer(model=model or "gemini-1.5-flash")
    if selected == "ollama":
        from agent_ctx.summarizers.ollama import OllamaDiffSummarizer

        return OllamaDiffSummarizer(model=model or "llama3.2")
    if selected == "local":
        from agent_ctx.summarizers.local import LocalDiffSummarizer

        return LocalDiffSummarizer()

    valid = "anthropic, openai, gemini, ollama, local"
    raise ValueError(f"Provedor de sumarização inválido: {selected}. Opções: {valid}")
