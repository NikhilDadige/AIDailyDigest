"""PDF formatter — generates NotebookLM-optimized PDF using reportlab"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict

IST = timezone(timedelta(hours=5, minutes=30))


def generate_pdf(analysis: Dict, config: dict) -> str:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.units import inch
    except ImportError:
        print("  Warning: reportlab not installed, skipping PDF generation")
        return ""

    now = datetime.now(IST)
    mode = analysis.get("mode", "weekly_digest")
    filename = f"ai_digest_{now.strftime('%Y_%m_%d')}_{mode}.pdf"
    output_path = Path("data") / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                                  fontSize=22, spaceAfter=12, textColor=HexColor('#1a1a2e'))
    h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'],
                               fontSize=16, spaceAfter=8, spaceBefore=16, textColor=HexColor('#4a3d8f'))
    body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                                 fontSize=11, leading=16, spaceAfter=6)
    item_style = ParagraphStyle('CustomItem', parent=styles['Normal'],
                                 fontSize=11, leading=15, spaceAfter=4, leftIndent=12)

    story = []
    title = "Weekly AI Digest" if "weekly" in mode else "AI Trend Report"
    story.append(Paragraph(f"{title} — {now.strftime('%B %d, %Y')}", title_style))
    story.append(Spacer(1, 12))

    # Executive summary (important for NotebookLM to latch onto)
    summary = analysis.get("executive_summary") or analysis.get("week_summary", "")
    if summary:
        story.append(Paragraph("Executive summary", h2_style))
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 8))

    # Top stories
    top = analysis.get("top_stories") or analysis.get("top_picks", [])
    if top:
        story.append(Paragraph("Top stories of the week", h2_style))
        for item in top[:7]:
            title_text = item.get("title", "")
            why = item.get("why_top") or item.get("why_important", "")
            score = item.get("impact_score", "")
            story.append(Paragraph(
                f"<b>{title_text}</b> (Impact: {score}/10)<br/>{why}",
                item_style
            ))
        story.append(Spacer(1, 8))

    # Category summaries (great for NotebookLM's section detection)
    cats = analysis.get("by_category") or analysis.get("category_activity", {})
    if isinstance(cats, list):
        story.append(Paragraph("Category breakdown", h2_style))
        for cat in cats:
            label = cat.get("topic_label") or cat.get("main_topic", "")
            cat_summary = cat.get("week_summary") or cat.get("notable", "")
            story.append(Paragraph(f"<b>{label}</b>: {cat_summary}", item_style))
    elif isinstance(cats, dict):
        story.append(Paragraph("Category activity", h2_style))
        for cat_id, data in cats.items():
            notable = data.get("notable", "")
            count = data.get("article_count", 0)
            story.append(Paragraph(f"<b>{cat_id}</b> ({count} articles): {notable}", item_style))

    # Notable launches
    launches = analysis.get("notable_launches") or analysis.get("launches", [])
    if launches:
        story.append(Paragraph("Notable launches", h2_style))
        for launch in launches[:10]:
            name = launch.get("name", "")
            what = launch.get("what", "")
            story.append(Paragraph(f"<b>{name}</b>: {what}", item_style))

    # What you missed
    missed = analysis.get("what_you_missed", [])
    if missed:
        story.append(Paragraph("What you might have missed", h2_style))
        for item in missed:
            title_text = item.get("title", "")
            why = item.get("why", "")
            story.append(Paragraph(f"<b>{title_text}</b>: {why}", item_style))

    # Leaderboard (for weekly trends)
    leaderboard = analysis.get("leaderboard", [])
    if leaderboard:
        story.append(Paragraph("Weekly leaderboard", h2_style))
        for item in leaderboard[:15]:
            rank = item.get("rank", "")
            name = item.get("tool_name", "")
            mentions = item.get("mentions", 0)
            trend = item.get("trend", "")
            story.append(Paragraph(
                f"#{rank} <b>{name}</b> — {mentions} mentions ({trend})", item_style
            ))

    doc.build(story)
    return str(output_path)
