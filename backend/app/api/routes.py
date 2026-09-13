import csv
import io
import time
import uuid
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import select
from app.config import settings
from app.documents.processor import PDFProcessor, PasswordRequired, UnsupportedDocument
from app.gmail.adapters import RealGmailAdapter
from app.gmail.oauth import authorization_url, connected_account, disconnect, exchange_callback, gmail_service, oauth_configured
from app.gmail.sync import sync_attachments
from app.ledger.reconcile import reconcile
from app.models.db import AgentRun, GoalRecord, SessionLocal, StatementRecord
from app.models.schemas import GoalCreate, GoalUpdate, StatementExtraction, StatementState
from app.providers.openrouter import OpenRouterClient, ProviderError

router = APIRouter(prefix="/api")
processor = PDFProcessor()
openrouter_verification: dict[str, object] = {"verified": False, "status": "not_run"}


def add_activity(db, job_id: str, stage: str, provider: str, status: str, started: float, records: int = 0, retries: int = 0, error: str | None = None, model: str | None = None) -> None:
    db.add(AgentRun(job_id=job_id, stage=stage, provider=provider, model=model, status=status, duration_ms=max(0, int((time.perf_counter() - started) * 1000)), record_count=records, retry_count=retries, redacted_error=error))


async def process_record(db, record: StatementRecord, content: bytes, password: str, job_id: str) -> dict:
    pdf_started = time.perf_counter()
    try:
        pages = processor.extract(content, password)
        add_activity(db, job_id, "Local PDF decryption", "pikepdf + pdfplumber (LOCAL)", "completed", pdf_started, len(pages))
        model_started = time.perf_counter()
        model_client = OpenRouterClient()
        extraction = await model_client.extract(pages)
        add_activity(db, job_id, "OpenRouter extraction", "OpenRouter (REAL)", "completed", model_started, len(extraction.transactions), model=settings.openrouter_model)
        category_started = time.perf_counter()
        categorized = await model_client.categorize(extraction.transactions)
        add_activity(db, job_id, "Transaction categorization", "OpenRouter (REAL)", "completed", category_started, categorized, model=settings.openrouter_model)
        ledger_started = time.perf_counter()
        validation = reconcile(extraction)
        add_activity(db, job_id, "Ledger Guard validation", "Deterministic code", "completed" if validation.valid else "needs_review", ledger_started, len(extraction.transactions), error=None if validation.valid else "ReconciliationMismatch")
        record.model_extraction = extraction.model_dump(mode="json")
        record.accepted_records = extraction.model_dump(mode="json") if validation.valid else None
        record.state = StatementState.IMPORTED if validation.valid else StatementState.NEEDS_REVIEW
        record.safe_error = None if validation.valid else "; ".join(validation.errors)
        db.commit()
        return {"statement_id": record.id, "state": record.state, "validation": validation}
    except PasswordRequired as exc:
        record.state = StatementState.NEEDS_PASSWORD; record.safe_error = str(exc)
        add_activity(db, job_id, "Local PDF decryption", "pikepdf (LOCAL)", "needs_password", pdf_started, error="PasswordRequired")
        db.commit()
        return {"statement_id": record.id, "state": record.state}
    except UnsupportedDocument as exc:
        record.state = StatementState.UNSUPPORTED; record.safe_error = str(exc)
        add_activity(db, job_id, "Local PDF decryption", "pikepdf (LOCAL)", "unsupported", pdf_started, error="UnsupportedDocument")
        db.commit()
        raise
    except ProviderError as exc:
        record.state = StatementState.NEEDS_REVIEW; record.safe_error = str(exc)
        add_activity(db, job_id, "OpenRouter extraction", "OpenRouter (REAL)", "error", time.perf_counter(), error=type(exc).__name__, model=settings.openrouter_model)
        db.commit()
        raise


