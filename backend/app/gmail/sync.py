import hashlib
from collections.abc import Awaitable, Callable
from app.gmail.adapters import GmailAdapter, GmailAttachment


async def sync_attachments(adapter: GmailAdapter, handler: Callable[[GmailAttachment], Awaitable[None]], seen: set[tuple[str, str, str]]) -> dict[str, int]:
    result = {"discovered": 0, "processed": 0, "duplicates": 0, "failed": 0}
    for attachment in await adapter.discover():
        result["discovered"] += 1
        digest = hashlib.sha256(attachment.content).hexdigest()
        key = (attachment.message_id, attachment.attachment_id, digest)
        if key in seen:
            result["duplicates"] += 1
            continue
        try:
            await handler(attachment)
            seen.add(key)
            result["processed"] += 1
        except Exception:
            result["failed"] += 1
    return result
