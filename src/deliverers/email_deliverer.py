"""Email deliverer — sends HTML digest via Resend API"""
import asyncio
import json
import os
from typing import Dict
from urllib.request import urlopen, Request

RESEND_API = "https://api.resend.com/emails"
MODE_SUBJECTS = {
    "trends": "AI Trends Digest",
    "news": "AI Daily Newsletter",
    "weekly_trends": "Weekly AI Trend Report",
    "weekly_digest": "Weekly AI Digest",
}


async def send_email_digest(html: str, mode: str, config: dict):
    if not config["delivery"]["email"]["enabled"]:
        return

    api_key = os.environ.get("RESEND_API_KEY", "")
    to_email = config["delivery"]["email"]["to"]
    from_email = config["delivery"]["email"]["from"] or "digest@resend.dev"

    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    subject = f"{MODE_SUBJECTS.get(mode, 'AI Digest')} — {now.strftime('%B %d, %Y')}"

    payload = json.dumps({
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }).encode()

    req = Request(
        RESEND_API,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        await asyncio.to_thread(lambda: urlopen(req, timeout=15).read())
    except Exception as e:
        print(f"  Warning: Email send failed: {e}")
