"""Contratos comuns dos injectors de estado para agentes-destino."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_ctx.core.schema import HandoverPayload


@dataclass(frozen=True)
class InjectionResult:
    """Resultado de uma operação de injeção de contexto."""

    injected: bool
    file_path: str | None = None
    message: str = ""


class Injector(Protocol):
    """Escreve o estado de handover no ambiente do agente-destino."""

    def inject(
        self, project_path: str, payload: HandoverPayload
    ) -> InjectionResult: ...
