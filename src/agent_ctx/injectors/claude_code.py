"""Injector Claude Code: escreve ``.claude/agent-context.md`` no projeto.

Cria um resumo markdown do handover que o Claude Code pode ler no início
de uma sessão. Não sobrescreve ``CLAUDE.md`` — escreve em arquivo separado.
"""

from __future__ import annotations

from pathlib import Path

from agent_ctx.core.schema import HandoverPayload
from agent_ctx.injectors.base import InjectionResult

_MAX_LOG_ENTRIES = 10


class ClaudeCodeInjector:
    """Escreve um resumo markdown do handover em ``.claude/agent-context.md``."""

    def inject(
        self, project_path: str, payload: HandoverPayload
    ) -> InjectionResult:
        target = Path(project_path) / ".claude"
        target.mkdir(parents=True, exist_ok=True)
        dest = target / "agent-context.md"
        content = _render(payload)
        dest.write_text(content, encoding="utf-8")
        return InjectionResult(injected=True, file_path=str(dest))


def _render(payload: HandoverPayload) -> str:
    lines: list[str] = []
    lines.append(f"# Handover: {payload.intent_summary}")
    lines.append("")
    lines.append(
        f"**Origem:** {payload.source_agent} → **Destino:** {payload.target_agent}"
    )
    lines.append(f"**Projeto:** {payload.project_path}")
    lines.append("")

    if payload.recent_files:
        lines.append("## Arquivos recentes")
        lines.append("")
        for rf in payload.recent_files:
            lines.append(f"- `{rf.path}`")
        lines.append("")

    logs = payload.last_conversation_logs[:_MAX_LOG_ENTRIES]
    if logs:
        lines.append("## Últimas mensagens")
        lines.append("")
        for log in logs:
            lines.append(f"**{log.role}:** {log.content}")
            lines.append("")

    return "\n".join(lines)
