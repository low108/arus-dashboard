from datetime import date
from decimal import Decimal
import pytest
from app.models.schemas import StatementExtraction, TransactionExtraction


@pytest.fixture
def valid_extraction():
    return StatementExtraction(
        institution="Meridian Bank", masked_account_identifier="•••• 4821", account_type="current",
        currency="MYR", statement_start_date=date(2026, 8, 1), statement_end_date=date(2026, 8, 31),
        opening_balance=Decimal("1000.00"), closing_balance=Decimal("1100.00"), source_pages=[1],
        transactions=[
            TransactionExtraction(source_identifier="p1-r1", date=date(2026, 8, 4), description="Salary", direction="credit", amount=Decimal("250.00"), currency="MYR", page_reference=1),
            TransactionExtraction(source_identifier="p1-r2", date=date(2026, 8, 8), description="Rent", direction="debit", amount=Decimal("150.00"), currency="MYR", page_reference=1),
        ],
    )
