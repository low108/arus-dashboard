"""Print the chat ID of whoever has messaged your bot.

Run this AFTER you have sent your bot a message in Telegram.

    python find_chat_id.py
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent


def load_env():
    path = HERE / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(),
                                  value.strip().strip('"').strip("'"))


load_env()
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    sys.exit("No TELEGRAM_BOT_TOKEN found.\n"
             "Put your token in a file called .env next to this script, "
             "like this:\n\n    TELEGRAM_BOT_TOKEN=123456:ABC-your-token\n")

url = f"https://api.telegram.org/bot{token}/getUpdates"
try:
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.load(resp)
except urllib.error.HTTPError as err:
    sys.exit(f"Telegram rejected the token. Check it is copied exactly.\n"
             f"{err.read().decode(errors='replace')}")

if not payload.get("ok"):
    sys.exit(f"Telegram said: {payload}")

seen = {}
for update in payload.get("result", []):
    message = (update.get("message") or update.get("channel_post")
               or update.get("edited_message") or {})
    chat = message.get("chat")
    if chat:
        name = (chat.get("title") or
                " ".join(filter(None, [chat.get("first_name"),
                                       chat.get("last_name")])) or
                chat.get("username") or "(no name)")
        seen[chat["id"]] = f"{name}  [{chat.get('type')}]"

if not seen:
    print("Your bot has not received any messages yet.\n\n"
          "Open Telegram, search for your bot by its @username, press START, "
          "send it any message, then run this again.\n\n"
          "Note: Telegram only keeps recent messages here, so if you sent one "
          "a long time ago, send another.")
else:
    print("Found these chats. Copy the number you want into .env as "
          "TELEGRAM_CHAT_ID:\n")
    for chat_id, who in seen.items():
        print(f"  TELEGRAM_CHAT_ID={chat_id}      {who}")
