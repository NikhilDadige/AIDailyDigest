"""Email formatter — generates clean HTML digest emails"""
from datetime import datetime, timezone, timedelta
from typing import Dict

IST = timezone(timedelta(hours=5, minutes=30))

MODE_TITLES = {
    "trends": "AI Trend Report",
    "news": "AI Daily Newsletter",
    "weekly_trends": "Weekly Trend Report",
    "weekly_digest": "Weekly Digest",
}


def format_email_html(analysis: Dict, mode: str) -> str:
    now = datetime.now(IST)
    title = MODE_TITLES.get(mode, "AI Digest")
    date_str = now.strftime("%B %d, %Y")

    articles_html = ""

    if mode == "trends":
        # Top picks
        top = analysis.get("top_picks", [])
        if top:
            articles_html += '<h2 style="color:#a78bfa;font-size:18px;margin:24px 0 12px;">Top picks</h2>'
            for item in top:
                score = item.get("impact_score", 0)
                score_color = "#34d399" if score >= 7 else "#fbbf24" if score >= 4 else "#9a9a9f"
                articles_html += f'''
                <div style="padding:14px 0;border-bottom:1px solid #2a2a30;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <a href="{item.get('url','')}" style="color:#e8e6e3;text-decoration:none;font-weight:600;font-size:15px;">{item.get('title','')}</a>
                    <span style="color:{score_color};font-weight:700;font-size:14px;min-width:30px;text-align:right;">{score}/10</span>
                  </div>
                  <p style="color:#9a9a9f;font-size:13px;margin:4px 0 0;">{item.get('why_important','')}</p>
                  <span style="color:#5a5a60;font-size:12px;">{item.get('source','')} · {item.get('primary_tag','')}</span>
                </div>'''

        # Trend signals
        signals = analysis.get("trend_signals", [])
        if signals:
            articles_html += '<h2 style="color:#2dd4bf;font-size:18px;margin:24px 0 12px;">Trend signals</h2>'
            for sig in signals:
                direction_colors = {"rising": "#34d399", "fading": "#fb7185", "new": "#60a5fa", "breakthrough": "#fbbf24"}
                dc = direction_colors.get(sig.get("direction", ""), "#9a9a9f")
                articles_html += f'''
                <div style="padding:10px 0;border-bottom:1px solid #2a2a30;">
                  <span style="color:{dc};font-weight:600;font-size:12px;text-transform:uppercase;">{sig.get('direction','')}</span>
                  <p style="color:#e8e6e3;font-size:14px;margin:4px 0;">{sig.get('signal','')}</p>
                </div>'''

    elif mode == "news":
        headline = analysis.get("headline", "")
        if headline:
            articles_html += f'<div style="padding:16px;background:#1a1a2e;border-radius:8px;margin-bottom:20px;"><p style="color:#a78bfa;font-size:16px;font-weight:600;margin:0;">{headline}</p></div>'

        for section in analysis.get("sections", []):
            articles_html += f'<h2 style="color:#60a5fa;font-size:16px;margin:24px 0 8px;">{section.get("topic_label","")}</h2>'
            for item in section.get("articles", []):
                articles_html += f'''
                <div style="padding:10px 0;border-bottom:1px solid #2a2a30;">
                  <a href="{item.get('url','')}" style="color:#e8e6e3;text-decoration:none;font-weight:500;font-size:14px;">{item.get('title','')}</a>
                  <p style="color:#9a9a9f;font-size:13px;margin:4px 0 0;">{item.get('summary_short','')}</p>
                  <span style="color:#5a5a60;font-size:12px;">{item.get('source','')}</span>
                </div>'''

    elif mode in ("weekly_trends", "weekly_digest"):
        summary = analysis.get("executive_summary") or analysis.get("week_summary", "")
        if summary:
            articles_html += f'<div style="padding:16px;background:#1a1a2e;border-radius:8px;margin-bottom:20px;"><p style="color:#e8e6e3;font-size:14px;line-height:1.7;margin:0;">{summary}</p></div>'

        top = analysis.get("top_stories") or analysis.get("leaderboard", [])
        if top:
            articles_html += '<h2 style="color:#fbbf24;font-size:18px;margin:24px 0 12px;">Top of the week</h2>'
            for item in top[:10]:
                name = item.get("title") or item.get("tool_name", "")
                detail = item.get("why_top") or item.get("trend", "")
                articles_html += f'''
                <div style="padding:10px 0;border-bottom:1px solid #2a2a30;">
                  <span style="color:#fbbf24;font-weight:700;margin-right:8px;">#{item.get('rank','')}</span>
                  <span style="color:#e8e6e3;font-weight:500;">{name}</span>
                  <p style="color:#9a9a9f;font-size:13px;margin:4px 0 0;">{detail}</p>
                </div>'''

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,system-ui,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:32px 24px;">
  <div style="text-align:center;margin-bottom:32px;">
    <h1 style="color:#e8e6e3;font-size:24px;margin:0;">{title}</h1>
    <p style="color:#5a5a60;font-size:13px;margin:6px 0 0;">{date_str}</p>
  </div>
  {articles_html}
  <div style="margin-top:32px;text-align:center;padding-top:20px;border-top:1px solid #2a2a30;">
    <p style="color:#5a5a60;font-size:12px;">AI Digest Agent · Powered by Gemini + Claude</p>
  </div>
</div>
</body>
</html>'''
