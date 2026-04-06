"""Google Sheets deliverer — appends rows to tracking spreadsheet"""
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict
from urllib.request import urlopen, Request

IST = timezone(timedelta(hours=5, minutes=30))
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def _sheets_request(method: str, url: str, body: dict = None) -> dict:
    api_key = os.environ.get("GOOGLE_SHEETS_API_KEY", "")
    full_url = f"{url}?key={api_key}" if "?" not in url else f"{url}&key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = Request(full_url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


async def push_to_sheets(analysis: dict, mode: str, config: dict):
    if not config["delivery"]["google_sheets"]["enabled"]:
        return

    spreadsheet_id = config["delivery"]["google_sheets"]["spreadsheet_id"]
    now = datetime.now(IST)

    articles = analysis.get("articles", [])
    if not articles:
        for section in analysis.get("sections", []):
            articles.extend(section.get("articles", []))

    if not articles:
        return

    sheet_name = config["delivery"]["google_sheets"]["daily_sheet"]
    if "weekly" in mode:
        sheet_name = config["delivery"]["google_sheets"]["weekly_sheet"]

    rows = []
    for a in articles:
        rows.append([
            now.strftime("%Y-%m-%d"),
            mode,
            a.get("title", ""),
            a.get("url", ""),
            a.get("source", ""),
            a.get("primary_tag", ""),
            ", ".join(a.get("secondary_tags", [])),
            a.get("main_topic", ""),
            a.get("impact_score", 0),
            a.get("content_type", ""),
            a.get("summary_short", ""),
            ", ".join(a.get("tool_names", [])),
            a.get("trend_signal", ""),
        ])

    body = {"values": rows}
    url = f"{SHEETS_API}/{spreadsheet_id}/values/{sheet_name}!A:M:append?valueInputOption=RAW"

    try:
        await asyncio.to_thread(_sheets_request, "POST", url, body)
    except Exception as e:
        print(f"  Warning: Failed to push to Sheets: {e}")