@router.get("/integrations/status")
async def integration_status():
    account = connected_account()
    gmail_connected = account is not None
    openrouter_configured = bool(settings.openrouter_api_key and settings.openrouter_model and settings.openrouter_base_url)
    return {
        "gmail": {"implemented": True, "connected": gmail_connected, "mode": "real", "account": account, "status": "Connected — real" if gmail_connected else "Setup required"},
        "openrouter": {"implemented": True, "configured": openrouter_configured, "verified": bool(openrouter_verification["verified"]), "mode": "real", "model": settings.openrouter_model, "status": "Connected — real" if openrouter_verification["verified"] else "Configured but unverified" if openrouter_configured else "Not configured"},
        "pdf": {"implemented": True, "encrypted_pdf_supported": True, "status": "Connected — real"},
        "exa": {"implemented": False, "configured": False, "status": "Not configured"},
        "google_sheets": {"implemented": False, "connected": False, "status": "Not configured"},
    }


@router.get("/provider/openrouter/health")
async def provider_health(): return await OpenRouterClient().health()


@router.post("/integrations/openrouter/verify")
async def verify_openrouter():
    result = await OpenRouterClient().verify()
    openrouter_verification.update(verified=result.status == "ok", status=result.status, request_id=result.request_id)
    with SessionLocal() as db:
        db.add(AgentRun(job_id="integration-openrouter", stage="OpenRouter connectivity", provider="OpenRouter (REAL)", model=result.configured_model, status="completed" if result.status == "ok" else "error", duration_ms=result.latency_ms, record_count=0, retry_count=0, redacted_error=result.error_type))
        db.commit()
    return result


@router.get("/auth/google/start")
async def google_start():
    if not oauth_configured(): raise HTTPException(409, "Google OAuth is not configured")
    return RedirectResponse(authorization_url())


@router.get("/auth/google/callback")
async def google_callback(request: Request, state: str):
    try: exchange_callback(str(request.url), state)
    except Exception as exc:
        error_type = type(exc).__name__
        print(f"Google OAuth callback failed safely: {error_type}: {str(exc)[:180]}", flush=True)
        raise HTTPException(400, {"code": error_type, "message": "Google OAuth token exchange failed"}) from exc
    return RedirectResponse(f"{settings.arus_frontend_url}/?view=settings&gmail=connected")


@router.post("/auth/google/disconnect")
async def google_disconnect(): disconnect(); return {"connected": False}


@router.post("/statements/import")
async def import_statement(pdf: UploadFile = File(...), user_id: str = Form(...), bank_layout: str = Form(...), pdf_password: str = Form(...)):
    content = await pdf.read(); digest = processor.hash_bytes(content); job_id = f"job_{uuid.uuid4().hex[:12]}"
    with SessionLocal() as db:
        existing = db.scalar(select(StatementRecord).where(StatementRecord.attachment_sha256 == digest))
        if existing and existing.state not in {StatementState.NEEDS_PASSWORD, StatementState.NEEDS_REVIEW}:
            return {"job_id": job_id, "statement_id": existing.id, "state": existing.state, "duplicate": True}
        record = existing or StatementRecord(user_id=user_id, attachment_sha256=digest, bank_layout=bank_layout, state=StatementState.PROCESSING)
        record.state = StatementState.PROCESSING; record.bank_layout = bank_layout
        record.safe_error = None; record.model_extraction = None; record.accepted_records = None; record.user_corrections = None
        if not existing: db.add(record)
        db.commit(); db.refresh(record)
        try:
            result = await process_record(db, record, content, pdf_password, job_id)
            return {"job_id": job_id, **result, "duplicate": False}
        except UnsupportedDocument as exc:
            raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
        except ProviderError as exc:
            raise HTTPException(503, {"code": "provider_failed", "message": "OpenRouter extraction could not be verified."}) from exc


