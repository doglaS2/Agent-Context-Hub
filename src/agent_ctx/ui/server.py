"""Dashboard local-first do AgentContext Hub (Fase 4)."""

from __future__ import annotations

import importlib.resources
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent_ctx.core.database import Database


def create_app(db_path: Path) -> FastAPI:
    """App Factory para o dashboard."""
    app = FastAPI(title="AgentContext Hub Dashboard")

    # Resolucao robusta para WHEEL ou SRC layout
    ui_pkg = importlib.resources.files("agent_ctx.ui")
    templates = Jinja2Templates(directory=ui_pkg / "templates")
    app.mount("/static", StaticFiles(directory=ui_pkg / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request, limit: int = 20):
        # UI e somente-leitura
        with Database(db_path, read_only=True) as db:
            try:
                handovers = db.list_summaries(limit=min(limit, 200))
            except Exception:
                handovers = []
        return templates.TemplateResponse(request, "index.html", {"handovers": handovers})

    @app.get("/handover/{handover_id}", response_class=HTMLResponse)
    async def handover_detail(request: Request, handover_id: str):
        # Validacao basica de UUID evitada na rota por simplicidade,
        # mas DATABASE trata corrupcao do payload_json
        with Database(db_path, read_only=True) as db:
            try:
                handover = db.get_handover(handover_id)
            except Exception:
                handover = None

        if not handover:
            return templates.TemplateResponse(request, "404.html", {"status": 404}, status_code=404)

        return templates.TemplateResponse(request, "detail.html", {"handover": handover})

    return app
