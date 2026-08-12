"""Testes dos extractors (base, claude_code, cursor, vscode, antigravity, generic)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent_ctx.extractors.antigravity import AntigravityExtractor
from agent_ctx.extractors.claude_code import ClaudeCodeExtractor, encode_project_path
from agent_ctx.extractors.cursor import CursorExtractor
from agent_ctx.extractors.generic import GenericExtractor
from agent_ctx.extractors.state_vscdb import find_workspace_dir, read_cursor_chat
from agent_ctx.extractors.vscode import VSCodeExtractor

# ───────────────────────────── helpers ─────────────────────────────

_PROJECT = r"C:\Projetos\demo"


def _jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")


def _make_user(text: str) -> dict:
    return {"type": "user", "message": {"content": text}}


def _make_assistant(text: str) -> dict:
    blocks = [{"type": "text", "text": text}]
    return {"type": "assistant", "message": {"content": blocks}}


def _make_assistant_blocks(blocks: list[dict]) -> dict:
    return {"type": "assistant", "message": {"content": blocks}}


def _make_system() -> dict:
    return {"type": "system", "message": {"content": "system init"}}


def _create_state_vscdb(
    db_path: Path, prompts: list[str], composer: dict | None = None
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    if prompts:
        prompts_json = json.dumps([{"text": t} for t in prompts])
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)", ("aiService.prompts", prompts_json)
        )
    if composer is not None:
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)",
            ("composer.composerData", json.dumps(composer)),
        )
    conn.commit()
    conn.close()


def _setup_workspace(
    base: Path,
    project_path: str,
    *,
    prompts: list[str] | None = None,
    composer: dict | None = None,
    session_requests: list[dict] | None = None,
) -> Path:
    hash_dir = "abcdef1234567890"
    ws = base / "User" / "workspaceStorage" / hash_dir
    ws.mkdir(parents=True)
    encoded = project_path.replace("\\", "/")
    folder_json = json.dumps({"folder": f"file:///{encoded}"})
    (ws / "workspace.json").write_text(folder_json, encoding="utf-8")
    if prompts is not None:
        _create_state_vscdb(ws / "state.vscdb", prompts, composer)
    if session_requests is not None:
        chat_dir = ws / "chatSessions"
        chat_dir.mkdir(parents=True)
        session_json = json.dumps({"requests": session_requests})
        (chat_dir / "session.json").write_text(session_json, encoding="utf-8")
    return ws


# ────────────────────── encode_project_path ───────────────────────

class TestEncodeProjectPath:
    def test_windows_path(self) -> None:
        assert encode_project_path(r"C:\Proj\demo") == "C--Proj-demo"

    def test_unix_path(self) -> None:
        assert encode_project_path("/home/user/proj.py") == "-home-user-proj-py"

    def test_colon(self) -> None:
        assert encode_project_path("C:") == "C-"


# ──────────────────── ClaudeCodeExtractor ─────────────────────────

_ENCODED = encode_project_path(_PROJECT)  # "C--Projetos-demo"


class TestClaudeCodeExtractor:
    def test_extrai_mensagens(self, tmp_path: Path) -> None:
        entries = [_make_user("Oi"), _make_assistant("Olá!")]
        _jsonl(tmp_path / _ENCODED / "s.jsonl", entries)
        ext = ClaudeCodeExtractor(projects_dir=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert len(ctx.conversation_logs) == 2
        assert ctx.conversation_logs[0].role == "user"
        assert ctx.conversation_logs[0].content == "Oi"
        assert ctx.conversation_logs[1].role == "assistant"
        assert ctx.conversation_logs[1].content == "Olá!"

    def test_limpa_ruido(self, tmp_path: Path) -> None:
        _jsonl(tmp_path / _ENCODED / "s.jsonl", [
            _make_user("<command-name>/help</command-name>"),
            _make_user("texto real"),
        ])
        ext = ClaudeCodeExtractor(projects_dir=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert len(ctx.conversation_logs) == 1
        assert ctx.conversation_logs[0].content == "texto real"

    def test_limite_20(self, tmp_path: Path) -> None:
        entries = [_make_user(f"msg{i}") for i in range(30)]
        _jsonl(tmp_path / _ENCODED / "s.jsonl", entries)
        ext = ClaudeCodeExtractor(projects_dir=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert len(ctx.conversation_logs) == 20

    def test_projeto_inexistente(self, tmp_path: Path) -> None:
        ext = ClaudeCodeExtractor(projects_dir=tmp_path / "empty")
        ctx = ext.extract("/nao/existe")
        assert "Handover" in ctx.intent_summary
        assert ctx.conversation_logs == []

    def test_summary_primeiro_usuario(self, tmp_path: Path) -> None:
        entries = [
            _make_system(),
            _make_user("Primeira pergunta"),
            _make_assistant("Resposta"),
        ]
        _jsonl(tmp_path / _ENCODED / "s.jsonl", entries)
        ext = ClaudeCodeExtractor(projects_dir=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert ctx.intent_summary == "Primeira pergunta"


# ────────────────────────── state_vscdb ───────────────────────────

class TestStateVscdb:
    def test_find_workspace_dir(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _PROJECT)
        result = find_workspace_dir(tmp_path, _PROJECT)
        assert result is not None
        assert result.is_dir()

    def test_find_workspace_dir_nao_encontrado(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _PROJECT)
        assert find_workspace_dir(tmp_path, _PROJECT + "x") is None

    def test_read_cursor_chat(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        composer = {"allComposers": [{"subtitle": "Meu projeto", "name": "Proj"}]}
        _create_state_vscdb(db, ["prompt1", "prompt2"], composer)
        chat = read_cursor_chat(db)
        assert chat.user_prompts == ["prompt1", "prompt2"]
        assert chat.summary == "Meu projeto"


# ──────────────────────── CursorExtractor ─────────────────────────

class TestCursorExtractor:
    def test_extrai_do_workspace(self, tmp_path: Path) -> None:
        composer = {"allComposers": [{"subtitle": "Resumo do cursor"}]}
        _setup_workspace(
            tmp_path, _PROJECT, prompts=["Pergunta A", "Pergunta B"], composer=composer
        )
        ext = CursorExtractor(root=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert ctx.intent_summary == "Resumo do cursor"
        assert len(ctx.conversation_logs) == 2
        assert ctx.conversation_logs[0].content == "Pergunta A"

    def test_workspace_nao_encontrado(self, tmp_path: Path) -> None:
        ext = CursorExtractor(root=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert "Handover" in ctx.intent_summary
        assert ctx.conversation_logs == []


# ──────────────────────── VSCodeExtractor ─────────────────────────

class TestVSCodeExtractor:
    def test_extrai_prompts_das_sessoes(self, tmp_path: Path) -> None:
        reqs = [
            {"message": {"parts": [{"text": "Como usar pytest?"}]}},
            {"message": {"parts": [{"text": "Gere fixtures"}]}},
        ]
        _setup_workspace(tmp_path, _PROJECT, session_requests=reqs)
        ext = VSCodeExtractor(root=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert len(ctx.conversation_logs) == 2
        assert ctx.conversation_logs[0].content == "Como usar pytest?"
        assert ctx.intent_summary == "Como usar pytest?"

    def test_workspace_nao_encontrado(self, tmp_path: Path) -> None:
        ext = VSCodeExtractor(root=tmp_path)
        ctx = ext.extract(_PROJECT)
        assert "Handover" in ctx.intent_summary


# ──────────────────── Antigravity / Generic ───────────────────────

class TestAntigravity:
    def test_contexto_vazio(self) -> None:
        ctx = AntigravityExtractor().extract("/proj")
        assert "Handover" in ctx.intent_summary
        assert ctx.conversation_logs == []


class TestGeneric:
    def test_contexto_vazio(self) -> None:
        ctx = GenericExtractor().extract("/proj")
        assert "Handover" in ctx.intent_summary
        assert ctx.conversation_logs == []
