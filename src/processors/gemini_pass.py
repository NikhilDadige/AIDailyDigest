"""Gemini Pass 1 — Compress raw articles into structured JSON summaries"""
import asyncio
import json
import os
from typing import Dict, List
from urllib.request import urlopen, Request
from src.utils.config import get_taxonomy_summary


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _call_gemini(prompt: str, config: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = config["ai"]["pass1"]["model"]
    url = GEMINI_API_URL.format(model=model) + f"?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": config["ai"]["pass1"]["temperature"],
            "maxOutputTokens": config["ai"]["pass1"]["max_tokens"],
            "responseMimeType": "application/json",
        }
    }).encode()

    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return text


async def gemini_compress(articles: List[Dict], config: dict) -> List[Dict]:
    taxonomy_text = get_taxonomy_summary(config)
    compressed = []

    # Process in batches of 5 to stay well within rate limits
    batch_size = 5
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        batch_json = json.dumps([{
            "title": a["title"],
            "source": a["source"],
            "url": a["url"],
            "raw_summary": a.get("raw_summary", ""),
            "category_hint": a.get("category_hint", "general"),
        } for a in batch], indent=1)

        prompt = f"""You are an AI news analyst. Process these articles into structured JSON.

TAXONOMY (assign tags from these categories):
{taxonomy_text}

ARTICLES TO PROCESS:
{batch_json}

For each article, return a JSON array where each item has:
- "title": original title
- "url": original URL
- "source": original source
- "summary_short": 1-line summary (max 20 words)
- "summary_detailed": 2-3 sentence summary
- "primary_tag": the single best matching sub_topic ID from taxonomy
- "secondary_tags": array of 0-3 additional sub_topic IDs that also apply
- "main_topic": the parent main_topic ID for the primary_tag
- "tool_names": array of specific tool/product names mentioned (e.g. ["Claude Code", "GPT-5"])
- "content_type": one of "launch", "update", "research", "opinion", "tutorial", "funding", "policy"

Return ONLY the JSON array, no markdown formatting."""

        try:
            result = await asyncio.to_thread(_call_gemini, prompt, config)
            parsed = json.loads(result)
            if isinstance(parsed, list):
                compressed.extend(parsed)
        except Exception as e:
            print(f"  Warning: Gemini batch {i//batch_size + 1} failed: {e}")
            # Fallback: create minimal entries
            for a in batch:
                compressed.append({
                    "title": a["title"],
                    "url": a["url"],
                    "source": a["source"],
                    "summary_short": a["title"],
                    "summary_detailed": a.get("raw_summary", "")[:200],
                    "primary_tag": a.get("category_hint", "general"),
                    "secondary_tags": [],
                    "main_topic": "intelligence_research",
                    "tool_names": [],
                    "content_type": "update",
                })

        # Small delay between batches to respect rate limits
        if i + batch_size < len(articles):
            await asyncio.sleep(2)

    return compressed
