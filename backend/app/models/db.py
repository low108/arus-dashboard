from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import JSON, Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.config import settings


class Base(DeclarativeBase):
    pass


class StatementRecord(Base):
    __tablename__ = "statements"
    __table_args__ = (UniqueConstraint("attachment_sha256"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    attachment_sha256: Mapped[str] = mapped_column(String(64))
    gmail_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gmail_attachment_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bank_layout: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(30))
    model_extraction: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    accepted_records: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_corrections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    safe_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(80), index=True)
    stage: Mapped[str] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    duration_ms: Mapped[int] = mapped_column(Integer)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    redacted_error: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GoalRecord(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(String(40), index=True)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    saved_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="MYR")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
