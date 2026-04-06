"""GitHub trending fetcher — scrapes trending repos filtered by AI keywords"""
import asyncio
import hashlib
import re
from typing import Dict, List
from urllib.request import urlopen, Request


async def fetch_github_trending(config: Dict) -> List[Dict]:
    keywords = [k.lower() for k in config.get("filter_keywords", [])]
    max_repos = config.get("max_repos", 10)
    languages = config.get("languages", ["python"])

    articles = []
    for lang in languages:
        try:
            url = f"https://github.com/trending/{lang}?since=daily"
            req = Request(url, headers={"User-Agent": "AI-Digest-Agent/1.0"})
            html = await asyncio.to_thread(lambda: urlopen(req, timeout=15).read().decode())

            repo_pattern = r'href="(/[^/]+/[^"]+)"[^>]*>\s*<span[^>]*>([^<]*)</span>\s*/\s*<span[^>]*>([^<]*)</span>'
            desc_pattern = r'<p class="col-9[^"]*">\s*([^<]+?)\s*</p>'
            repos = re.findall(repo_pattern, html)
            descs = re.findall(desc_pattern, html)

            for i, (path, owner, name) in enumerate(repos[:20]):
                full_name = f"{owner.strip()}/{name.strip()}"
                repo_url = f"https://github.com{path.strip()}"
                desc = descs[i].strip() if i < len(descs) else ""

                check_text = f"{full_name} {desc}".lower()
                if not any(kw in check_text for kw in keywords):
                    continue

                article_id = hashlib.md5(repo_url.encode()).hexdigest()[:12]
                articles.append({
                    "id": article_id,
                    "title": f"[GitHub Trending] {full_name}",
                    "url": repo_url,
                    "source": f"GitHub Trending ({lang})",
                    "source_type": "github",
                    "category_hint": "open_source_models",
                    "published": None,
                    "raw_summary": desc[:500] if desc else f"Trending {lang} repository: {full_name}",
                })

                if len(articles) >= max_repos:
                    break
        except Exception as e:
            print(f"  Warning: Failed to fetch GitHub trending for {lang}: {e}")
            continue

    return articles[:max_repos]
