"""
Lincoln Corpus Downloader — Gutenberg Edition
==============================================
Downloads Lincoln's complete works from Project Gutenberg as plain text,
then splits them into individual speech files matched to corpus_index.csv.

REQUIREMENTS: Python 3.6 or later — NO additional installs needed.

HOW TO RUN (from your ABC/lincoln folder):
    python download_speeches.py

Project Gutenberg serves plain .txt files — no HTML scraping, no 403 errors.
"""

import csv
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Gutenberg plain-text volume URLs ─────────────────────────────────────────
# The Papers and Writings of Abraham Lincoln (7 volumes, edited by Lapsley)
GUTENBERG_VOLUMES = {
    1: "https://www.gutenberg.org/files/2653/2653-0.txt",  # 1832–1843
    2: "https://www.gutenberg.org/files/2654/2654-0.txt",  # 1843–1858
    3: "https://www.gutenberg.org/files/2655/2655-0.txt",  # 1858–1858
    4: "https://www.gutenberg.org/files/2656/2656-0.txt",  # 1858–1860
    5: "https://www.gutenberg.org/files/2657/2657-0.txt",  # 1858–1862
    6: "https://www.gutenberg.org/files/2658/2658-0.txt",  # 1862–1863
    7: "https://www.gutenberg.org/files/2659/2659-0.txt",  # 1863–1865
}

# Wikisource raw-text API for speeches with confirmed Wikisource pages
# (returns plain wikitext — easier to clean than HTML)
WIKISOURCE_OVERRIDES = {
    "LINC_004": "https://en.wikisource.org/w/index.php?title=Perpetuation_of_Our_Political_Institutions&action=raw",
    "LINC_018": "https://en.wikisource.org/w/index.php?title=House_Divided_Speech&action=raw",
    "LINC_038": "https://en.wikisource.org/w/index.php?title=Cooper_Union_address&action=raw",
    "LINC_044": "https://en.wikisource.org/w/index.php?title=Farewell_Address_at_Springfield&action=raw",
    "LINC_052": "https://en.wikisource.org/w/index.php?title=Abraham_Lincoln%27s_First_Inaugural_Address&action=raw",
    "LINC_064": "https://en.wikisource.org/w/index.php?title=Letter_to_Horace_Greeley_(August_22,_1862)&action=raw",
    "LINC_065": "https://en.wikisource.org/w/index.php?title=Preliminary_Emancipation_Proclamation&action=raw",
    "LINC_067": "https://en.wikisource.org/w/index.php?title=Emancipation_Proclamation&action=raw",
    "LINC_073": "https://en.wikisource.org/w/index.php?title=Proclamation_of_Thanksgiving_(1863)&action=raw",
    "LINC_074": "https://en.wikisource.org/w/index.php?title=Gettysburg_Address&action=raw",
    "LINC_087": "https://en.wikisource.org/w/index.php?title=Abraham_Lincoln%27s_Second_Inaugural_Address&action=raw",
    "LINC_089": "https://en.wikisource.org/w/index.php?title=Last_public_address_(Lincoln)&action=raw",
}

HEADERS = {
    "User-Agent": "Lincoln-Corpus-Builder/1.0 (academic research; python urllib)"
}

# ── HTTP fetch ────────────────────────────────────────────────────────────────

