from __future__ import annotations

from datetime import UTC, datetime
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
from pathlib import Path

from agent_ctx.core.database import Database, default_db_path

app = FastAPI(title="AgentContext Hub Dashboard")
app.mount("/static", StaticFiles(directory="src/agent_ctx/ui/static"), name="static")
templates = Jinja2Templates(directory="src/agent_ctx/ui/templates")


def _to_local(value: datetime) -> datetime:
    """Converte UTC datetime para o timezone local do sistema."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone()


def _format_dt(value: datetime, fmt: str) -> str:
    """Formata datetime com strftime (Jinja2 não tem nativo)."""
    if value is None:
        return ""
    return value.strftime(fmt)


templates.env.filters["to_local"] = _to_local
templates.env.filters["strftime"] = _format_dt
db_path = os.environ.get("AGENT_CTX_DB")
db = Database(Path(db_path) if db_path else default_db_path())


@app.on_event("startup")
async def startup_event() -> None:
    db.migrate()


@app.get("/api/handovers")
async def get_handovers() -> list[dict[str, object]]:
    return [handover.model_dump(mode="json") for handover in db.list_handovers(limit=50)]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    handovers = db.list_handovers(limit=50)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "handovers": handovers,
            "total_handovers": db.count(),
        },
    )


@app.get("/handover/{handover_id}", response_class=HTMLResponse)
async def handover_detail(request: Request, handover_id: str) -> HTMLResponse:
    handover = db.get_handover(handover_id)
    if handover is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("detail.html", {"request": request, "handover": handover})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
