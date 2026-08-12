"""Testes da camada de persistência SQLite (database.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_ctx.core.database import (
    SCHEMA_VERSION,
    Database,
    DatabaseError,
    default_db_path,
)
from agent_ctx.core.schema import HandoverPayload

_VALID_RAW: dict = {
    "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
    "timestamp": "2026-08-11T21:00:00Z",
    "source_agent": "claude-code",
    "target_agent": "cursor",
    "project_path": "/home/user/projects/agripampa",
    "intent_summary": "Implementação da rota de streaming em tempo real no FastAPI",
    "recent_files": [],
    "last_conversation_logs": [],
}


def _payload(**overrides: object) -> HandoverPayload:
    raw = {**_VALID_RAW, **overrides}
    # IDs únicos para evitar colisão de inserts no mesmo run.
    if "id" not in overrides:
        import uuid
        raw["id"] = str(uuid.uuid4())
    return HandoverPayload.model_validate(raw)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "history.db")
    database.migrate()
    yield database
    database.close()


class TestSchema:
    """Migração do banco."""

    def test_versao_correta(self, db: Database) -> None:
        assert db._user_version() == SCHEMA_VERSION

    def test_migrate_idempotente(self, db: Database) -> None:
        # Segunda chamada não deve falhar nem mudar a versão.
        assert db.migrate() == SCHEMA_VERSION
        assert db._user_version() == SCHEMA_VERSION

    def test_migrate_multiplas_versoes(self, tmp_path: Path) -> None:
        """Simula upgrade incremental: v0 → v1."""
        database = Database(tmp_path / "incremental.db")
        assert database._user_version() == 0
        database.migrate()
        assert database._user_version() == SCHEMA_VERSION
        database.close()


class TestSaveAndList:
    """Round-trip de save ↔ list."""

    def test_salva_e_lista(self, db: Database) -> None:
        p = _payload()
        db.save_handover(p)
        handovers = db.list_handovers()
        assert len(handovers) == 1
        assert handovers[0] == p

    def test_ordem_descendente(self, db: Database) -> None:
        p1 = _payload(
            intent_summary="primeiro",
            timestamp="2026-08-11T21:00:00Z",
        )
        p2 = _payload(
            intent_summary="segundo",
            timestamp="2026-08-11T22:00:00Z",
        )
        db.save_handover(p1)
        db.save_handover(p2)
        listed = db.list_handovers()
        # Mais recente primeiro.
        assert listed[0].intent_summary == "segundo"
        assert listed[1].intent_summary == "primeiro"

    def test_empate_timestamp_usa_rowid(self, db: Database) -> None:
        """Timestamps iguais não devem quebrar a ordenação (tiebreak por rowid)."""
        p1 = _payload(intent_summary="empate-1", timestamp="2026-08-11T21:00:00Z")
        p2 = _payload(intent_summary="empate-2", timestamp="2026-08-11T21:00:00Z")
        db.save_handover(p1)
        db.save_handover(p2)
        listed = db.list_handovers()
        assert [h.intent_summary for h in listed] == ["empate-2", "empate-1"]

    def test_limite(self, db: Database) -> None:
        for i in range(5):
            db.save_handover(_payload(intent_summary=f"item-{i}"))
        assert db.count() == 5
        assert len(db.list_handovers(limit=2)) == 2

    def test_limite_zero_erro(self, db: Database) -> None:
        with pytest.raises(DatabaseError, match="positivo"):
            db.list_handovers(limit=0)

    def test_banco_vazio(self, db: Database) -> None:
        assert db.list_handovers() == []
        assert db.count() == 0


class TestGetHandover:
    """Busca por ID."""

    def test_encontrado(self, db: Database) -> None:
        p = _payload()
        db.save_handover(p)
        got = db.get_handover(str(p.id))
        assert got == p

    def test_nao_encontrado(self, db: Database) -> None:
        assert db.get_handover("00000000-0000-0000-0000-000000000000") is None


class TestDatabasePath:
    """Caminho padrão."""

    def test_default_path(self) -> None:
        path = default_db_path()
        assert path.name == "history.db"
        assert ".agent-ctx" in str(path)

    def test_default_path_resolved(self) -> None:
        assert default_db_path().parent == Path.home() / ".agent-ctx"


class TestContextManager:
    """Comportamento do Database como context manager."""

    def test_context_manager(self, tmp_path: Path) -> None:
        with Database(tmp_path / "ctx.db") as db:
            db.migrate()
            p = _payload()
            db.save_handover(p)
            assert db.count() == 1

    def test_close_limpa_conn(self, db: Database) -> None:
        _ = db.conn  # força conexão
        db.close()
        assert db._conn is None

    def test_conn_reconecta(self, db: Database) -> None:
        db.close()
        # Acessar conn depois de close cria nova conexão.
        _ = db.conn
        assert db._conn is not None


class TestPayloadJson:
    """O payload_json armazenado é JSON válido e round-tripa."""

    def test_roundtrip_via_payload_json(self, db: Database) -> None:
        p = _payload(intent_summary="roundtrip JSON")
        db.save_handover(p)
        row = db.conn.execute(
            "SELECT payload_json FROM handovers WHERE id = ?",
            (str(p.id),),
        ).fetchone()
        data = json.loads(row["payload_json"])
        assert data["intent_summary"] == "roundtrip JSON"
        rebuilt = HandoverPayload.model_validate(data)
        assert rebuilt == p
