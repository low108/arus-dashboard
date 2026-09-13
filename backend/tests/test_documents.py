from pathlib import Path
import pikepdf
import pytest
from reportlab.pdfgen import canvas
from app.documents.processor import PDFProcessor, PasswordRequired, UnsupportedDocument


def encrypted_pdf(tmp_path: Path, password: str = "fixture-password") -> bytes:
    plain = tmp_path / "plain.pdf"
    pdf = canvas.Canvas(str(plain)); pdf.drawString(72, 720, "Synthetic statement balance 100.00"); pdf.save()
    encrypted = tmp_path / "encrypted.pdf"
    with pikepdf.open(plain) as source:
        source.save(encrypted, encryption=pikepdf.Encryption(owner=password, user=password, R=6))
    return encrypted.read_bytes()


def test_correct_pdf_password(tmp_path):
    pages = PDFProcessor().extract(encrypted_pdf(tmp_path), "fixture-password")
    assert "Synthetic statement" in pages[0][1]


def test_incorrect_pdf_password(tmp_path):
    with pytest.raises(PasswordRequired): PDFProcessor().extract(encrypted_pdf(tmp_path), "wrong")


def test_malformed_pdf():
    with pytest.raises(UnsupportedDocument): PDFProcessor().extract(b"not-a-pdf", "x")


def test_temporary_files_cleaned(monkeypatch, tmp_path):
    created = tmp_path / "isolated"
    def tracked_directory(**kwargs):
        created.mkdir()
        return str(created)
    monkeypatch.setattr("app.documents.processor.tempfile.mkdtemp", tracked_directory)
    PDFProcessor().extract(encrypted_pdf(tmp_path), "fixture-password")
    assert not created.exists()
