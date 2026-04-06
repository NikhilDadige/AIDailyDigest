"""Telegram formatter — plain text with HTML tags for Telegram"""
from typing import Dict

def format_telegram_message(analysis: Dict, mode: str) -> str:
    lines = []
    if mode == "trends":
        lines.append("<b>AI Trend Report</b>\n")
        for item in analysis.get("top_picks", [])[:5]:
            score = item.get("impact_score", 0)
            lines.append(f"<b>[{score}/10]</b> {item.get('title','')}")
            lines.append(f"  <i>{item.get('why_important','')}</i>")
            lines.append(f"  {item.get('url','')}\n")
        signals = analysis.get("trend_signals", [])
        if signals:
            lines.append("\n<b>Trend signals:</b>")
            for s in signals[:3]:
                lines.append(f"  {s.get('direction','').upper()}: {s.get('signal','')}")

    elif mode == "news":
        lines.append("<b>AI Daily Newsletter</b>\n")
        headline = analysis.get("headline", "")
        if headline:
            lines.append(f"<b>{headline}</b>\n")
        for section in analysis.get("sections", [])[:4]:
            lines.append(f"\n<b>{section.get('topic_label','')}</b>")
            for a in section.get("articles", [])[:3]:
                lines.append(f"  {a.get('title','')}")
                lines.append(f"  {a.get('url','')}")

    elif mode == "weekly_trends":
        lines.append("<b>Weekly AI Trend Report</b>\n")
        summary = analysis.get("week_summary", "")
        if summary:
            lines.append(f"{summary}\n")
        for item in analysis.get("leaderboard", [])[:10]:
            lines.append(f"  #{item.get('rank','')} {item.get('tool_name','')} ({item.get('trend','')})")

    elif mode == "weekly_digest":
        lines.append("<b>Weekly AI Digest</b>\n")
        summary = analysis.get("executive_summary", "")
        if summary:
            lines.append(f"{summary}\n")
        for item in analysis.get("top_stories", [])[:5]:
            lines.append(f"  #{item.get('rank','')} {item.get('title','')}")
            lines.append(f"  {item.get('url','')}")

    return "\n".join(lines)
