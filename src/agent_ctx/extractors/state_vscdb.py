"""Leitor compartilhado do estado local do Cursor/VS Code.

Ambos os editores armazenam, por workspace, um diretório
``User/workspaceStorage/<hash>/`` com um ``workspace.json`` (que mapeia o hash
para a pasta do projeto) e um banco ``state.vscdb`` com tabela ``ItemTable``.
Este módulo concentra a localização do workspace e a leitura das chaves de
chat do Cursor; o VS Code guarda as sessões em ``chatSessions/*.json``.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

_PROMPTS_KEY = "aiService.prompts"
_COMPOSER_KEY = "composer.composerData"


@dataclass(frozen=True)
class ChatData:
    """Chat extraído do Cursor (state.vscdb)."""

    user_prompts: list[str]
    summary: str | None = None


def find_workspace_dir(base_dir: Path, project_path: str) -> Path | None:
    """Localiza o workspaceStorage cujo workspace.json aponta para project_path."""
    storage = base_dir / "User" / "workspaceStorage"
    if not storage.is_dir():
        return None
    target = Path(project_path).resolve()
    for child in storage.iterdir():
        if not child.is_dir():
            continue
        folder = _folder_from_workspace_json(child / "workspace.json")
        if folder is not None and folder == target:
            return child
    return None


def _folder_from_workspace_json(path: Path) -> Path | None:
    """Extrai a pasta do projeto de um workspace.json (URI file://)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    uri = data.get("folder") if isinstance(data, dict) else None
    if not isinstance(uri, str) or not uri.startswith("file://"):
        return None
    raw = urllib.parse.unquote(uri[len("file://"):]).lstrip("/")
    if not raw:
        return None
    try:
        return Path(raw).resolve()
    except OSError:
        return None


def read_cursor_chat(db_path: Path, max_prompts: int = 20) -> ChatData:
    """Lê prompts e resumo de um state.vscdb do Cursor."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        prompts_raw = _get_key(conn, _PROMPTS_KEY)
        composer_raw = _get_key(conn, _COMPOSER_KEY)
    finally:
        conn.close()
    prompts = _parse_prompts(prompts_raw)
    return ChatData(
        user_prompts=prompts[-max_prompts:],
        summary=_parse_composer_summary(composer_raw),
    )


def _get_key(conn: sqlite3.Connection, key: str) -> str | None:
    try:
        row = conn.execute(
            "SELECT value FROM ItemTable WHERE key = ?", (key,)
        ).fetchone()
    except sqlite3.DatabaseError:
        return None
    if row is None:
        return None
    value = row[0]
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _parse_prompts(raw: str | None) -> list[str]:
    if raw is None:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    prompts: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            prompts.append(text.strip())
    return prompts


def _parse_composer_summary(raw: str | None) -> str | None:
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    composers = data.get("allComposers") if isinstance(data, dict) else None
    if not isinstance(composers, list) or not composers:
        return None
    first = composers[0]
    if not isinstance(first, dict):
        return None
    for field in ("subtitle", "name"):
        value = first.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
