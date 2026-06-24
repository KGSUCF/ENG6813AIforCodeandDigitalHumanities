"""
Lincoln Corpus Downloader
=========================
Run this script on your LOCAL machine (not in a cloud environment)
to download Lincoln speech texts from UCSB and the University of Michigan
Collected Works.

Usage:
    python download_speeches.py [--output ../speeches] [--delay 2]

Requirements:
    pip install requests beautifulsoup4

The script reads corpus_index.csv, fetches each speech that is not yet
in the corpus (in_corpus != 'yes'), and saves it as a .txt file.
"""

import csv
import os
import re
import time
import argparse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies first:  pip install requests beautifulsoup4")
    raise

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ──────────────────────────────────────────────────────────────────────────────
# Site-specific scrapers
# ──────────────────────────────────────────────────────────────────────────────

def scrape_ucsb(url: str, session: requests.Session) -> str | None:
    """Fetch a speech from presidency.ucsb.edu."""
    resp = session.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    # The speech body lives in <div class="field-docs-content"> or
    # <div class="field-item even">
    for selector in [
        "div.field-docs-content",
        "div.field-item.even",
        "div#transcript",
    ]:
        div = soup.select_one(selector)
        if div:
            return div.get_text(separator="\n").strip()
    return None


def scrape_umich(url: str, session: requests.Session) -> str | None:
    """Fetch a speech from quod.lib.umich.edu/l/lincoln."""
    resp = session.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    # Main text body
    for selector in ["div#text", "div.text", "div.bodytext", "body"]:
        div = soup.select_one(selector)
        if div:
            text = div.get_text(separator="\n").strip()
            if len(text) > 200:
                return text
    return None


def scrape_generic(url: str, session: requests.Session) -> str | None:
    """Fallback: grab the largest text block on the page."""
    resp = session.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n").strip()


def fetch_speech(url: str, session: requests.Session) -> str | None:
    if not url:
        return None
    if "presidency.ucsb.edu" in url:
        return scrape_ucsb(url, session)
    if "quod.lib.umich.edu" in url:
        return scrape_umich(url, session)
    return scrape_generic(url, session)


# ──────────────────────────────────────────────────────────────────────────────
# Filename helpers
# ──────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60]


def make_filename(row: dict) -> str:
    date = row["date"] or "0000-00-00"
    slug = slugify(row["title"])
    return f"{date}_{slug}.txt"


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download Lincoln corpus speeches")
    parser.add_argument("--output", default="../speeches", help="Output directory for .txt files")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests")
    parser.add_argument("--index", default="../metadata/corpus_index.csv", help="Path to corpus_index.csv")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = Path(args.index).resolve()

    with open(index_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    session = requests.Session()
    downloaded = 0
    skipped = 0
    failed = []

    for row in rows:
        speech_id = row["id"]
        title = row["title"]
        already = row.get("in_corpus", "").strip().lower() == "yes"
        url = row.get("source_url", "").strip()

        if already:
            skipped += 1
            continue

        filename = row.get("filename") or make_filename(row)
        dest = out_dir / filename

        if args.skip_existing and dest.exists():
            print(f"  [skip]  {filename}")
            skipped += 1
            continue

        if not url:
            print(f"  [no url] {speech_id}: {title}")
            failed.append((speech_id, title, "no source URL"))
            continue

        print(f"  [{speech_id}] {title[:60]}...", end=" ", flush=True)
        try:
            text = fetch_speech(url, session)
        except Exception as exc:
            print(f"ERROR: {exc}")
            failed.append((speech_id, title, str(exc)))
            time.sleep(args.delay)
            continue

        if not text or len(text) < 100:
            print("EMPTY/SHORT — skipping")
            failed.append((speech_id, title, "empty or too short"))
            time.sleep(args.delay)
            continue

        header = (
            f"TITLE: {title}\n"
            f"DATE: {row['date']}\n"
            f"LOCATION: {row.get('location', '')}\n"
            f"TYPE: {row.get('type', '')}\n"
            f"TOPICS: {row.get('topics', '')}\n"
            f"SOURCE: {url}\n"
            f"{'=' * 60}\n\n"
        )

        dest.write_text(header + text, encoding="utf-8")
        print(f"saved ({len(text):,} chars)")
        downloaded += 1
        time.sleep(args.delay)

    print(f"\n{'─'*50}")
    print(f"Downloaded : {downloaded}")
    print(f"Skipped    : {skipped}")
    print(f"Failed     : {len(failed)}")
    if failed:
        print("\nFailed items:")
        for fid, ftitle, reason in failed:
            print(f"  {fid}: {ftitle[:55]}  [{reason}]")


if __name__ == "__main__":
    main()
