from datetime import datetime
import pytest
from app.gmail.adapters import GmailAttachment, MockGmailAdapter
from app.gmail.sync import sync_attachments


def attachment(index: int) -> GmailAttachment:
    return GmailAttachment(str(index), str(index), "statements@example.test", datetime(2026, 9, 13), f"statement-{index}.pdf", f"pdf-{index}".encode())


@pytest.mark.asyncio
async def test_one_failed_attachment_does_not_block_another():
    items = [attachment(1), attachment(2)]
    async def handler(item):
        if item.message_id == "1": raise ValueError("fixture failure")
    result = await sync_attachments(MockGmailAdapter(items), handler, set())
    assert result == {"discovered": 2, "processed": 1, "duplicates": 0, "failed": 1}


@pytest.mark.asyncio
async def test_repeated_sync_is_idempotent():
    seen = set(); items = [attachment(1)]
    async def handler(item): pass
    await sync_attachments(MockGmailAdapter(items), handler, seen)
    second = await sync_attachments(MockGmailAdapter(items), handler, seen)
    assert second["duplicates"] == 1 and second["processed"] == 0
