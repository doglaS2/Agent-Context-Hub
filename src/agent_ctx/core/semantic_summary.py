"""Modelo do payload enriquecido de sumarização semântica de diffs (AI-SPEC.md)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SemanticSummary(BaseModel):
    """Resumo semântico de um diff, pronto para handover entre agentes."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(
        min_length=1,
        max_length=10_000,
        description="Texto conciso do que mudou e por quê.",
    )
    impact_areas: list[str] = Field(
        default_factory=list,
        description="Módulos, arquivos ou funções afetadas.",
    )
    intent: str = Field(
        min_length=0,
        max_length=5_000,
        description="Intenção original inferida a partir do contexto.",
    )
    token_count_diff: int = Field(
        default=0,
        ge=0,
        description="Economia estimada de tokens em relação ao diff bruto.",
    )
