#!/usr/bin/env python3
"""AI Digest Agent v2 — Claude-only pipeline"""
import argparse, asyncio, json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.fetchers.rss_fetcher import fetch_rss_feeds
from src.fetchers.hn_fetcher import fetch_hacker_news
from src.fetchers.github_fetcher import fetch_github_trending
from src.processors.taxonomy_updater import update_taxonomy
from src.deliverers.notion_deliverer import push_to_notion
from src.processors.claude_pass import claude_analyze
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


async def run_daily_pipeline(mode, config, dry_run=False):
    now = datetime.now(IST)
    log.info(f"Starting daily {mode} run at {now.strftime('%Y-%m-%d %H:%M IST')}")

    log.info("Stage 1: Fetching raw articles...")
    raw_articles = []

    rss = await fetch_rss_feeds(config["sources"]["rss_feeds"])
    raw_articles.extend(rss)
    log.info(f"  RSS: {len(rss)} articles")

    if config["sources"]["apis"]["hacker_news"]["enabled"]:
        hn = await fetch_hacker_news(config["sources"]["apis"]["hacker_news"])
        raw_articles.extend(hn)
        log.info(f"  HN: {len(hn)} articles")

    if config["sources"]["apis"]["github_trending"]["enabled"]:
        gh = await fetch_github_trending(config["sources"]["apis"]["github_trending"])
        raw_articles.extend(gh)
        log.info(f"  GitHub: {len(gh)} articles")

    log.info(f"Total raw articles: {len(raw_articles)}")
    if not raw_articles:
        log.warning("No articles fetched. Exiting.")
        return

    # ── Claude analysis (NO Gemini) ──
    log.info(f"Stage 2: Claude analyzing ({mode} mode)...")
    analysis = await claude_analyze(raw_articles, mode, config)
    log.info("Analysis complete")

    if analysis.get("taxonomy_proposals"):
        update_taxonomy(analysis["taxonomy_proposals"], config)

    if not dry_run:
        log.info("Stage 3: Storing & delivering...")
        await push_to_notion(analysis, mode, config)
        await push_to_sheets(analysis, mode, config)

        archive_path = Path("data/archive") / now.strftime("%Y-%m-%d")
        archive_path.mkdir(parents=True, exist_ok=True)
        (archive_path / f"{mode}.md").write_text(format_markdown_archive(analysis, mode))

        if config["delivery"]["email"]["enabled"]:
            html = format_email_html(analysis, mode)
            await send_email_digest(html, mode, config)
            log.info("  Email sent")

        if config["delivery"]["telegram"]["enabled"]:
            await send_telegram_digest(format_telegram_message(analysis, mode), config)
    else:
        print(json.dumps(analysis, indent=2, default=str))

    log.info(f"Daily {mode} run complete.")
    return analysis


async def run_weekly_pipeline(mode, config, dry_run=False):
    now = datetime.now(IST)
    daily_mode = "trends" if mode == "weekly_trends" else "news"
    log.info(f"Starting weekly {mode} run")

    log.info("Step 1: Processing Sunday's articles...")
    await run_daily_pipeline(daily_mode, config, dry_run)

    log.info("Step 2: Reading stored week data...")
    week_data = []
    for i in range(7):
        day = now - timedelta(days=6-i)
        p = Path("data/archive") / day.strftime("%Y-%m-%d") / f"{daily_mode}.md"
        if p.exists():
            week_data.append(p.read_text())

    if not week_data:
        p = Path("data/archive") / now.strftime("%Y-%m-%d") / f"{daily_mode}.md"
        if p.exists():
            week_data = [p.read_text()]

    log.info("Step 3: Claude weekly aggregation...")
    weekly = await claude_analyze(week_data, mode, config, is_weekly=True)

    if mode == "weekly_digest" and not dry_run:
        pdf_path = generate_pdf(weekly, config)
        if pdf_path and config["delivery"]["google_drive"]["enabled"]:
            await upload_pdf_to_drive(pdf_path, config)

    if not dry_run:
        await push_to_notion(weekly, mode, config)
        await push_to_sheets(weekly, mode, config)
        if config["delivery"]["email"]["enabled"]:
            await send_email_digest(format_email_html(weekly, mode), mode, config)

    log.info(f"Weekly {mode} complete.")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["trends","news","weekly_trends","weekly_digest"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config()

    if args.mode in ("trends", "news"):
        await run_daily_pipeline(args.mode, config, args.dry_run)
    else:
        await run_weekly_pipeline(args.mode, config, args.dry_run)

if __name__ == "__main__":
    asyncio.run(main())
