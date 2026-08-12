"""Extractors — leitores de estado das fontes locais (Fase 2).

Módulos:
- ``base``: ``ExtractedContext``, ``Extractor`` (Protocol)
- ``claude_code``: transcripts JSONL do ``~/.claude/projects/``
- ``cursor``: ``state.vscdb`` do Cursor
- ``vscode``: sessões de chat do VS Code (Copilot Chat)
- ``antigravity``: best-effort, sem histórico estruturado
- ``generic``: fallback do schema (``generic``)
"""
