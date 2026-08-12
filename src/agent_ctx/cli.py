"""CLI do AgentContext Hub (Typer).

Comandos da Fase 1: ``version``, ``init``, ``add`` e ``list``.
Fase 2: ``extract``. Fase 3: ``inject`` e ``resume``.
Fase 4: ``ui``.
"""

from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from agent_ctx.core.database import Database, default_db_path
from agent_ctx.core.scanner import Scanner
from agent_ctx.core.schema import HandoverPayload

_VALID_AGENTS = ("claude-code", "cursor", "vscode", "antigravity", "generic")

app = typer.Typer(
    name="agent-ctx",
    help=(
        "AgentContext Hub - State Handover local-first "
        "entre agentes de IA."
    ),
    no_args_is_help=True,
)

_DbOption = Annotated[
    Path | None,
    typer.Option("--db", help="Caminho do banco SQLite local."),
]


def _resolve_db(db: Path | None) -> Path:
    return db if db is not None else default_db_path()


@app.command("version")
def show_version() -> None:
    """Mostra a versão instalada do AgentContext Hub."""
    try:
        current = metadata.version("agent-ctx")
    except metadata.PackageNotFoundError:
        current = "0.1.0"
    typer.echo(f"agent-ctx {current}")


@app.command()
def init(db: _DbOption = None) -> None:
    """Inicializa o banco SQLite local (~/.agent-ctx/history.db)."""
    db_path = _resolve_db(db)
    with Database(db_path) as database:
        database.migrate()
    typer.echo(f"banco inicializado em {db_path}")


@app.command("add")
def handover_add(
    file: Annotated[Path, typer.Option("--file", "-f",
                                       help="Arquivo JSON do payload.")],
    db: _DbOption = None,
) -> None:
    """Valida um HandoverPayload (Schema Universal) de um JSON e o salva."""
    db_path = _resolve_db(db)
    payload = _load_payload(file)
    with Database(db_path) as database:
        database.migrate()
        database.save_handover(payload)
    typer.echo(f"handover {payload.id} salvo em {db_path}")


@app.command("list")
def list_handovers(
    limit: Annotated[int,
                     typer.Option("--limit", "-n",
                                  help="Número de itens.")] = 20,
    db: _DbOption = None,
) -> None:
    """Lista os handovers recentes do banco local."""
    db_path = _resolve_db(db)
    with Database(db_path) as database:
        database.migrate()
        handovers = database.list_handovers(limit=limit)
    for handover in handovers:
        line = (
            f"{handover.timestamp.isoformat()}  "
            f"{handover.source_agent} -> {handover.target_agent}  "
            f"{handover.id}"
        )
        typer.echo(line)


def _load_payload(path: Path) -> HandoverPayload:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"arquivo não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"JSON inválido em {path}: {exc}") from exc
    try:
        return HandoverPayload.model_validate(raw)
    except ValidationError as exc:
        raise typer.BadParameter(f"payload inválido: {exc.errors()}") from exc


# ──────────────────────── Fase 2: extract ──────────────────────────

@app.command("extract")
def extract_context(
    source: Annotated[str, typer.Option("--source", help="Agente de origem.")],
    target: Annotated[str, typer.Option("--target", help="Agente de destino.")],
    project: Annotated[Path, typer.Option("--project", help="Caminho do projeto.")],
    minutes: Annotated[
        int, typer.Option("--minutes", help="Janela de mtime (minutos).")
    ] = 15,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Mostra resultado sem persistir.")
    ] = False,
    db: _DbOption = None,
) -> None:
    """Lê o estado local de um agente e gera um handover."""
    if source not in _VALID_AGENTS:
        raise typer.BadParameter(
            f"fonte inválida: {source}. Opções: {', '.join(_VALID_AGENTS)}"
        )
    if target not in _VALID_AGENTS:
        raise typer.BadParameter(
            f"destino inválido: {target}. Opções: {', '.join(_VALID_AGENTS)}"
        )
    if not project.is_dir():
        raise typer.BadParameter(f"caminho do projeto não é diretório: {project}")
    if minutes < 1:
        raise typer.BadParameter("minutes deve ser >= 1")

    from agent_ctx.extractors.antigravity import AntigravityExtractor
    from agent_ctx.extractors.claude_code import ClaudeCodeExtractor
    from agent_ctx.extractors.cursor import CursorExtractor
    from agent_ctx.extractors.generic import GenericExtractor
    from agent_ctx.extractors.vscode import VSCodeExtractor

    _EXTRACTORS = {
        "claude-code": ClaudeCodeExtractor,
        "cursor": CursorExtractor,
        "vscode": VSCodeExtractor,
        "antigravity": AntigravityExtractor,
        "generic": GenericExtractor,
    }

    extractor = _EXTRACTORS[source]()
    context = extractor.extract(str(project))
    recent = Scanner(minutes=minutes).recent_files(project)

    payload = HandoverPayload(
        source_agent=source,
        target_agent=target,
        project_path=str(project.resolve()),
        intent_summary=context.intent_summary,
        recent_files=recent,
        last_conversation_logs=context.conversation_logs,
    )

    if dry_run:
        typer.echo(f"[dry-run] intent: {payload.intent_summary}")
        typer.echo(f"[dry-run] recent_files: {len(payload.recent_files)}")
        logs = len(payload.last_conversation_logs)
        typer.echo(f"[dry-run] conversation_logs: {logs}")
        return

    db_path = _resolve_db(db)
    with Database(db_path) as database:
        database.migrate()
        database.save_handover(payload)
    typer.echo(f"handover {payload.id} salvo em {db_path}")


