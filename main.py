#!/usr/bin/env python3
"""
AI Digest Agent — Main Entry Point
Runs via GitHub Actions cron. Modes: trends, news, weekly_trends, weekly_digest
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.fetchers.rss_fetcher import fetch_rss_feeds
from src.fetchers.hn_fetcher import fetch_hacker_news
from src.fetchers.github_fetcher import fetch_github_trending
from src.processors.gemini_pass import gemini_compress
from src.processors.claude_pass import claude_analyze
from src.processors.taxonomy_updater import update_taxonomy
from src.deliverers.notion_deliverer import push_to_notion
from src.deliverers.sheets_deliverer import push_to_sheets
from src.deliverers.email_deliverer import send_email_digest
from src.deliverers.telegram_deliverer import send_telegram_digest
from src.deliverers.drive_deliverer import upload_pdf_to_drive
from src.formatters.email_formatter import format_email_html
from src.formatters.telegram_formatter import format_telegram_message
from src.formatters.pdf_formatter import generate_pdf
from src.formatters.markdown_formatter import format_markdown_archive

IST = timezone(timedelta(hours=5, minutes=30))
log = setup_logger("agent")


def parse_args():
    parser = argparse.ArgumentParser(description="AI Digest Agent")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["trends", "news", "weekly_trends", "weekly_digest"],
        help="Run mode"
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip delivery, print output")
    return parser.parse_args()


async def run_daily_pipeline(mode: str, config: dict, dry_run: bool = False):
    """Daily pipeline: fetch → Gemini compress → Claude analyze → store → deliver"""
    now = datetime.now(IST)
    log.info(f"Starting daily {mode} run at {now.strftime('%Y-%m-%d %H:%M IST')}")

    # ── Stage 1: Fetch raw articles ──
    log.info("Stage 1: Fetching raw articles...")
    raw_articles = []

    rss_articles = await fetch_rss_feeds(config["sources"]["rss_feeds"])
    raw_articles.extend(rss_articles)
    log.info(f"  RSS: {len(rss_articles)} articles")

    if config["sources"]["apis"]["hacker_news"]["enabled"]:
        hn_articles = await fetch_hacker_news(config["sources"]["apis"]["hacker_news"])
        raw_articles.extend(hn_articles)
        log.info(f"  HN: {len(hn_articles)} articles")

    if config["sources"]["apis"]["github_trending"]["enabled"]:
        gh_articles = await fetch_github_trending(config["sources"]["apis"]["github_trending"])
        raw_articles.extend(gh_articles)
        log.info(f"  GitHub: {len(gh_articles)} articles")

    log.info(f"Total raw articles: {len(raw_articles)}")

    if not raw_articles:
        log.warning("No articles fetched. Exiting.")
        return

    # ── Stage 2: Gemini Pass 1 — Compression ──
    log.info("Stage 2: Gemini Pass 1 — compressing articles...")
    compressed = await gemini_compress(raw_articles, config)
    log.info(f"Compressed to {len(compressed)} structured items")

    # ── Stage 3: Claude Pass 2 — Intelligence ──
    log.info(f"Stage 3: Claude Pass 2 — analyzing ({mode} mode)...")
    analysis = await claude_analyze(compressed, mode, config)
    log.info("Analysis complete")

    # ── Stage 4: Taxonomy feedback ──
    if analysis.get("taxonomy_proposals"):
        log.info(f"Taxonomy proposals: {len(analysis['taxonomy_proposals'])} changes")
        if not dry_run:
            update_taxonomy(analysis["taxonomy_proposals"], config)

    # ── Stage 5: Store ──
    if not dry_run:
        log.info("Stage 5: Storing results...")
        await push_to_notion(analysis, mode, config)
        await push_to_sheets(analysis, mode, config)

        # Archive markdown
        archive_path = Path("data/archive") / now.strftime("%Y-%m-%d")
        archive_path.mkdir(parents=True, exist_ok=True)
        md_content = format_markdown_archive(analysis, mode)
        (archive_path / f"{mode}.md").write_text(md_content)
        log.info("  Stored to Notion, Sheets, and archive")

    # ── Stage 6: Format & Deliver ──
    log.info("Stage 6: Formatting and delivering...")
    if not dry_run:
        # Email
        if config["delivery"]["email"]["enabled"]:
            html = format_email_html(analysis, mode)
            await send_email_digest(html, mode, config)
            log.info("  Email sent")

        # Telegram
        if config["delivery"]["telegram"]["enabled"]:
            tg_msg = format_telegram_message(analysis, mode)
            await send_telegram_digest(tg_msg, config)
            log.info("  Telegram sent")
    else:
        print(json.dumps(analysis, indent=2, default=str))

    log.info(f"Daily {mode} run complete.")
    return analysis


async def run_weekly_pipeline(mode: str, config: dict, dry_run: bool = False):
    """
    Weekly pipeline (Sunday):
    1. Run normal daily pipeline first (to capture Sunday's articles)
    2. Read Mon-Sun data from storage
    3. Claude aggregates into weekly report
    4. Generate PDF for NotebookLM
    5. Deliver
    """
    now = datetime.now(IST)
    daily_mode = "trends" if mode == "weekly_trends" else "news"
    log.info(f"Starting weekly {mode} run at {now.strftime('%Y-%m-%d %H:%M IST')}")

    # ── Step 1: Run Sunday's daily pipeline first ──
    log.info("Step 1: Processing Sunday's articles first...")
    await run_daily_pipeline(daily_mode, config, dry_run)

    # ── Step 2: Read week's stored data ──
    log.info("Step 2: Reading Mon-Sun stored data...")
    # In production, this queries Notion DB or Sheets for the past 7 days
    # For now, we read from the archive
    week_start = now - timedelta(days=6)
    week_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_path = Path("data/archive") / day.strftime("%Y-%m-%d") / f"{daily_mode}.md"
        if day_path.exists():
            week_data.append(day_path.read_text())

    # ── Step 3: Claude aggregates ──
    log.info("Step 3: Claude aggregating weekly report...")
    weekly_analysis = await claude_analyze(
        week_data, mode, config, is_weekly=True
    )

    # ── Step 4: Generate PDF for NotebookLM ──
    if mode == "weekly_digest" and not dry_run:
        log.info("Step 4: Generating NotebookLM-optimized PDF...")
        pdf_path = generate_pdf(weekly_analysis, config)

        if config["delivery"]["google_drive"]["enabled"]:
            await upload_pdf_to_drive(pdf_path, config)
            log.info("  PDF uploaded to Google Drive")

    # ── Step 5: Deliver ──
    if not dry_run:
        log.info("Step 5: Delivering weekly report...")
        await push_to_notion(weekly_analysis, mode, config)
        await push_to_sheets(weekly_analysis, mode, config)

        if config["delivery"]["email"]["enabled"]:
            html = format_email_html(weekly_analysis, mode)
            await send_email_digest(html, mode, config)

        if config["delivery"]["telegram"]["enabled"]:
            tg_msg = format_telegram_message(weekly_analysis, mode)
            await send_telegram_digest(tg_msg, config)
            # Sunday: also send Drive link reminder for NotebookLM
            if mode == "weekly_digest":
                folder_id = config["delivery"]["google_drive"]["folder_id"]
                reminder = (
                    "Your weekly digest PDF is ready in Google Drive.\n"
                    f"Open NotebookLM and generate your audio podcast."
                )
                await send_telegram_digest(reminder, config)
    else:
        print(json.dumps(weekly_analysis, indent=2, default=str))

    log.info(f"Weekly {mode} run complete.")


async def main():
    args = parse_args()
    config = load_config()

    if args.mode in ("trends", "news"):
        await run_daily_pipeline(args.mode, config, args.dry_run)
    elif args.mode in ("weekly_trends", "weekly_digest"):
        await run_weekly_pipeline(args.mode, config, args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