def fetch_text(url: str) -> str | None:
    """Fetch a URL and return decoded text, or None on failure."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            ct = resp.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ct)
            charset = m.group(1) if m else "utf-8"
            return raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}", end=" ")
    except Exception as e:
        print(f"ERROR({type(e).__name__})", end=" ")
    return None

# ── Wikitext cleaner ──────────────────────────────────────────────────────────

def clean_wikitext(wikitext: str) -> str:
    """Strip wikitext markup, leaving readable plain text."""
    t = wikitext
    # Remove templates {{...}}
    t = re.sub(r"\{\{[^}]*\}\}", "", t)
    # Remove [[File:...]] and [[Image:...]]
    t = re.sub(r"\[\[(File|Image):[^\]]*\]\]", "", t, flags=re.IGNORECASE)
    # Convert [[link|text]] → text, [[link]] → link
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    # Remove external links [url text] → text
    t = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", t)
    # Remove section headers ==...==
    t = re.sub(r"={2,}([^=]+)={2,}", r"\1", t)
    # Remove bold/italic markup
    t = re.sub(r"'{2,}", "", t)
    # Remove HTML tags
    t = re.sub(r"<[^>]+>", "", t)
    # Collapse blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# ── Gutenberg volume cache & parser ──────────────────────────────────────────

_volume_cache: dict[int, str] = {}

def get_volume(vol: int) -> str | None:
    """Download and cache a Gutenberg volume."""
    if vol in _volume_cache:
        return _volume_cache[vol]
    url = GUTENBERG_VOLUMES.get(vol)
    if not url:
        return None
    print(f"\n  [Gutenberg] Downloading Volume {vol}...", end=" ", flush=True)
    text = fetch_text(url)
    if text:
        print(f"({len(text):,} chars)")
        _volume_cache[vol] = text
    else:
        print("FAILED")
    return text


def find_in_gutenberg(title: str, date_str: str) -> str | None:
    """
    Search all Gutenberg volumes for a speech matching the title.
    Returns the speech text if found, None otherwise.
    """
    # Build search keywords from the title
    # Strip common words and punctuation
    stopwords = {"the", "a", "an", "of", "on", "at", "to", "in", "and",
                 "for", "by", "with", "no", "reply", "address", "speech",
                 "message", "letter", "proclamation", "annual", "special"}
    keywords = [
        w.upper() for w in re.findall(r"[a-zA-Z]+", title)
        if w.lower() not in stopwords and len(w) > 3
    ][:5]  # use at most 5 keywords

    if not keywords:
        return None

    for vol in range(1, 8):
        text = get_volume(vol)
        if not text:
            continue

        # Find candidate section headings (lines that are mostly uppercase)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            # Check if this line contains most of our keywords
            upper = stripped.upper()
            hits = sum(1 for kw in keywords if kw in upper)
            if hits >= min(2, len(keywords)):
                # Found a likely heading — extract text until next heading
                section_lines = []
                j = i + 1
                while j < len(lines) and j < i + 2000:
                    next_line = lines[j].strip().upper()
                    # Stop at next all-caps heading (new speech)
                    if (len(next_line) > 10 and
                            next_line == lines[j].strip() and
                            re.match(r"^[A-Z\s,\.\-\'\"]+$", lines[j].strip()) and
                            len(lines[j].strip()) > 10 and
                            j > i + 5):
                        # Check it looks like a heading not just a sentence
                        if not any(c in lines[j] for c in "abcdefghijklmnopqrstuvwxyz"):
                            break
                    section_lines.append(lines[j])
                    j += 1

                candidate = "\n".join(section_lines).strip()
                if len(candidate) > 200:
                    return candidate

    return None

# ── Main ──────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60]


def make_filename(row: dict) -> str:
    date = row.get("date") or "0000-00-00"
    slug = slugify(row.get("title", "untitled"))
    return f"{date}_{slug}.txt"


def main():
    here = Path(__file__).parent.resolve()

    # Look for corpus_index.csv in same folder or one level up
    index_path = here / "corpus_index.csv"
    if not index_path.exists():
        index_path = here.parent / "metadata" / "corpus_index.csv"
    if not index_path.exists():
        print("Cannot find corpus_index.csv")
        print("Make sure it is in the same folder as this script.")
        return

    out_dir = here  # save speech files to same folder
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(index_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Index loaded: {len(rows)} speeches")
    print(f"Output folder: {out_dir}\n")

    downloaded, skipped, failed = 0, 0, []

    for row in rows:
        speech_id = row["id"]
        title = row["title"]
        date = row.get("date", "")
        already = row.get("in_corpus", "").strip().lower() == "yes"

        if already:
            skipped += 1
            continue

        filename = row.get("filename") or make_filename(row)
        dest = out_dir / filename

        if dest.exists():
            print(f"  [exists]  {filename}")
            skipped += 1
            continue

        print(f"  [{speech_id}] {title[:55]}...", end=" ", flush=True)

        text = None

        # 1. Try Wikisource override if available
        ws_url = WIKISOURCE_OVERRIDES.get(speech_id)
        if ws_url:
            raw = fetch_text(ws_url)
            if raw and len(raw) > 100:
                text = clean_wikitext(raw)

        # 2. Try Gutenberg volume search
        if not text or len(text) < 100:
            text = find_in_gutenberg(title, date)

        if not text or len(text) < 100:
            print("not found")
            failed.append((speech_id, title))
            time.sleep(1)
            continue

        header = (
            f"TITLE: {title}\n"
            f"DATE: {date}\n"
            f"LOCATION: {row.get('location', '')}\n"
            f"TYPE: {row.get('type', '')}\n"
            f"TOPICS: {row.get('topics', '')}\n"
            f"SOURCE: {ws_url or 'Project Gutenberg Collected Works'}\n"
            f"{'=' * 60}\n\n"
        )

        dest.write_text(header + text, encoding="utf-8")
        print(f"saved ({len(text):,} chars)")
        downloaded += 1
        time.sleep(0.5)

    print(f"\n{'─' * 50}")
    print(f"Downloaded : {downloaded}")
    print(f"Skipped    : {skipped}  (already in corpus)")
    print(f"Not found  : {len(failed)}")
    if failed:
        print("\nNot found in Gutenberg volumes:")
        for fid, ftitle in failed:
            print(f"  {fid}: {ftitle[:70]}")
        print("\nFor these speeches, see corpus_index.csv for the source_url")
        print("and copy/paste the text manually from that web page.")


if __name__ == "__main__":
    main()