# ──────────────────────── Fase 3: inject ──────────────────────────

@app.command("inject")
def inject_context(
    id: Annotated[str, typer.Option("--id", help="ID do handover no banco.")],
    project: Annotated[Path, typer.Option("--project",
                                          help="Caminho do projeto destino.")],
    db: _DbOption = None,
) -> None:
    """Carrega um HandoverPayload do banco e injeta no projeto destino."""
    if not project.is_dir():
        raise typer.BadParameter(f"caminho do projeto não é diretório: {project}")

    db_path = _resolve_db(db)
    with Database(db_path) as database:
        database.migrate()
        payload = database.get_handover(id)
    if payload is None:
        raise typer.BadParameter(f"handover não encontrado: {id}")

    from agent_ctx.injectors import _resolve_injector

    injector = _resolve_injector(payload.target_agent)
    result = injector.inject(str(project), payload)
    typer.echo(f"handover {id} injetado em {result.file_path}")


# ──────────────────────── Fase 3: resume ──────────────────────────

@app.command("resume")
def resume_context(
    source: Annotated[str, typer.Option("--source", help="Agente de origem.")],
    target: Annotated[str, typer.Option("--target", help="Agente de destino.")],
    project: Annotated[Path, typer.Option("--project", help="Caminho do projeto.")],
    minutes: Annotated[
        int, typer.Option("--minutes", help="Janela de mtime (minutos).")
    ] = 15,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Mostra resultado sem persistir.")
    ] = False,
    db: _DbOption = None,
) -> None:
    """Extract + Inject + Salva: transfere contexto entre agentes."""
    if source not in _VALID_AGENTS:
        raise typer.BadParameter(
            f"fonte inválida: {source}. Opções: {', '.join(_VALID_AGENTS)}"
        )
    if target not in _VALID_AGENTS:
        raise typer.BadParameter(
            f"destino inválido: {target}. Opções: {', '.join(_VALID_AGENTS)}"
        )
    if not project.is_dir():
        raise typer.BadParameter(f"caminho do projeto não é diretório: {project}")
    if minutes < 1:
        raise typer.BadParameter("minutes deve ser >= 1")

    from agent_ctx.extractors.antigravity import AntigravityExtractor
    from agent_ctx.extractors.claude_code import ClaudeCodeExtractor
    from agent_ctx.extractors.cursor import CursorExtractor
    from agent_ctx.extractors.generic import GenericExtractor
    from agent_ctx.extractors.vscode import VSCodeExtractor
    from agent_ctx.injectors import _resolve_injector

    _EXTRACTORS = {
        "claude-code": ClaudeCodeExtractor,
        "cursor": CursorExtractor,
        "vscode": VSCodeExtractor,
        "antigravity": AntigravityExtractor,
        "generic": GenericExtractor,
    }

    extractor = _EXTRACTORS[source]()
    context = extractor.extract(str(project))
    recent = Scanner(minutes=minutes).recent_files(project)

    payload = HandoverPayload(
        source_agent=source,
        target_agent=target,
        project_path=str(project.resolve()),
        intent_summary=context.intent_summary,
        recent_files=recent,
        last_conversation_logs=context.conversation_logs,
    )

    injector = _resolve_injector(target)
    result = injector.inject(str(project), payload)

    if dry_run:
        typer.echo(f"[dry-run] intent: {payload.intent_summary}")
        typer.echo(f"[dry-run] injectado em: {result.file_path}")
        return

    db_path = _resolve_db(db)
    with Database(db_path) as database:
        database.migrate()
        database.save_handover(payload)
    typer.echo(f"handover {payload.id} salvo em {db_path}")
