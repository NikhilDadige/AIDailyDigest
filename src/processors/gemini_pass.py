"""Gemini Pass 1 — Compress raw articles into structured JSON summaries"""
import asyncio
import json
import os
import re
from typing import Dict, List
from urllib.request import urlopen, Request


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Compact taxonomy for prompt (keeps token usage low)
TAXONOMY_SHORT = """Main topics and sub-topics:
content_creation: image_generation, video_generation, audio_music, writing_copy, three_d_spatial, presentations_design
development_engineering: coding_assistants, vibe_coding, devops_cloud, databases_vector, open_source_models, developer_utilities
intelligence_research: foundation_models, research_knowledge, search_discovery, data_analytics
agents_automation: workflow_automation, ai_assistants, browser_agents, voice_agents, customer_support
media_utilities: media_image_utilities, media_video_utilities, media_audio_utilities, document_utilities
business_productivity: productivity_pm, marketing_seo, meetings_comms, sales_crm, finance_accounting, hr_recruiting
social_media_creators: social_content, creator_monetization, social_analytics
personal_ai: health_fitness, personal_finance, travel_lifestyle, learning_study
frontier_ecosystem: hardware_chips, robotics, healthcare_biotech, safety_ethics, education_tech, funding_acquisitions, climate_sustainability
translation_localization: realtime_translation, document_translation
legal_compliance: contract_ai, compliance_tools
security_ai: threat_detection, vulnerability_scanning
accessibility: visual_accessibility, communication_access
ecommerce_ai: product_listing, customer_experience, logistics_operations"""


def _call_gemini(prompt: str, model: str, api_key: str) -> str:
    url = GEMINI_API_URL.format(model=model) + f"?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
        }
    }).encode()

    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return text


def _parse_json_safe(text: str) -> dict:
    """Try multiple strategies to parse JSON from LLM output"""
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try finding first { to last } or first [ to last ]
    for open_c, close_c in [('{', '}'), ('[', ']')]:
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


async def gemini_compress(articles: List[Dict], config: dict) -> List[Dict]:
    compressed = []
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = config["ai"]["pass1"]["model"]

    # Process articles one at a time for reliable JSON output
    for idx, article in enumerate(articles):
        prompt = f"""You are an AI news analyst. Process this article into structured JSON.

TAXONOMY:
{TAXONOMY_SHORT}

ARTICLE:
Title: {article['title']}
Source: {article['source']}
URL: {article['url']}
Summary: {article.get('raw_summary', '')[:800]}

Return a single JSON object with these keys:
"title": original title
"url": original URL
"source": original source
"summary_short": 1-line summary max 20 words
"summary_detailed": 2-3 sentence summary
"primary_tag": best matching sub_topic ID from taxonomy
"secondary_tags": array of 0-2 related sub_topic IDs
"main_topic": parent main_topic ID for the primary_tag
"tool_names": array of specific tool names mentioned
"content_type": one of "launch","update","research","opinion","tutorial","funding","policy"

Return ONLY valid JSON."""

        try:
            result = await asyncio.to_thread(_call_gemini, prompt, model, api_key)
            parsed = _parse_json_safe(result)

            if isinstance(parsed, list):
                parsed = parsed[0] if parsed else {}

            parsed.setdefault("title", article["title"])
            parsed.setdefault("url", article["url"])
            parsed.setdefault("source", article["source"])
            parsed.setdefault("summary_short", article["title"])
            parsed.setdefault("summary_detailed", article.get("raw_summary", "")[:200])
            parsed.setdefault("primary_tag", article.get("category_hint", "general"))
            parsed.setdefault("secondary_tags", [])
            parsed.setdefault("main_topic", "intelligence_research")
            parsed.setdefault("tool_names", [])
            parsed.setdefault("content_type", "update")

            compressed.append(parsed)

        except Exception as e:
            print(f"  Warning: Gemini article {idx+1} failed: {e}")
            compressed.append({
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                "summary_short": article["title"],
                "summary_detailed": article.get("raw_summary", "")[:200],
                "primary_tag": article.get("category_hint", "general"),
                "secondary_tags": [],
                "main_topic": "intelligence_research",
                "tool_names": [],
                "content_type": "update",
            })

        if idx < len(articles) - 1:
            await asyncio.sleep(1.5)

    return compressed
