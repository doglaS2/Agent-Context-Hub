"""Testes do sumarizador semântico de diffs (ClaudeDiffSummarizer)."""

from __future__ import annotations

from agent_ctx.core.semantic_summary import SemanticSummary
from agent_ctx.summarizers.claude import ClaudeDiffSummarizer


def test_summarize_empty_diff() -> None:
    summarizer = ClaudeDiffSummarizer(api_key=None)
    result = summarizer.summarize("   ", intent_hint="testar vazio")
    assert isinstance(result, SemanticSummary)
    assert "vazio" in result.summary.lower()
    assert result.token_count_diff == 0


def test_summarize_local_fallback() -> None:
    summarizer = ClaudeDiffSummarizer(api_key=None)
    raw_diff = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,2 +1,3 %>\n"
        "+def nova_funcao():\n"
        "+    pass\n"
        "-x = 1\n"
    )
    result = summarizer.summarize(raw_diff, intent_hint="refatorar modulo foo")
    assert isinstance(result, SemanticSummary)
    assert any(path.endswith("src/foo.py") for path in result.impact_areas)
    assert result.intent == "refatorar modulo foo"
    assert result.token_count_diff >= 0
    assert len(result.summary) > 0
