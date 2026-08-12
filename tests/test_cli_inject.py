"""Testes dos comandos ``agent-ctx inject`` e ``agent-ctx resume``."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_ctx.core.database import Database
from agent_ctx.core.schema import HandoverPayload

_VALID = ("claude-code", "cursor")


def _run(args: list[str]) -> str | None:
    from typer.testing import CliRunner

    from agent_ctx.cli import app

    runner = CliRunner()
    result = runner.invoke(app, args)
    if result.exit_code != 0:
        raise AssertionError(
            f"CLI falhou ({result.exit_code}): {result.output}\n"
            f"{result.exception}"
        )
    return result.output


def _save_payload(db_path: Path) -> str:
    """Salva um handover de teste no DB e retorna o ID."""
    payload = HandoverPayload(
        source_agent="claude-code",
        target_agent="cursor",
        project_path="/tmp/test-proj",
        intent_summary="Teste inject",
    )
    with Database(db_path) as db:
        db.migrate()
        db.save_handover(payload)
    return str(payload.id)


class TestInject:
    def test_inject_ok(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        hid = _save_payload(db_path)
        output = _run([
            "inject", "--id", hid, "--project", str(tmp_path),
            "--db", str(db_path),
        ])
        assert "injetado" in output
        assert (tmp_path / ".agent-ctx" / "handover.json").exists()

    def test_inject_id_inexistente(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        with Database(db_path) as db:
            db.migrate()
        with pytest.raises(AssertionError, match="não encontrado"):
            _run([
                "inject", "--id", "00000000-0000-0000-0000-000000000000",
                "--project", str(tmp_path), "--db", str(db_path),
            ])


class TestResume:
    def test_resume_dry_run(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        output = _run([
            "resume", "--source", "claude-code", "--target", "cursor",
            "--project", str(tmp_path), "--db", str(db_path),
            "--dry-run",
        ])
        assert "[dry-run]" in output
        assert not db_path.exists()

    def test_resume_save(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        output = _run([
            "resume", "--source", "claude-code", "--target", "cursor",
            "--project", str(tmp_path), "--db", str(db_path),
        ])
        assert "salvo" in output
        assert db_path.exists()
        with Database(db_path) as db:
            assert db.count() == 1
        assert (tmp_path / ".agent-ctx" / "handover.json").exists()
