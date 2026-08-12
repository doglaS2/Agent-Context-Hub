"""Testes do comando ``agent-ctx extract``."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_ctx.core.database import Database


def _run(args: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from agent_ctx.cli import app
    runner = CliRunner()
    result = runner.invoke(app, args)
    if result.exit_code != 0:
        detail = f"{result.output}\n{result.exception}"
        raise AssertionError(f"CLI falhou ({result.exit_code}): {detail}")
    return result.output


class TestExtractDryRun:
    def test_dry_run(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        output = _run([
            "extract", "--source", "claude-code", "--target", "cursor",
            "--project", str(tmp_path),
            "--db", str(db_path),
            "--dry-run",
        ], None)
        assert "[dry-run]" in output
        assert "intent:" in output
        # Não persistiu: banco não existe.
        assert not db_path.exists()


class TestExtractSave:
    def test_save(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        output = _run([
            "extract", "--source", "claude-code", "--target", "cursor",
            "--project", str(tmp_path),
            "--db", str(db_path),
        ], None)
        assert "salvo" in output
        assert db_path.exists()
        with Database(db_path) as db:
            assert db.count() == 1


class TestExtractValidations:
    def test_fonte_invalida(self, tmp_path: Path) -> None:
        with pytest.raises(AssertionError, match="inválid"):
            _run([
                "extract", "--source", "alice-ai", "--target", "cursor",
                "--project", str(tmp_path), "--db", str(tmp_path / "h.db"),
            ], None)

    def test_projeto_nao_e_diretorio(self, tmp_path: Path) -> None:
        p = tmp_path / "file.txt"
        p.write_text("x")
        with pytest.raises(AssertionError, match="não é diretório"):
            _run([
                "extract", "--source", "claude-code", "--target", "cursor",
                "--project", str(p), "--db", str(tmp_path / "h.db"),
            ], None)

    def test_minutes_zero(self, tmp_path: Path) -> None:
        with pytest.raises(AssertionError, match=">= 1"):
            _run([
                "extract", "--source", "claude-code", "--target", "cursor",
                "--project", str(tmp_path),
                "--minutes", "0", "--db", str(tmp_path / "h.db"),
            ], None)
