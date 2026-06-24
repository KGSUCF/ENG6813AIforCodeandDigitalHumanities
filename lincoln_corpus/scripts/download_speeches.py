"""
Lincoln Corpus Downloader
=========================
Run this script on your LOCAL machine to download Lincoln speech texts
from UCSB and the University of Michigan Collected Works.

REQUIREMENTS: Python 3.6 or later — NO additional installs needed.
This script uses only Python's built-in standard library.

HOW TO RUN:
  1. Open a terminal (Mac: Terminal app; Windows: Command Prompt or PowerShell)
  2. Navigate to the scripts folder, e.g.:
       cd Desktop/ENG6813AIforCodeandDigitalHumanities/lincoln_corpus/scripts
  3. Run:
       python download_speeches.py

Speeches will be saved to the speeches/ folder one level up.
"""

import csv
import os
import re
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from html.parser import HTMLParser


# ──────────────────────────────────────────────────────────────────────────────
# Minimal HTML text extractor (no third-party libraries needed)
# ──────────────────────────────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """Extract plain text from HTML, skipping scripts/styles/nav."""

    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self):
        raw = " ".join(self._parts)
        # Collapse whitespace
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r"[ \t]+", " ", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return p.get_text()


# ──────────────────────────────────────────────────────────────────────────────
# Target content extraction — pull the main speech body from each site
# ──────────────────────────────────────────────────────────────────────────────

def extract_ucsb(html: str) -> str:
    """Pull speech body from presidency.ucsb.edu HTML."""
    # The speech text lives between specific div markers
    for pattern in [
        r'class="field-docs-content"[^>]*>(.*?)</div>',
        r'id="transcript"[^>]*>(.*?)</div>',
        r'class="field-item even"[^>]*>(.*?)</div>',
    ]:
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m:
            return html_to_text(m.group(1))
    # Fallback: strip all HTML
    return html_to_text(html)


def extract_umich(html: str) -> str:
    """Pull speech body from quod.lib.umich.edu Lincoln pages."""
    for pattern in [
        r'<div[^>]+id="text"[^>]*>(.*?)</div>',
        r'<div[^>]+class="[^"]*bodytext[^"]*"[^>]*>(.*?)</div>',
    ]:
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m:
            text = html_to_text(m.group(1))
            if len(text) > 200:
                return text
    return html_to_text(html)


def fetch_url(url: str) -> str | None:
    """Fetch a URL and return the decoded HTML body, or None on failure."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            # Try to detect encoding from headers or meta tag
            charset = "utf-8"
            ct = resp.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ct)
            if m:
                charset = m.group(1)
            return raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}", end=" ")
        return None
    except Exception as e:
        print(f"ERROR({e})", end=" ")
        return None


def fetch_speech(url: str) -> str | None:
    if not url:
        return None
    html = fetch_url(url)
    if not html:
        return None
    if "presidency.ucsb.edu" in url:
        return extract_ucsb(html)
    if "quod.lib.umich.edu" in url:
        return extract_umich(html)
    return html_to_text(html)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60]


def make_filename(row: dict) -> str:
    date = row.get("date") or "0000-00-00"
    slug = slugify(row.get("title", "untitled"))
    return f"{date}_{slug}.txt"


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download Lincoln corpus speeches — no extra installs needed"
    )
    parser.add_argument(
        "--output", default="../speeches",
        help="Folder to save .txt files (default: ../speeches)"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds to wait between requests (default: 2)"
    )
    parser.add_argument(
        "--index", default="../metadata/corpus_index.csv",
        help="Path to corpus_index.csv"
    )
    args = parser.parse_args()

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = Path(args.index).resolve()

    if not index_path.exists():
        print(f"Cannot find index file at: {index_path}")
        print("Make sure you are running this from the scripts/ folder.")
        return

    with open(index_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Index loaded: {len(rows)} speeches")
    print(f"Output folder: {out_dir}\n")

    downloaded, skipped, failed = 0, 0, []

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

        if dest.exists():
            print(f"  [exists] {filename}")
            skipped += 1
            continue

        if not url:
            print(f"  [no url] {speech_id}: {title[:55]}")
            failed.append((speech_id, title, "no source URL"))
            continue

        print(f"  [{speech_id}] {title[:55]}...", end=" ", flush=True)
        text = fetch_speech(url)

        if not text or len(text) < 100:
            print("empty/short — skipping")
            failed.append((speech_id, title, "empty or too short"))
            time.sleep(args.delay)
            continue

        header = (
            f"TITLE: {title}\n"
            f"DATE: {row.get('date', '')}\n"
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

    print(f"\n{'─' * 50}")
    print(f"Downloaded : {downloaded}")
    print(f"Skipped    : {skipped}  (already in corpus)")
    print(f"Failed     : {len(failed)}")
    if failed:
        print("\nFailed items:")
        for fid, ftitle, reason in failed:
            print(f"  {fid}: {ftitle[:55]}  [{reason}]")


if __name__ == "__main__":
    main()
