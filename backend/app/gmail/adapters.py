from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable


@dataclass(frozen=True)
class GmailAttachment:
    message_id: str
    attachment_id: str
    sender: str
    received_at: datetime
    filename: str
    content: bytes


class GmailAdapter(ABC):
    @abstractmethod
    async def discover(self) -> Iterable[GmailAttachment]: ...


class SyntheticGmailAdapter(GmailAdapter):
    """Clearly labelled fixture adapter; never represents a live Gmail connection."""
    def __init__(self, attachments: list[GmailAttachment]): self.attachments = attachments
    async def discover(self): return list(self.attachments)


class MockGmailAdapter(SyntheticGmailAdapter):
    pass


class RealGmailAdapter(GmailAdapter):
    """Read-only Gmail boundary. OAuth credentials are supplied by the caller, never logged."""
    def __init__(self, gmail_service, allowed_senders: set[str], after: datetime | None = None):
        self.service, self.allowed_senders, self.after = gmail_service, allowed_senders, after

    async def discover(self):
        sender_query = " OR ".join(f"from:{sender}" for sender in sorted(self.allowed_senders))
        query = "has:attachment filename:pdf"
        if sender_query:
            query += f" ({sender_query})"
        if self.after:
            query += f" after:{self.after.strftime('%Y/%m/%d')}"
        page_token = None
        found: list[GmailAttachment] = []
        while True:
            response = self.service.users().messages().list(userId="me", q=query, pageToken=page_token).execute()
            for item in response.get("messages", []):
                message = self.service.users().messages().get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Date"]).execute()
                headers = {header["name"].lower(): header["value"] for header in message.get("payload", {}).get("headers", [])}
                sender = headers.get("from", "")
                if self.allowed_senders and not any(allowed in sender.lower() for allowed in self.allowed_senders):
                    continue
                received = parsedate_to_datetime(headers["date"]) if headers.get("date") else datetime.fromtimestamp(int(message.get("internalDate", "0")) / 1000)
                stack = list(message.get("payload", {}).get("parts", []))
                while stack:
                    part = stack.pop()
                    stack.extend(part.get("parts", []))
                    body = part.get("body", {})
                    filename = part.get("filename", "")
                    attachment_id = body.get("attachmentId")
                    if not attachment_id or not filename.lower().endswith(".pdf") or part.get("mimeType") != "application/pdf":
                        continue
                    payload = self.service.users().messages().attachments().get(userId="me", messageId=item["id"], id=attachment_id).execute()
                    encoded = payload.get("data", "")
                    content = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
                    found.append(GmailAttachment(item["id"], attachment_id, sender, received, filename, content))
            page_token = response.get("nextPageToken")
            if not page_token:
                return found
