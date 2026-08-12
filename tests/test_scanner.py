"""Testes do scanner de arquivos recentemente modificados (scanner.py)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_ctx.core.scanner import MAX_FILES, Scanner

_NOW = datetime(2026, 8, 11, 21, 0, 0, tzinfo=UTC)


def _touch(path: Path, minutes_ago: int) -> None:
    """Cria/atualiza o arquivo e fixa o mtime relativo a _NOW."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("conteudo do arquivo\n", encoding="utf-8")
    mtime = (_NOW - timedelta(minutes=minutes_ago)).timestamp()
    os.utime(path, (mtime, mtime))


def _scanner(minutes: int = 15, now: datetime = _NOW) -> Scanner:
    return Scanner(minutes=minutes, now=now)


class TestFiltroDeMtime:
    def test_arquivo_recente_incluido(self, tmp_path: Path) -> None:
        f = tmp_path / "main.py"
        _touch(f, minutes_ago=2)
        result = _scanner().recent_files(tmp_path)
        assert len(result) == 1
        assert result[0].path == str(f)
        assert "conteudo" in (result[0].diff or "")

    def test_arquivo_antigo_excluido(self, tmp_path: Path) -> None:
        _touch(tmp_path / "velho.py", minutes_ago=120)
        result = _scanner().recent_files(tmp_path)
        assert result == []

    def test_arquivo_no_limite_incluido(self, tmp_path: Path) -> None:
        # Exatamente na janela (15 min atrás) ainda entra (mtime >= cutoff).
        _touch(tmp_path / "limite.py", minutes_ago=15)
        result = _scanner().recent_files(tmp_path)
        assert len(result) == 1

    def test_janela_configuravel(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.py", minutes_ago=10)
        # Janela de 5 min exclui o arquivo de 10 min atrás.
        assert _scanner(minutes=5).recent_files(tmp_path) == []
        # Janela de 30 min inclui.
        assert len(_scanner(minutes=30).recent_files(tmp_path)) == 1


class TestDiretoriosIgnorados:
    def test_ignora_pastas_irrelevantes(self, tmp_path: Path) -> None:
        for d in ("node_modules", ".git", ".venv", "venv", "__pycache__"):
            _touch(tmp_path / d / "x.py", minutes_ago=1)
        _touch(tmp_path / "real.py", minutes_ago=1)
        result = _scanner().recent_files(tmp_path)
        assert len(result) == 1
        assert result[0].path.endswith("real.py")

    def test_ignora_aninhadas(self, tmp_path: Path) -> None:
        _touch(tmp_path / "src" / "node_modules" / "deep.py", minutes_ago=1)
        result = _scanner().recent_files(tmp_path)
        assert result == []

    def test_arquivos_na_raiz_nao_ignorada(self, tmp_path: Path) -> None:
        _touch(tmp_path / ".gitignore", minutes_ago=1)
        result = _scanner().recent_files(tmp_path)
        # .gitignore é arquivo (não diretório): deve entrar.
        assert len(result) == 1


class TestLimitesEGuardas:
    def test_max_files_respeitado(self, tmp_path: Path) -> None:
        for i in range(MAX_FILES + 10):
            _touch(tmp_path / f"f{i:03d}.py", minutes_ago=1)
        result = _scanner().recent_files(tmp_path)
        assert len(result) == MAX_FILES

    def test_binario_com_null_byte_excluido(self, tmp_path: Path) -> None:
        p = tmp_path / "bin.dat"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x00\x01\x02\x03binary")
        os.utime(p, (_NOW.timestamp(), _NOW.timestamp()))
        assert _scanner().recent_files(tmp_path) == []

    def test_texto_nao_utf8_excluido(self, tmp_path: Path) -> None:
        p = tmp_path / "latin1.txt"
        p.write_bytes(b"caf\xe9 \xff\xfe")  # não UTF-8 válido
        os.utime(p, (_NOW.timestamp(), _NOW.timestamp()))
        assert _scanner().recent_files(tmp_path) == []

    def test_diff_preview_limitado(self, tmp_path: Path) -> None:
        p = tmp_path / "grande.txt"
        p.write_bytes(b"x" * (50_000 + 100))
        os.utime(p, (_NOW.timestamp(), _NOW.timestamp()))
        (result,) = _scanner().recent_files(tmp_path)
        assert result.diff is not None
        assert len(result.diff) <= 50_000


class TestOrdenacao:
    def test_mais_recente_primeiro(self, tmp_path: Path) -> None:
        _touch(tmp_path / "velho.py", minutes_ago=14)
        _touch(tmp_path / "novo.py", minutes_ago=1)
        result = _scanner().recent_files(tmp_path)
        expected = [str(tmp_path / "novo.py"), str(tmp_path / "velho.py")]
        assert [r.path for r in result] == expected

    def test_projeto_inexistente_retorna_vazio(self, tmp_path: Path) -> None:
        assert _scanner().recent_files(tmp_path / "nao-existe") == []

    def test_campo_mtime_preenchido(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.py", minutes_ago=5)
        (result,) = _scanner().recent_files(tmp_path)
        assert result.mtime is not None
        assert result.mtime.tzinfo is not None
