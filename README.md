# AI Digest Agent

Autonomous, serverless AI ecosystem monitoring agent. Scans 14 main topics, 52+ sub-topics across the entire AI landscape. Delivers daily trend reports, newsletters, and weekly digests — with zero machines running.

## Architecture

```
RSS/APIs/GitHub → Gemini Flash (free) → Claude Sonnet ($) → Notion + Sheets + Email + Telegram + NotebookLM PDF
                   compress & tag         rank & analyze      store & deliver
```

**Two-pass pipeline:**
- **Pass 1 (Gemini 2.5 Flash):** Compresses raw articles into structured JSON. Free tier.
- **Pass 2 (Claude Sonnet 4.6):** Ranks, detects trends, generates insights. ~₹300/month.

## Schedule (IST)

| Day | 8:00 PM | 10:00 PM |
|-----|---------|----------|
| Mon–Sat | Daily trend report | Daily newsletter |
| Sunday | Weekly trend report | Weekly digest + NotebookLM PDF |

## Quick Setup (~30 minutes)

### 1. Fork this repo

### 2. Get API keys

| Service | Where | Cost |
|---------|-------|------|
| Anthropic API | [console.anthropic.com](https://console.anthropic.com) | Pay-as-you-go ($5 free credits) |
| Gemini API | [ai.google.dev](https://ai.google.dev) | Free |
| Notion integration | [developers.notion.com](https://developers.notion.com) | Free |
| Resend | [resend.com](https://resend.com) | Free (100 emails/day) |
| Telegram bot | Message @BotFather on Telegram | Free |
| Google Sheets API | [console.cloud.google.com](https://console.cloud.google.com) | Free |
| Google Drive API | Same GCP project | Free |

### 3. Set up Notion

1. Create a new database with these properties:
   - **Title** (title)
   - **URL** (url)
   - **Source** (select)
   - **Primary Tag** (select)
   - **Secondary Tags** (multi-select)
   - **Main Topic** (select)
   - **Impact Score** (number)
   - **Content Type** (select)
   - **Summary** (rich text)
   - **Tools Mentioned** (multi-select)
   - **Date** (date)

2. Create a Notion integration and share the database with it.

3. Create two parent pages: "Daily Digests" and "Weekly Digests" — share both with the integration.

### 4. Add GitHub Secrets

Go to your repo → Settings → Secrets → Actions → New repository secret.

Add each of these:
```
GEMINI_API_KEY
ANTHROPIC_API_KEY
NOTION_API_KEY
NOTION_DATABASE_ID
NOTION_DAILY_PARENT_ID
NOTION_WEEKLY_PARENT_ID
GOOGLE_SHEETS_API_KEY
GOOGLE_SHEETS_ID
RESEND_API_KEY
EMAIL_TO
EMAIL_FROM
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
GOOGLE_DRIVE_API_KEY
GDRIVE_FOLDER_ID
```

### 5. Test manually

Go to Actions tab → "Daily AI Digest" → "Run workflow" → select mode → Run.

## Self-Evolving Taxonomy

The agent automatically proposes taxonomy changes:
- **New categories** when articles don't fit existing ones
- **Stale flags** when a category has zero articles for 30+ days
- **Merge suggestions** when two categories converge

Changes are committed to `config.yaml` automatically. Review them in your git history.

## Project Structure

```
ai-digest-agent/
├── main.py                          # Entry point
├── config.yaml                      # Taxonomy + sources + settings
├── requirements.txt
├── .github/workflows/
│   ├── daily.yml                    # Mon-Sat cron (8 PM + 10 PM IST)
│   └── weekly.yml                   # Sunday cron (8 PM + 10 PM IST)
├── src/
│   ├── fetchers/
│   │   ├── rss_fetcher.py           # RSS feed parser
│   │   ├── hn_fetcher.py            # Hacker News API
│   │   └── github_fetcher.py        # GitHub trending scraper
│   ├── processors/
│   │   ├── gemini_pass.py           # Pass 1: compression via Gemini
│   │   ├── claude_pass.py           # Pass 2: analysis via Claude
│   │   └── taxonomy_updater.py      # Auto-evolve config.yaml
│   ├── formatters/
│   │   ├── email_formatter.py       # HTML email templates
│   │   ├── telegram_formatter.py    # Telegram message format
│   │   ├── pdf_formatter.py         # NotebookLM-optimized PDF
│   │   └── markdown_formatter.py    # Archive markdown
│   ├── deliverers/
│   │   ├── notion_deliverer.py      # Notion API integration
│   │   ├── sheets_deliverer.py      # Google Sheets API
│   │   ├── email_deliverer.py       # Resend API
│   │   ├── telegram_deliverer.py    # Telegram Bot API
│   │   └── drive_deliverer.py       # Google Drive upload
│   └── utils/
│       ├── config.py                # YAML loader + env resolver
│       └── logger.py                # Logging setup
└── data/
    └── archive/                     # Daily markdown archives
```

## Cost

| Component | Monthly Cost |
|-----------|-------------|
| GitHub Actions | ₹0 |
| Gemini API | ₹0 |
| Claude API | ~₹300 |
| Notion API | ₹0 |
| Google Sheets | ₹0 |
| Email (Resend) | ₹0 |
| Telegram | ₹0 |
| Google Drive | ₹0 |
| **Total** | **~₹300/month (~$3.60)** |

## License

MIT
