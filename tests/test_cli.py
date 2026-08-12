"""Testes da CLI (Typer) — smoke tests da Fase 1."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agent_ctx.cli import app

runner = CliRunner()


class TestVersion:
    def test_mostra_versao(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "agent-ctx" in result.stdout


class TestInit:
    def test_init_cria_banco(self, tmp_path: Path) -> None:
        db = tmp_path / "novo.db"
        result = runner.invoke(app, ["init", "--db", str(db)])
        assert result.exit_code == 0
        assert db.exists()
        assert "inicializado" in result.stdout

    def test_init_cria_pasta_automaticamente(self, tmp_path: Path) -> None:
        db = tmp_path / "sub" / "pasta" / "history.db"
        result = runner.invoke(app, ["init", "--db", str(db)])
        assert result.exit_code == 0
        assert db.exists()


class TestAdd:
    def _valid_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "handover.json"
        p.write_text(
            """{
                "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
                "timestamp": "2026-08-11T21:00:00Z",
                "source_agent": "claude-code",
                "target_agent": "cursor",
                "project_path": "/home/user/projects/agripampa",
                "intent_summary": "Teste de streaming"
            }""",
            encoding="utf-8",
        )
        return p

    def test_add_arquivo_valido(self, tmp_path: Path) -> None:
        hf = self._valid_file(tmp_path)
        db_path = tmp_path / "h.db"
        result = runner.invoke(
            app, ["add", "--file", str(hf), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "salvo" in result.stdout

    def test_add_arquivo_inexistente(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        result = runner.invoke(
            app, ["add", "--file", str(tmp_path / "nope.json"), "--db", str(db_path)],
        )
        assert result.exit_code != 0

    def test_add_json_invalido(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{{not json", encoding="utf-8")
        db_path = tmp_path / "h.db"
        result = runner.invoke(
            app, ["add", "--file", str(bad), "--db", str(db_path)],
        )
        assert result.exit_code != 0

    def test_add_payload_invalido(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"source_agent": 42}', encoding="utf-8")
        db_path = tmp_path / "h.db"
        result = runner.invoke(
            app, ["add", "--file", str(bad), "--db", str(db_path)],
        )
        assert result.exit_code != 0


class TestList:
    def test_list_banco_vazio(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        runner.invoke(app, ["init", "--db", str(db_path)])
        result = runner.invoke(app, ["list", "--db", str(db_path)])
        assert result.exit_code == 0
        assert result.stdout.strip() == ""

    def test_list_apos_add(self, tmp_path: Path) -> None:
        db_path = tmp_path / "h.db"
        hf = tmp_path / "p.json"
        hf.write_text(
            """{
                "id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
                "timestamp": "2026-08-11T21:00:00Z",
                "source_agent": "claude-code",
                "target_agent": "cursor",
                "project_path": "/home/user/projects/test",
                "intent_summary": "Teste list"
            }""",
            encoding="utf-8",
        )
        runner.invoke(app, ["init", "--db", str(db_path)])
        runner.invoke(app, ["add", "--file", str(hf), "--db", str(db_path)])
        result = runner.invoke(app, ["list", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "claude-code" in result.stdout


class TestNoArgs:
    def test_no_args_mostra_ajuda(self) -> None:
        result = runner.invoke(app, [])
        # Typer/Click exibe o help com exit 0 ou 2; o que importa é o help.
        assert result.exit_code in (0, 2)
        assert "agent-ctx" in result.stdout.lower()
