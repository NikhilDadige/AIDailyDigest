"""RSS feed fetcher — pulls articles from configured RSS sources"""
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import feedparser


async def fetch_rss_feeds(feeds_config: List[Dict]) -> List[Dict]:
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for feed_cfg in feeds_config:
        try:
            feed = await asyncio.to_thread(feedparser.parse, feed_cfg["url"])
            for entry in feed.entries[:10]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                if published and published < cutoff:
                    continue

                url = entry.get("link", "")
                article_id = hashlib.md5(url.encode()).hexdigest()[:12]

                summary = ""
                if hasattr(entry, "summary"):
                    summary = entry.summary[:2000]
                elif hasattr(entry, "description"):
                    summary = entry.description[:2000]

                # Strip HTML tags from summary
                import re
                summary = re.sub(r'<[^>]+>', '', summary).strip()

                articles.append({
                    "id": article_id,
                    "title": entry.get("title", "Untitled"),
                    "url": url,
                    "source": feed_cfg["name"],
                    "source_type": "rss",
                    "category_hint": feed_cfg.get("category_hint", "general"),
                    "published": published.isoformat() if published else None,
                    "raw_summary": summary[:1500],
                })
        except Exception as e:
            print(f"  Warning: Failed to fetch {feed_cfg['name']}: {e}")
            continue

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    return unique
