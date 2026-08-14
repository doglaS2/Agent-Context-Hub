from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_ctx.core.database import Database
from agent_ctx.core.schema import HandoverPayload
from agent_ctx.ui.server import create_app


@pytest.fixture
def test_db(tmp_path: Path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.migrate()
    yield db_path
    db.close()

def test_ui_timeline(test_db):
    # Insere handover via Database
    db = Database(test_db)
    db.save_handover(HandoverPayload(source_agent='claude-code', target_agent='cursor', project_path='C:/p', intent_summary='teste'))
    db.close()

    app = create_app(test_db)
    client = TestClient(app)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "claude-code" in resp.text
    assert "cursor" in resp.text
    assert "teste" in resp.text

def test_ui_xss_protection(test_db):
    db = Database(test_db)
    db.save_handover(HandoverPayload(source_agent='claude-code', target_agent='cursor', project_path='C:/p', intent_summary='<script>alert(1)</script>'))
    db.close()

    app = create_app(test_db)
    client = TestClient(app)

    resp = client.get("/")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text
    assert "<script>" not in resp.text

def test_tailwind_exists(test_db):
    app = create_app(test_db)
    client = TestClient(app)
    resp = client.get("/static/tailwind.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]
