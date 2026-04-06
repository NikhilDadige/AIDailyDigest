"""Claude Pass 2 — Analyze compressed summaries for trends, rankings, and insights"""
import asyncio
import json
import os
from typing import Dict, List, Union
from urllib.request import urlopen, Request
from src.utils.config import get_taxonomy_summary


CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


def _call_claude(prompt: str, system: str, config: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = config["ai"]["pass2"]["model"]

    payload = json.dumps({
        "model": model,
        "max_tokens": config["ai"]["pass2"]["max_tokens"],
        "temperature": config["ai"]["pass2"]["temperature"],
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = Request(
        CLAUDE_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    with urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())

    return result["content"][0]["text"]


SYSTEM_PROMPT = """You are an expert AI industry analyst producing a daily digest. 
You analyze pre-processed article summaries and generate structured insights.
Always respond with valid JSON. No markdown, no preamble."""


def _build_trends_prompt(articles_json: str, taxonomy: str) -> str:
    return f"""Analyze these AI news articles and produce a TREND REPORT.

CURRENT TAXONOMY:
{taxonomy}

ARTICLES (pre-processed by Pass 1):
{articles_json}

Return a JSON object with:
{{
  "date": "YYYY-MM-DD",
  "mode": "trends",
  "total_articles": <int>,
  "top_picks": [
    {{
      "title": "...",
      "url": "...",
      "source": "...",
      "why_important": "1 sentence on why this matters",
      "impact_score": <1-10>,
      "primary_tag": "...",
      "secondary_tags": [...]
    }}
  ],  // top 5 most impactful articles
  "trend_signals": [
    {{
      "signal": "short description of the trend",
      "direction": "rising" | "fading" | "new" | "breakthrough",
      "evidence": ["article title 1", "article title 2"],
      "affected_categories": ["sub_topic_id_1", "sub_topic_id_2"]
    }}
  ],  // 3-5 cross-article trend signals
  "category_activity": {{
    "<main_topic_id>": {{
      "article_count": <int>,
      "notable": "1-line summary of what happened in this category"
    }}
  }},
  "articles": [
    {{
      "title": "...",
      "url": "...",
      "source": "...",
      "summary_short": "...",
      "summary_detailed": "...",
      "primary_tag": "...",
      "secondary_tags": [...],
      "main_topic": "...",
      "tool_names": [...],
      "content_type": "...",
      "impact_score": <1-10>,
      "trend_signal": "rising" | "stable" | "fading" | null
    }}
  ],
  "taxonomy_proposals": [
    {{
      "action": "add" | "merge" | "remove",
      "target": "sub_topic_id or new name",
      "parent": "main_topic_id",
      "rationale": "why this change"
    }}
  ]  // empty array if no changes needed
}}"""


def _build_news_prompt(articles_json: str, taxonomy: str) -> str:
    return f"""Organize these AI news articles into a clean NEWSLETTER.

CURRENT TAXONOMY:
{taxonomy}

ARTICLES (pre-processed by Pass 1):
{articles_json}

Return a JSON object with:
{{
  "date": "YYYY-MM-DD",
  "mode": "news",
  "total_articles": <int>,
  "headline": "The single most important story today in 1 sentence",
  "sections": [
    {{
      "main_topic": "<main_topic_id>",
      "topic_label": "Human-readable label",
      "articles": [
        {{
          "title": "...",
          "url": "...",
          "source": "...",
          "summary_short": "...",
          "summary_detailed": "...",
          "primary_tag": "...",
          "secondary_tags": [...],
          "tool_names": [...],
          "content_type": "...",
          "is_breaking": false
        }}
      ]
    }}
  ],  // grouped by main_topic, only include topics that have articles
  "launches": [
    {{
      "name": "tool or product name",
      "what": "1-line description",
      "url": "...",
      "category": "sub_topic_id"
    }}
  ],  // new product launches or major updates specifically
  "taxonomy_proposals": []
}}"""


def _build_weekly_trends_prompt(week_data: str) -> str:
    return f"""Aggregate this week's daily trend data into a WEEKLY TREND REPORT.

WEEK DATA (daily summaries Mon-Sun):
{week_data}

Return a JSON object with:
{{
  "week": "YYYY-MM-DD to YYYY-MM-DD",
  "mode": "weekly_trends",
  "leaderboard": [
    {{
      "rank": 1,
      "tool_name": "...",
      "mentions": <int>,
      "avg_impact": <float>,
      "categories": ["..."],
      "trend": "rising" | "stable" | "new"
    }}
  ],  // top 15 tools by mentions * impact
  "category_heatmap": {{
    "<main_topic_id>": {{
      "article_count": <int>,
      "avg_impact": <float>,
      "hottest_subtopic": "...",
      "trend_vs_last_week": "up" | "down" | "stable"
    }}
  }},
  "biggest_movers": [
    {{
      "name": "tool or category",
      "movement": "Entered top 10" | "Jumped 5 spots" | etc,
      "why": "1-line explanation"
    }}
  ],
  "emerging_themes": [
    {{
      "theme": "short description",
      "evidence_count": <int>,
      "first_seen": "day of week"
    }}
  ],
  "week_summary": "3-4 sentence executive summary of the week in AI"
}}"""


def _build_weekly_digest_prompt(week_data: str) -> str:
    return f"""Create a WEEKLY DIGEST from this week's data.

WEEK DATA (daily summaries Mon-Sun):
{week_data}

Return a JSON object with:
{{
  "week": "YYYY-MM-DD to YYYY-MM-DD",
  "mode": "weekly_digest",
  "executive_summary": "4-5 sentence summary of the week — the 'if you read nothing else' version",
  "top_stories": [
    {{
      "rank": 1,
      "title": "...",
      "url": "...",
      "source": "...",
      "why_top": "Why this was the biggest story this week",
      "impact_score": <1-10>
    }}
  ],  // top 5 stories of the week
  "by_category": [
    {{
      "main_topic": "...",
      "topic_label": "...",
      "week_summary": "2-3 sentence summary for this category",
      "key_articles": ["title1", "title2"]
    }}
  ],
  "notable_launches": [
    {{
      "name": "...",
      "what": "...",
      "url": "...",
      "day": "Monday" | etc
    }}
  ],
  "what_you_missed": [
    {{
      "title": "...",
      "url": "...",
      "why": "1-line on why it's worth reading"
    }}
  ]  // 3-5 articles that were important but easy to miss
}}"""


async def claude_analyze(
    data: Union[List[Dict], List[str]],
    mode: str,
    config: dict,
    is_weekly: bool = False
) -> Dict:
    taxonomy = get_taxonomy_summary(config)

    if is_weekly:
        combined = "\n---\n".join(data) if isinstance(data[0], str) else json.dumps(data)
        if mode == "weekly_trends":
            prompt = _build_weekly_trends_prompt(combined)
        else:
            prompt = _build_weekly_digest_prompt(combined)
    else:
        articles_json = json.dumps(data, indent=1)
        if mode == "trends":
            prompt = _build_trends_prompt(articles_json, taxonomy)
        else:
            prompt = _build_news_prompt(articles_json, taxonomy)

    result = await asyncio.to_thread(_call_claude, prompt, SYSTEM_PROMPT, config)

    # Parse JSON from response (handle possible markdown wrapping)
    text = result.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(text)
