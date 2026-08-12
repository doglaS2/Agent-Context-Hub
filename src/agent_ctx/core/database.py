"""Gerenciamento do banco SQLite local (~/.agent-ctx/history.db).

Camada fina sobre ``sqlite3`` (stdlib) com migrations leves via
``PRAGMA user_version``. A tabela ``handovers`` guarda o payload JSON
Universal (Schema Universal) mais colunas indexadas para consulta rápida.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from agent_ctx.core.schema import HandoverPayload

# Versão do schema SQLite. Incremente e adicione o passo em ``_MIGRATIONS``.
SCHEMA_VERSION = 1

_MIGRATIONS: dict[int, str] = {
    1: """
        CREATE TABLE IF NOT EXISTS handovers (
            id             TEXT PRIMARY KEY,
            timestamp      TEXT NOT NULL,
            source_agent   TEXT NOT NULL,
            target_agent   TEXT NOT NULL,
            project_path   TEXT NOT NULL,
            intent_summary TEXT NOT NULL,
            payload_json   TEXT NOT NULL,
            created_at     TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_handovers_timestamp
            ON handovers (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_handovers_source
            ON handovers (source_agent);
    """,
}

_INSERT_COLUMNS = (
    "id, timestamp, source_agent, target_agent, project_path, "
    "intent_summary, payload_json, created_at"
)


class DatabaseError(RuntimeError):
    """Erro de persistência do AgentContext Hub."""


def default_db_path() -> Path:
    """Caminho padrão do banco local: ``~/.agent-ctx/history.db``."""
    return Path.home() / ".agent-ctx" / "history.db"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


class Database:
    """Conexão SQLite local com migração de schema e operações de handover."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_db_path()
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._connect()
        return self._conn

    def _connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        self._conn = conn

    def migrate(self) -> int:
        """Aplica migrations pendentes e retorna a versão do schema resultante."""
        current = self._user_version()
        for version in range(current + 1, SCHEMA_VERSION + 1):
            sql = _MIGRATIONS.get(version)
            if sql is None:
                raise DatabaseError(f"migration ausente para a versão {version}")
            with self.conn:
                self.conn.executescript(sql)
                # PRAGMA não aceita parâmetros; `version` vem de dict interno.
                self.conn.execute(f"PRAGMA user_version = {version}")
        return SCHEMA_VERSION

    def _user_version(self) -> int:
        row = self.conn.execute("PRAGMA user_version").fetchone()
        return int(row[0])

    def save_handover(self, payload: HandoverPayload) -> None:
        """Persiste um handover validado (Schema Universal)."""
        values = {
            "id": str(payload.id),
            "timestamp": _iso(payload.timestamp),
            "source_agent": payload.source_agent,
            "target_agent": payload.target_agent,
            "project_path": payload.project_path,
            "intent_summary": payload.intent_summary,
            "payload_json": payload.model_dump_json(),
            "created_at": _iso(datetime.now(UTC)),
        }
        placeholders = ", ".join(f":{k}" for k in values)
        with self.conn:
            self.conn.execute(
                f"INSERT INTO handovers ({_INSERT_COLUMNS}) "
                f"VALUES ({placeholders})",
                values,
            )

    def get_handover(self, handover_id: str) -> HandoverPayload | None:
        """Retorna um handover por ID, ou ``None`` se não existir."""
        row = self.conn.execute(
            "SELECT payload_json FROM handovers WHERE id = ?",
            (handover_id,),
        ).fetchone()
        if row is None:
            return None
        return HandoverPayload.model_validate_json(row["payload_json"])

    def list_handovers(self, *, limit: int = 50) -> list[HandoverPayload]:
        """Lista os handovers mais recentes, do mais novo para o mais antigo."""
        if limit <= 0:
            raise DatabaseError("limit deve ser positivo")
        rows = self.conn.execute(
            "SELECT payload_json FROM handovers "
            "ORDER BY timestamp DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [HandoverPayload.model_validate_json(r["payload_json"]) for r in rows]

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM handovers").fetchone()
        return int(row["n"])

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