@router.post("/sync")
async def sync():
    service = gmail_service()
    if not service: raise HTTPException(409, "Gmail is not connected")
    job_id = f"job_{uuid.uuid4().hex[:12]}"; discovered_started = time.perf_counter()
    adapter = RealGmailAdapter(service, settings.allowed_senders)
    seen: set[tuple[str, str, str]] = set()
    with SessionLocal() as db:
        for row in db.scalars(select(StatementRecord).where(StatementRecord.gmail_message_id.is_not(None))).all():
            seen.add((row.gmail_message_id or "", row.gmail_attachment_id or "", row.attachment_sha256))
    async def handler(attachment):
        digest = processor.hash_bytes(attachment.content)
        with SessionLocal() as db:
            record = StatementRecord(user_id="gmail-oauth", attachment_sha256=digest, gmail_message_id=attachment.message_id, gmail_attachment_id=attachment.attachment_id, bank_layout="auto", state=StatementState.PROCESSING)
            db.add(record); db.commit(); db.refresh(record)
            await process_record(db, record, attachment.content, settings.demo_pdf_password or "", job_id)
    result = await sync_attachments(adapter, handler, seen)
    with SessionLocal() as db:
        add_activity(db, job_id, "Gmail discovery", "Gmail API (REAL)", "completed", discovered_started, result["discovered"], error=None if not result["failed"] else "AttachmentProcessingFailed")
        db.commit()
    return {"job_id": job_id, "adapter": "real", "status": "completed", **result}


@router.get("/jobs/{job_id}")
async def job(job_id: str): return {"job_id": job_id, "status": "completed"}


@router.get("/statements")
async def list_statements():
    with SessionLocal() as db:
        rows = db.scalars(select(StatementRecord).order_by(StatementRecord.created_at.desc())).all()
        return [{"id": row.id, "state": row.state, "bank_layout": row.bank_layout, "source": "Gmail" if row.gmail_message_id else "Manual upload", "created_at": row.created_at, "gmail_message_id": row.gmail_message_id} for row in rows]


@router.get("/statements/{statement_id}")
async def statement(statement_id: int):
    with SessionLocal() as db:
        row = db.get(StatementRecord, statement_id)
        if not row: raise HTTPException(404, "Statement not found")
        return {"id": row.id, "state": row.state, "extraction": row.model_extraction, "accepted": row.accepted_records, "corrections": row.user_corrections}


@router.post("/statements/{statement_id}/password")
async def retry_password(statement_id: int): return {"statement_id": statement_id, "state": "processing", "message": "Re-submit the encrypted source through the import route."}


def consolidated_transactions() -> list[dict]:
    result: list[dict] = []
    with SessionLocal() as db:
        rows = db.scalars(select(StatementRecord).where(StatementRecord.state == StatementState.IMPORTED)).all()
        for row in rows:
            accepted = row.accepted_records or {}
            for transaction in accepted.get("transactions", []):
                result.append({**transaction, "statement_id": row.id, "institution": accepted.get("institution"), "masked_account_identifier": accepted.get("masked_account_identifier")})
    return result


@router.get("/transactions")
async def transactions(): return consolidated_transactions()


