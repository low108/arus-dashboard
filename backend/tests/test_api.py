import io
import uuid
import pikepdf
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import delete
from app.main import app
from app.models.db import SessionLocal, StatementRecord
from app.providers.openrouter import MockModelClient


def encrypted_pdf_bytes(tmp_path, password: str) -> bytes:
    plain = tmp_path / f"{uuid.uuid4().hex}.pdf"
    encrypted = tmp_path / f"{uuid.uuid4().hex}.encrypted.pdf"
    document = canvas.Canvas(str(plain)); document.drawString(72, 720, f"Synthetic statement {uuid.uuid4().hex}"); document.save()
    with pikepdf.open(plain) as source: source.save(encrypted, encryption=pikepdf.Encryption(owner=password, user=password, R=6))
    return encrypted.read_bytes()


def test_integration_status_is_honest(monkeypatch):
    monkeypatch.setattr("app.api.routes.connected_account", lambda: None)
    with TestClient(app) as client:
        data = client.get("/api/integrations/status").json()
    assert data["gmail"]["connected"] is False
    assert data["gmail"]["status"] == "Setup required"
    assert data["gmail"]["mode"] == "real"
    assert data["openrouter"]["verified"] is False
    assert data["google_sheets"]["implemented"] is False


def test_manual_import_wrong_password_then_success_and_dedup(monkeypatch, tmp_path, valid_extraction):
    secret = "synthetic-test-only"
    content = encrypted_pdf_bytes(tmp_path, secret)
    monkeypatch.setattr("app.api.routes.OpenRouterClient", lambda: MockModelClient(valid_extraction))
    try:
        with TestClient(app) as client:
            wrong = client.post("/api/statements/import", data={"user_id": "test", "bank_layout": "synthetic", "pdf_password": "incorrect"}, files={"pdf": ("synthetic.pdf", content, "application/pdf")})
            assert wrong.status_code == 200 and wrong.json()["state"] == "needs_password"
            correct = client.post("/api/statements/import", data={"user_id": "test", "bank_layout": "synthetic", "pdf_password": secret}, files={"pdf": ("synthetic.pdf", content, "application/pdf")})
            assert correct.status_code == 200 and correct.json()["state"] == "imported"
            repeat = client.post("/api/statements/import", data={"user_id": "test", "bank_layout": "synthetic", "pdf_password": secret}, files={"pdf": ("synthetic.pdf", content, "application/pdf")})
            assert repeat.json()["duplicate"] is True
            assert client.get("/api/overview").json()["verified_statement_count"] >= 1
            assert client.get("/api/export/transactions.csv").text.startswith("date,")
    finally:
        with SessionLocal() as db:
            db.execute(delete(StatementRecord).where(StatementRecord.user_id == "test"))
            db.commit()
