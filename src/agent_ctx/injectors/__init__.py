"""Injectors — escritores de estado nas ferramentas de destino (Fase 3).

Módulos:
- ``base``: ``InjectionResult``, ``Injector`` (Protocol)
- ``project``: universal — escreve ``.agent-ctx/handover.json`` no projeto
- ``claude_code``: resumo markdown em ``.claude/agent-context.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_ctx.core.schema import AgentId
    from agent_ctx.injectors.base import Injector


def _resolve_injector(target_agent: AgentId) -> Injector:
    """Retorna o injector correto para o agente-alvo."""
    if target_agent == "claude-code":
        from agent_ctx.injectors.claude_code import ClaudeCodeInjector

        return ClaudeCodeInjector()

    from agent_ctx.injectors.project import ProjectInjector

    return ProjectInjector()
