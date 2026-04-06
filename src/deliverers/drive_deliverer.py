"""Google Drive deliverer — uploads PDF for NotebookLM consumption"""
import asyncio
import json
import os
from pathlib import Path
from urllib.request import urlopen, Request

DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"


async def upload_pdf_to_drive(pdf_path: str, config: dict):
    if not config["delivery"]["google_drive"]["enabled"]:
        return

    api_key = os.environ.get("GOOGLE_DRIVE_API_KEY", "")
    folder_id = config["delivery"]["google_drive"]["folder_id"]
    filename = Path(pdf_path).name

    metadata = json.dumps({
        "name": filename,
        "parents": [folder_id],
        "mimeType": "application/pdf",
    })

    pdf_data = Path(pdf_path).read_bytes()

    boundary = "----AgentBoundary"
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{metadata}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + pdf_data + f"\r\n--{boundary}--\r\n".encode()

    req = Request(
        f"{DRIVE_UPLOAD_API}&key={api_key}",
        data=body,
        headers={
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )

    try:
        await asyncio.to_thread(lambda: urlopen(req, timeout=30).read())
    except Exception as e:
        print(f"  Warning: Drive upload failed: {e}")
