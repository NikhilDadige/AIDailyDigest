"""Notion deliverer — pushes articles to database + creates daily/weekly pages"""
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict
from urllib.request import urlopen, Request

NOTION_API = "https://api.notion.com/v1"
IST = timezone(timedelta(hours=5, minutes=30))


def _notion_request(method: str, endpoint: str, body: dict = None) -> dict:
    token = os.environ.get("NOTION_API_KEY", "")
    url = f"{NOTION_API}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


async def _add_article_to_db(article: dict, config: dict):
    db_id = config["delivery"]["notion"]["database_id"]
    properties = {
        "Title": {"title": [{"text": {"content": article.get("title", "")[:100]}}]},
        "URL": {"url": article.get("url", "")},
        "Source": {"select": {"name": article.get("source", "Unknown")[:100]}},
        "Primary Tag": {"select": {"name": article.get("primary_tag", "general")[:100]}},
        "Main Topic": {"select": {"name": article.get("main_topic", "")[:100]}},
        "Impact Score": {"number": article.get("impact_score", 0)},
        "Content Type": {"select": {"name": article.get("content_type", "update")[:100]}},
        "Summary": {"rich_text": [{"text": {"content": article.get("summary_short", "")[:2000]}}]},
        "Date": {"date": {"start": datetime.now(IST).strftime("%Y-%m-%d")}},
    }

    # Secondary tags as multi-select
    sec_tags = article.get("secondary_tags", [])
    if sec_tags:
        properties["Secondary Tags"] = {"multi_select": [{"name": t[:100]} for t in sec_tags[:5]]}

    # Tool names as multi-select
    tools = article.get("tool_names", [])
    if tools:
        properties["Tools Mentioned"] = {"multi_select": [{"name": t[:100]} for t in tools[:5]]}

    body = {"parent": {"database_id": db_id}, "properties": properties}
    await asyncio.to_thread(_notion_request, "POST", "pages", body)


async def _create_digest_page(analysis: dict, mode: str, config: dict):
    parent_key = "weekly_page_parent" if "weekly" in mode else "daily_page_parent"
    parent_id = config["delivery"]["notion"].get(parent_key, "")
    if not parent_id:
        return

    now = datetime.now(IST)
    mode_labels = {
        "trends": "Daily Trends",
        "news": "Daily Newsletter",
        "weekly_trends": "Weekly Trend Report",
        "weekly_digest": "Weekly Digest",
    }
    title = f"{mode_labels.get(mode, mode)} — {now.strftime('%B %d, %Y')}"

    # Build page content blocks
    children = []

    # Executive summary or headline
    summary = analysis.get("executive_summary") or analysis.get("headline") or analysis.get("week_summary", "")
    if summary:
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}],
                "color": "purple_background",
            }
        })

    # Top picks / stories
    top = analysis.get("top_picks") or analysis.get("top_stories", [])
    if top:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Top stories"}}]}
        })
        for item in top[:5]:
            text = f"{item.get('title', '')} — {item.get('why_important', item.get('why_top', ''))}"
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": text[:2000]}}]}
            })

    body = {
        "parent": {"page_id": parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": children[:50],
    }
    await asyncio.to_thread(_notion_request, "POST", "pages", body)


async def push_to_notion(analysis: dict, mode: str, config: dict):
    if not config["delivery"]["notion"]["enabled"]:
        return

    # Add individual articles to database
    articles = analysis.get("articles", [])
    if not articles:
        # For news mode, articles are nested inside sections
        for section in analysis.get("sections", []):
            articles.extend(section.get("articles", []))

    for article in articles:
        try:
            await _add_article_to_db(article, config)
            await asyncio.sleep(0.4)  # Rate limit: 3 req/sec
        except Exception as e:
            print(f"  Warning: Failed to add article to Notion: {e}")

    # Create digest page
    try:
        await _create_digest_page(analysis, mode, config)
    except Exception as e:
        print(f"  Warning: Failed to create Notion page: {e}")