@router.post("/transactions/categorize")
async def categorize_transactions():
    """Backfill semantic labels on already-verified real transactions."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    categorized = 0
    updated_statements = 0
    try:
        with SessionLocal() as db:
            rows = db.scalars(select(StatementRecord).where(StatementRecord.state == StatementState.IMPORTED)).all()
            model_client = OpenRouterClient()
            for row in rows:
                extraction = StatementExtraction.model_validate(row.accepted_records or {})
                if not any(not transaction.suggested_category or not transaction.suggested_merchant for transaction in extraction.transactions):
                    continue
                categorized += await model_client.categorize(extraction.transactions)
                value = extraction.model_dump(mode="json")
                row.accepted_records = value
                row.model_extraction = value
                updated_statements += 1
            add_activity(db, job_id, "Transaction categorization", "OpenRouter (REAL)", "completed", started, categorized, model=settings.openrouter_model)
            db.commit()
    except ProviderError as exc:
        with SessionLocal() as db:
            add_activity(db, job_id, "Transaction categorization", "OpenRouter (REAL)", "error", started, error=type(exc).__name__, model=settings.openrouter_model)
            db.commit()
        raise HTTPException(503, {"code": "provider_failed", "message": "OpenRouter categorization could not be verified."}) from exc
    return {"job_id": job_id, "categorized": categorized, "updated_statements": updated_statements}


@router.get("/export/transactions.csv")
async def export_transactions_csv():
    fields = ["date", "suggested_merchant", "description", "masked_account_identifier", "suggested_category", "direction", "amount", "currency", "statement_id", "page_reference", "category_confidence"]
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
    for row in consolidated_transactions(): writer.writerow({key: row.get(key) for key in fields})
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=arus-transactions.csv"})


@router.get("/overview")
async def overview():
    with SessionLocal() as db:
        rows = db.scalars(select(StatementRecord).where(StatementRecord.state == StatementState.IMPORTED)).all()
        all_count = len(db.scalars(select(StatementRecord)).all())
        cash = Decimal("0"); debt = Decimal("0"); income = Decimal("0"); spending = Decimal("0"); dates: list[str] = []
        for row in rows:
            value = row.accepted_records or {}
            closing = Decimal(str(value.get("closing_balance") or "0"))
            account_type = str(value.get("account_type") or "").lower()
            is_credit_account = value.get("card_due_amount") is not None or any(marker in account_type for marker in ("credit", "card", "visa", "mastercard"))
            if is_credit_account: debt += closing
            else: cash += closing
            if value.get("statement_end_date"): dates.append(value["statement_end_date"])
            for txn in value.get("transactions", []):
                amount = Decimal(str(txn["amount"])); income += amount if txn["direction"] == "credit" else Decimal("0"); spending += amount if txn["direction"] == "debit" else Decimal("0")
        return {"latest_reported_cash": str(cash), "reported_card_debt": str(debt), "income": str(income), "spending": str(spending), "verified_statement_count": len(rows), "total_statement_count": all_count, "balance_dates": dates, "mixed_dates": len(set(dates)) > 1, "data_mode": "real" if rows else "empty"}


def serialize_goal(goal: GoalRecord) -> dict:
    return {
        "id": goal.id,
        "name": goal.name,
        "purpose": goal.purpose,
        "target_amount": str(goal.target_amount),
        "saved_amount": str(goal.saved_amount),
        "currency": goal.currency,
        "target_date": goal.target_date,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
    }


@router.get("/goals")
async def goals():
    with SessionLocal() as db:
        rows = db.scalars(select(GoalRecord).order_by(GoalRecord.created_at.desc())).all()
        return [serialize_goal(row) for row in rows]


@router.post("/goals", status_code=201)
async def create_goal(payload: GoalCreate):
    with SessionLocal() as db:
        row = GoalRecord(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return serialize_goal(row)


@router.patch("/goals/{goal_id}")
async def update_goal(goal_id: int, payload: GoalUpdate):
    with SessionLocal() as db:
        row = db.get(GoalRecord, goal_id)
        if not row:
            raise HTTPException(404, "Goal not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        db.commit()
        db.refresh(row)
        return serialize_goal(row)


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(goal_id: int):
    with SessionLocal() as db:
        row = db.get(GoalRecord, goal_id)
        if not row:
            raise HTTPException(404, "Goal not found")
        db.delete(row)
        db.commit()


@router.get("/agent-runs/{job_id}")
async def agent_runs(job_id: str):
    with SessionLocal() as db:
        rows = db.scalars(select(AgentRun).where(AgentRun.job_id == job_id).order_by(AgentRun.created_at)).all()
        return [{"stage": row.stage, "provider": row.provider, "model": row.model, "mode": "real" if "REAL" in row.provider else "local", "status": row.status, "duration_ms": row.duration_ms, "record_count": row.record_count, "retry_count": row.retry_count, "timestamp": row.created_at, "redacted_error": row.redacted_error} for row in rows]
