"""Injector universal: escreve ``.agent-ctx/handover.json`` no projeto.

Qualquer agente pode ler este arquivo para retomar o contexto.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_ctx.core.schema import HandoverPayload
from agent_ctx.injectors.base import InjectionResult


class ProjectInjector:
    """Escreve o HandoverPayload completo como JSON no diretório do projeto."""

    def inject(
        self, project_path: str, payload: HandoverPayload
    ) -> InjectionResult:
        target = Path(project_path) / ".agent-ctx"
        target.mkdir(parents=True, exist_ok=True)
        dest = target / "handover.json"
        dest.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
        return InjectionResult(injected=True, file_path=str(dest))


def read_handover(project_path: str) -> HandoverPayload | None:
    """Lê ``.agent-ctx/handover.json`` do projeto, ou ``None`` se não existir."""
    src = Path(project_path) / ".agent-ctx" / "handover.json"
    if not src.exists():
        return None
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        return HandoverPayload.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None
