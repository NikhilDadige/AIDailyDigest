"""Markdown formatter — generates archive-friendly markdown"""
from typing import Dict
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def format_markdown_archive(analysis: Dict, mode: str) -> str:
    now = datetime.now(IST)
    lines = [f"# {mode.replace('_',' ').title()} — {now.strftime('%Y-%m-%d')}\n"]

    summary = analysis.get("executive_summary") or analysis.get("headline") or analysis.get("week_summary", "")
    if summary:
        lines.append(f"> {summary}\n")

    top = analysis.get("top_picks") or analysis.get("top_stories", [])
    if top:
        lines.append("## Top stories\n")
        for item in top:
            score = item.get("impact_score", "")
            lines.append(f"- **[{score}/10]** [{item.get('title','')}]({item.get('url','')})")
            why = item.get("why_important") or item.get("why_top", "")
            if why:
                lines.append(f"  {why}")
        lines.append("")

    articles = analysis.get("articles", [])
    if articles:
        lines.append("## All articles\n")
        for a in articles:
            lines.append(f"- [{a.get('title','')}]({a.get('url','')}) — {a.get('source','')}")
            lines.append(f"  Tags: {a.get('primary_tag','')} | {', '.join(a.get('secondary_tags',[]))}")
        lines.append("")

    for section in analysis.get("sections", []):
        lines.append(f"## {section.get('topic_label','')}\n")
        for a in section.get("articles", []):
            lines.append(f"- [{a.get('title','')}]({a.get('url','')}) — {a.get('summary_short','')}")
        lines.append("")

    signals = analysis.get("trend_signals", [])
    if signals:
        lines.append("## Trend signals\n")
        for s in signals:
            lines.append(f"- **{s.get('direction','').upper()}**: {s.get('signal','')}")
        lines.append("")

    return "\n".join(lines)
