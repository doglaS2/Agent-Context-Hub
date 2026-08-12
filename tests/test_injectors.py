"""Testes dos injectors (base, project, claude_code) e do resolver."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from agent_ctx.core.schema import ConversationLog, HandoverPayload, RecentFile
from agent_ctx.injectors import _resolve_injector
from agent_ctx.injectors.claude_code import ClaudeCodeInjector
from agent_ctx.injectors.project import ProjectInjector, read_handover

# ───────────────────────────── helpers ─────────────────────────────

_PAYLOAD = HandoverPayload(
    source_agent="claude-code",
    target_agent="cursor",
    project_path="/projeto/demo",
    intent_summary="Corrigir bug no login",
)


def _payload_full() -> HandoverPayload:
    return HandoverPayload(
        source_agent="claude-code",
        target_agent="cursor",
        project_path="/projeto/demo",
        intent_summary="Refatorar modulo de auth",
        recent_files=[
            RecentFile(path="/projeto/demo/auth.py", mtime=datetime.now(UTC)),
        ],
        last_conversation_logs=[
            ConversationLog(role="user", content="Refatore o auth.py"),
            ConversationLog(role="assistant", content="Vou refatorar."),
        ],
    )


# ──────────────── ProjectInjector ─────────────────────────────────


class TestProjectInjector:
    def test_cria_handover_json(self, tmp_path: Path) -> None:
        ProjectInjector().inject(str(tmp_path), _PAYLOAD)
        target = tmp_path / ".agent-ctx" / "handover.json"
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["source_agent"] == "claude-code"
        assert data["intent_summary"] == "Corrigir bug no login"

    def test_sobrescreve(self, tmp_path: Path) -> None:
        inj = ProjectInjector()
        inj.inject(str(tmp_path), _PAYLOAD)
        inj.inject(str(tmp_path), _PAYLOAD)
        assert (tmp_path / ".agent-ctx" / "handover.json").exists()

    def test_le_de_volta(self, tmp_path: Path) -> None:
        ProjectInjector().inject(str(tmp_path), _PAYLOAD)
        loaded = read_handover(str(tmp_path))
        assert loaded is not None
        assert loaded.intent_summary == _PAYLOAD.intent_summary
        assert loaded.id == _PAYLOAD.id

    def test_leitura_sem_handover(self, tmp_path: Path) -> None:
        assert read_handover(str(tmp_path)) is None


# ──────────────── ClaudeCodeInjector ──────────────────────────────


class TestClaudeCodeInjector:
    def test_cria_agent_context_md(self, tmp_path: Path) -> None:
        ClaudeCodeInjector().inject(str(tmp_path), _PAYLOAD)
        target = tmp_path / ".claude" / "agent-context.md"
        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert "Corrigir bug no login" in content

    def test_conteudo_completo(self, tmp_path: Path) -> None:
        payload = _payload_full()
        ClaudeCodeInjector().inject(str(tmp_path), payload)
        content = (
            tmp_path / ".claude" / "agent-context.md"
        ).read_text(encoding="utf-8")
        assert "Refatorar modulo de auth" in content
        assert "auth.py" in content
        assert "Refatore o auth.py" in content


# ──────────────── _resolve_injector ───────────────────────────────


class TestResolveInjector:
    def test_claude_code(self) -> None:
        assert isinstance(_resolve_injector("claude-code"), ClaudeCodeInjector)

    def test_cursor(self) -> None:
        assert isinstance(_resolve_injector("cursor"), ProjectInjector)

    def test_vscode(self) -> None:
        assert isinstance(_resolve_injector("vscode"), ProjectInjector)

    def test_antigravity(self) -> None:
        assert isinstance(_resolve_injector("antigravity"), ProjectInjector)

    def test_generic(self) -> None:
        assert isinstance(_resolve_injector("generic"), ProjectInjector)
