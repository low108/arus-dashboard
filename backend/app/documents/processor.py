import hashlib
import shutil
import tempfile
from pathlib import Path
import pdfplumber
import pikepdf


class DocumentError(RuntimeError):
    code = "document_failed"


class PasswordRequired(DocumentError):
    code = "needs_password"


class UnsupportedDocument(DocumentError):
    code = "unsupported"


class PDFProcessor:
    def hash_bytes(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def extract(self, content: bytes, password: str) -> list[tuple[int, str]]:
        if not content.startswith(b"%PDF"):
            raise UnsupportedDocument("The attachment is not a supported PDF.")
        tmp = tempfile.mkdtemp(prefix="arus-")
        try:
            source = Path(tmp) / "source.pdf"
            decrypted = Path(tmp) / "decrypted.pdf"
            source.write_bytes(content)
            try:
                with pikepdf.open(source, password=password) as pdf:
                    pdf.save(decrypted)
            except pikepdf.PasswordError as exc:
                raise PasswordRequired("The PDF password was not accepted.") from exc
            except pikepdf.PdfError as exc:
                raise UnsupportedDocument("The PDF could not be parsed.") from exc
            pages: list[tuple[int, str]] = []
            with pdfplumber.open(decrypted) as pdf:
                for index, page in enumerate(pdf.pages, 1):
                    pages.append((index, page.extract_text() or ""))
            return pages
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
