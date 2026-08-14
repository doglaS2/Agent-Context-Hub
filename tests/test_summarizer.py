"""Testes dos sumarizadores semânticos (múltiplos provedores e factory)."""

from __future__ import annotations

import pytest

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers.claude import ClaudeDiffSummarizer
from agent_ctx.summarizers.factory import get_diff_summarizer
from agent_ctx.summarizers.gemini import GeminiDiffSummarizer
from agent_ctx.summarizers.local import LocalDiffSummarizer
from agent_ctx.summarizers.ollama import OllamaDiffSummarizer
from agent_ctx.summarizers.openai import OpenAIDiffSummarizer


def test_local_summarizer() -> None:
    summarizer = LocalDiffSummarizer()
    raw_diff = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,2 +1,3 @@\n"
        "+def nova_funcao():\n"
        "+    pass\n"
    )
    result = summarizer.summarize(raw_diff, intent_hint="testar local")
    assert isinstance(result, SemanticSummary)
    assert result.intent == "testar local"
    assert len(result.impact_areas) > 0


def test_factory_selection() -> None:
    s_local = get_diff_summarizer(provider="local")
    assert isinstance(s_local, LocalDiffSummarizer)

    s_openai = get_diff_summarizer(provider="openai")
    assert isinstance(s_openai, OpenAIDiffSummarizer)

    s_gemini = get_diff_summarizer(provider="gemini")
    assert isinstance(s_gemini, GeminiDiffSummarizer)

    s_ollama = get_diff_summarizer(provider="ollama")
    assert isinstance(s_ollama, OllamaDiffSummarizer)

    s_claude = get_diff_summarizer(provider="anthropic")
    assert isinstance(s_claude, ClaudeDiffSummarizer)


def test_factory_invalid_provider() -> None:
    with pytest.raises(ValueError, match="Provedor de sumarização inválido"):
        get_diff_summarizer(provider="invalid-provider")


def test_summarize_empty_diff() -> None:
    summarizer = LocalDiffSummarizer()
    result = summarizer.summarize("   ", intent_hint="vazio")
    assert isinstance(result, SemanticSummary)
    assert result.token_count_diff == 0
