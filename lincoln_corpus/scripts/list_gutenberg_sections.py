"""
Gutenberg Diagnostic — list all section titles found in Lincoln volumes.
Run this once, copy the output, and share it so the download script
can be updated with correct title matches.

Usage:
    python list_gutenberg_sections.py
"""
import re
import urllib.request

VOLS = [
    ("Vol 1 (1832-1843)", "https://www.gutenberg.org/files/2653/2653-0.txt"),
    ("Vol 2 (1843-1858)", "https://www.gutenberg.org/cache/epub/2654/pg2654.txt"),
    ("Vol 3 (1858)",      "https://www.gutenberg.org/cache/epub/2655/pg2655.txt"),
    ("Vol 4 (1858-1860)", "https://www.gutenberg.org/cache/epub/2656/pg2656.txt"),
    ("Vol 5 (1858-1862)", "https://www.gutenberg.org/cache/epub/2657/pg2657.txt"),
    ("Vol 6 (1862-1863)", "https://www.gutenberg.org/cache/epub/2658/pg2658.txt"),
    ("Vol 7 (1863-1865)", "https://www.gutenberg.org/cache/epub/2659/pg2659.txt"),
]

HEADERS = {"User-Agent": "Lincoln-Corpus-Builder/1.0 (academic research)"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FAILED: {e}")
        return None

def find_sections(text):
    """
    Find lines that look like speech headings:
    - All uppercase (no lowercase letters)
    - At least 5 characters long
    - Not just a number or single word like "THE"
    """
    sections = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        s = line.strip()
        if len(s) < 5:
            continue
        if re.search(r"[a-z]", s):   # skip anything with lowercase
            continue
        if re.match(r"^[\d\s\.\,\-]+$", s):  # skip pure numbers/dates
            continue
        if s.startswith("*") or s.startswith("_"):
            continue
        # Must have at least 2 words or be long enough to be a title
        words = s.split()
        if len(words) < 2 and len(s) < 20:
            continue
        sections.append((i + 1, s))
    return sections

for label, url in VOLS:
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"Downloading {url} ...", flush=True)
    text = fetch(url)
    if not text:
        print("  Could not download.")
        continue
    sections = find_sections(text)
    print(f"Found {len(sections)} uppercase headings:\n")
    for lineno, title in sections:
        print(f"  line {lineno:5d}: {title}")

print("\nDone.")
