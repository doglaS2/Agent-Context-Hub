"""Testes dos modelos Pydantic do Schema Universal."""

from __future__ import annotations

import uuid
from typing import ClassVar

import pytest
from pydantic import ValidationError

from agent_ctx.core.schema import (
    HandoverPayload,
    RecentFile,
)

_VALID_RAW: dict = {
    "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
    "timestamp": "2026-08-11T21:00:00Z",
    "source_agent": "claude-code",
    "target_agent": "cursor",
    "project_path": "/home/user/projects/agripampa",
    "intent_summary": "Implementação da rota de streaming em tempo real no FastAPI",
    "recent_files": [
        {
            "path": "backend/api.py",
            "diff": "@@ -45,3 +45,12 @@",
            "mtime": "2026-08-11T20:55:00Z",
        },
    ],
    "last_conversation_logs": [
        {"role": "user", "content": "Crie o endpoint de streaming."},
        {"role": "assistant", "content": "Entendido. Usarei geradores."},
    ],
}


class TestHandoverPayload:
    """Validação do contrato JSON Universal completo."""

    def test_payload_valido(self) -> None:
        p = HandoverPayload.model_validate(_VALID_RAW)
        assert p.source_agent == "claude-code"
        assert p.target_agent == "cursor"
        assert p.id == uuid.UUID("3f2504e0-4f89-41d3-9a0c-0305e82c3301")
        assert len(p.recent_files) == 1
        assert len(p.last_conversation_logs) == 2

    def test_payload_sem_opcionais(self) -> None:
        base = {
            k: v
            for k, v in _VALID_RAW.items()
            if k not in ("recent_files", "last_conversation_logs")
        }
        p = HandoverPayload.model_validate(base)
        assert p.recent_files == []
        assert p.last_conversation_logs == []

    def test_uuid_auto_gerado(self) -> None:
        base = {k: v for k, v in _VALID_RAW.items() if k != "id"}
        p = HandoverPayload.model_validate(base)
        assert isinstance(p.id, uuid.UUID)

    def test_timestamp_auto_gerado(self) -> None:
        base = {k: v for k, v in _VALID_RAW.items() if k != "timestamp"}
        p = HandoverPayload.model_validate(base)
        assert p.timestamp is not None

    def test_roundtrip_json(self) -> None:
        p = HandoverPayload.model_validate(_VALID_RAW)
        p2 = HandoverPayload.model_validate_json(p.model_dump_json())
        assert p == p2

    def test_modelo_frozen(self) -> None:
        p = HandoverPayload.model_validate(_VALID_RAW)
        with pytest.raises(ValidationError):
            p.intent_summary = "mutado"  # type: ignore[misc]


class TestCamposObrigatorios:
    """Campos obrigatórios rejeitam valores vazios."""

    @pytest.mark.parametrize(
        "campo",
        ["source_agent", "target_agent", "project_path", "intent_summary"],
    )
    def test_campo_vazio_rejeitado(self, campo: str) -> None:
        dados = dict(_VALID_RAW, **{campo: ""})
        with pytest.raises(ValidationError):
            HandoverPayload.model_validate(dados)

    def test_summary_vazio_rejeitado(self) -> None:
        dados = {**_VALID_RAW, "intent_summary": ""}
        with pytest.raises(ValidationError):
            HandoverPayload.model_validate(dados)


class TestAgentes:
    """Source e target devem ser IDs de agentes conhecidos."""

    AGENTES_CONHECIDOS: ClassVar[tuple[str, ...]] = (
        "claude-code", "cursor", "vscode", "antigravity", "generic",
    )

    @pytest.mark.parametrize("agente", AGENTES_CONHECIDOS)
    def test_agente_valido(self, agente: str) -> None:
        dados = {**_VALID_RAW, "source_agent": agente}
        p = HandoverPayload.model_validate(dados)
        assert p.source_agent == agente

    def test_agente_desconhecido_rejeitado(self) -> None:
        dados = {**_VALID_RAW, "source_agent": "alice-ai"}
        with pytest.raises(ValidationError):
            HandoverPayload.model_validate(dados)

    def test_agente_numerico_rejeitado(self) -> None:
        dados = {**_VALID_RAW, "source_agent": 42}
        with pytest.raises(ValidationError):
            HandoverPayload.model_validate(dados)


class TestConversaEArquivos:
    """Validação de sub-modelos RecentFile e ConversationLog."""

    def test_role_invalido_rejeitado(self) -> None:
        dados = dict(_VALID_RAW)
        dados["last_conversation_logs"] = [{"role": "admin", "content": "x"}]
        with pytest.raises(ValidationError):
            HandoverPayload.model_validate(dados)

    def test_role_validos(self) -> None:
        for role in ("user", "assistant", "system", "tool"):
            dados = dict(_VALID_RAW)
            dados["last_conversation_logs"] = [{"role": role, "content": "ok"}]
            p = HandoverPayload.model_validate(dados)
            assert p.last_conversation_logs[0].role == role

    def test_conteudo_log_vazio_rejeitado(self) -> None:
        dados = dict(_VALID_RAW)
        dados["last_conversation_logs"] = [{"role": "user", "content": ""}]
        with pytest.raises(ValidationError):
            HandoverPayload.model_validate(dados)

    def test_recent_file_valido(self) -> None:
        rf = RecentFile(path="main.py", diff="@@ +1,1 @@")
        assert rf.path == "main.py"
        assert rf.diff is not None

    def test_recent_file_path_vazio(self) -> None:
        with pytest.raises(ValidationError):
            RecentFile(path="", diff=None)
