"""Hacker News fetcher — pulls top AI-related stories via Firebase API"""
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List
from urllib.request import urlopen, Request


def _fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "AI-Digest-Agent/1.0"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


async def fetch_hacker_news(config: Dict) -> List[Dict]:
    endpoint = config["endpoint"]
    keywords = [k.lower() for k in config.get("filter_keywords", [])]
    max_stories = config.get("max_stories", 15)

    top_ids = await asyncio.to_thread(_fetch_json, f"{endpoint}/topstories.json")
    top_ids = top_ids[:100]

    articles = []
    for story_id in top_ids:
        if len(articles) >= max_stories:
            break
        try:
            story = await asyncio.to_thread(_fetch_json, f"{endpoint}/item/{story_id}.json")
            if not story or story.get("type") != "story":
                continue

            title = story.get("title", "").lower()
            url = story.get("url", "")
            if not url:
                url = f"https://news.ycombinator.com/item?id={story_id}"

            if not any(kw in title for kw in keywords):
                continue

            article_id = hashlib.md5(url.encode()).hexdigest()[:12]
            published = None
            if story.get("time"):
                published = datetime.fromtimestamp(story["time"], tz=timezone.utc)

            articles.append({
                "id": article_id,
                "title": story.get("title", "Untitled"),
                "url": url,
                "source": "Hacker News",
                "source_type": "hn",
                "category_hint": "general",
                "published": published.isoformat() if published else None,
                "raw_summary": f"HN score: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}",
                "hn_score": story.get("score", 0),
            })
        except Exception:
            continue

    articles.sort(key=lambda x: x.get("hn_score", 0), reverse=True)
    return articles[:max_stories]
