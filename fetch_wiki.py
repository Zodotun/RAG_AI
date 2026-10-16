"""Download WARFRAME Wiki articles as clean text into data/wiki/.

Polite by design (see docs/warframe-wiki-data.md):
  - only fetches normal article URLs (/w/<Title>), which robots.txt allows; never api.php or ?action=
  - one request at a time, REQUEST_DELAY seconds apart, with a User-Agent naming this project
  - skips pages already on disk, so an interrupted run picks up where it stopped

Examples:
  python fetch_wiki.py                                  # default starter slice (see DEFAULT_CATEGORIES)
  python fetch_wiki.py --category Warframes --limit 20
  python fetch_wiki.py --title Excalibur --title "Braton Prime"
"""
import argparse
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup

from wiki_text import html_to_text

BASE = "https://wiki.warframe.com"
USER_AGENT = "RAG_AI_TCG/0.1 (student AI club project; https://github.com/Zodotun/RAG_AI_TCG)"
REQUEST_DELAY = 1.0  # seconds between requests
OUT_DIR = Path("data/wiki")

# Starter slice: enough to ask real questions without a 3-hour full download.
DEFAULT_CATEGORIES = ["Warframes", "Warframe Abilities", "Primary Weapons", "Secondary Weapons", "Melee Weapons"]

# Members in these namespaces aren't articles.
SKIP_PREFIXES = ("File:", "Category:", "Template:", "Module:", "User:", "Special:", "Talk:", "Help:",
                 "Bucket:", "WARFRAME Wiki:", "Conclave:")  # Conclave = PvP variants, mostly noise

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
_last_request = 0.0


def get(url):
    """GET with a fixed delay between requests and backoff on 429/5xx."""
    global _last_request
    for attempt in range(5):
        wait = REQUEST_DELAY - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        resp = session.get(url, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = int(resp.headers.get("Retry-After", 0)) or 10 * (attempt + 1)
            print(f"  {resp.status_code} from server, waiting {delay}s")
            time.sleep(delay)
            continue
        return resp
    resp.raise_for_status()
    return resp


def page_url(title):
    return f"{BASE}/w/{quote(title.replace(' ', '_'), safe='/:()_,-')}"


def safe_filename(title):
    return re.sub(r'[<>:"/\\|?*]', "_", title).strip(". ") + ".md"


def category_members(category):
    """All article titles in a category, following the category's 'next page' links."""
    url, titles = page_url(f"Category:{category}"), []
    while url:
        resp = get(url)
        if resp.status_code == 404:
            print(f"Category not found: {category}")
            return titles
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        pages = soup.select_one("#mw-pages")
        if pages is None:
            break
        for a in pages.select(".mw-category a[title]"):
            title = a["title"]
            if not title.startswith(SKIP_PREFIXES):
                titles.append(title)
        nxt = next((a for a in pages.find_all("a", href=True) if a.get_text(strip=True) == "next page"), None)
        url = urljoin(BASE, nxt["href"]) if nxt else None
    return titles


def fetch_page(title, refresh=False):
    """Download one article. Returns 'saved', 'skipped' or 'missing'."""
    out = OUT_DIR / safe_filename(title)
    if out.exists() and not refresh:
        return "skipped"
    resp = get(page_url(title))
    if resp.status_code == 404:
        return "missing"
    resp.raise_for_status()

    # Redirects land on the canonical page; record that title so citations point at the real article.
    canonical = BeautifulSoup(resp.text, "html.parser").select_one('link[rel="canonical"]')
    url = canonical["href"] if canonical else page_url(title)
    real_title = unquote(url.rsplit("/w/", 1)[-1]).replace("_", " ")

    text, info = html_to_text(resp.text)
    header = [f"title: {real_title}", f"url: {url}"]
    header += [f"{k}: {v}" for k, v in info.items()]
    out.write_text("---\n" + "\n".join(header) + "\n---\n\n" + text + "\n", encoding="utf-8")
    return "saved"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", action="append", help="wiki category to download (repeatable)")
    ap.add_argument("--title", action="append", help="single article title to download (repeatable)")
    ap.add_argument("--limit", type=int, help="max articles per category")
    ap.add_argument("--refresh", action="store_true", help="re-download pages already on disk")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    titles = list(args.title or [])
    if not args.title or args.category:
        for cat in args.category or DEFAULT_CATEGORIES:
            members = category_members(cat)
            print(f"Category:{cat} -> {len(members)} articles")
            titles += members[: args.limit] if args.limit else members
    titles = list(dict.fromkeys(titles))  # dedupe, keep order

    counts = {"saved": 0, "skipped": 0, "missing": 0, "failed": 0}
    for i, title in enumerate(titles, 1):
        try:
            result = fetch_page(title, args.refresh)
        except requests.RequestException as e:
            result = "failed"
            print(f"  failed: {title}: {e}")
        counts[result] += 1
        if result != "skipped":
            print(f"[{i}/{len(titles)}] {result}: {title}")
    print("Done:", ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
