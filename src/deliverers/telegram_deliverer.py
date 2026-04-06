"""Telegram deliverer — sends formatted messages via Bot API"""
import asyncio
import json
import os
from urllib.request import urlopen, Request

TG_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_digest(message: str, config: dict):
    if not config["delivery"]["telegram"]["enabled"]:
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = config["delivery"]["telegram"]["chat_id"]

    # Telegram has a 4096 char limit per message
    chunks = []
    while message:
        if len(message) <= 4000:
            chunks.append(message)
            break
        split_at = message[:4000].rfind("\n")
        if split_at == -1:
            split_at = 4000
        chunks.append(message[:split_at])
        message = message[split_at:].lstrip()

    for chunk in chunks:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }).encode()

        url = TG_API.format(token=token)
        req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

        try:
            await asyncio.to_thread(lambda: urlopen(req, timeout=15).read())
        except Exception as e:
            print(f"  Warning: Telegram send failed: {e}")

        if len(chunks) > 1:
            await asyncio.sleep(1)
