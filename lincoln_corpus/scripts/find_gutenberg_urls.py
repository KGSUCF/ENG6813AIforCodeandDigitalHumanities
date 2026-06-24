"""
Find working Gutenberg URLs for Lincoln volumes.
Run this once and paste the output back.

Usage:
    python find_gutenberg_urls.py
"""
import urllib.request

HEADERS = {"User-Agent": "Lincoln-Corpus-Builder/1.0 (academic research)"}

# Candidates to test — the complete works plus plausible individual volume numbers
CANDIDATES = [
    # Complete 7-volume works (most likely to work)
    ("Complete Works (3253)",   "https://www.gutenberg.org/files/3253/3253-0.txt"),
    ("Speeches & Letters (14721)", "https://www.gutenberg.org/files/14721/14721-0.txt"),
    # Vol 1 (confirmed)
    ("Vol 1 — 2653-0",  "https://www.gutenberg.org/files/2653/2653-0.txt"),
    # Try alternative URL format for vols 2-7
    ("Vol 2 — 2654-0",  "https://www.gutenberg.org/files/2654/2654-0.txt"),
    ("Vol 2 — 2654",    "https://www.gutenberg.org/files/2654/2654.txt"),
    ("Vol 2 — pg2654",  "https://www.gutenberg.org/cache/epub/2654/pg2654.txt"),
    ("Vol 3 — 2655-0",  "https://www.gutenberg.org/files/2655/2655-0.txt"),
    ("Vol 3 — pg2655",  "https://www.gutenberg.org/cache/epub/2655/pg2655.txt"),
    ("Vol 4 — 2656-0",  "https://www.gutenberg.org/files/2656/2656-0.txt"),
    ("Vol 4 — pg2656",  "https://www.gutenberg.org/cache/epub/2656/pg2656.txt"),
    ("Vol 5 — 2657-0",  "https://www.gutenberg.org/files/2657/2657-0.txt"),
    ("Vol 5 — pg2657",  "https://www.gutenberg.org/cache/epub/2657/pg2657.txt"),
    ("Vol 6 — 2658-0",  "https://www.gutenberg.org/files/2658/2658-0.txt"),
    ("Vol 6 — pg2658",  "https://www.gutenberg.org/cache/epub/2658/pg2658.txt"),
    ("Vol 7 — 2659-0",  "https://www.gutenberg.org/files/2659/2659-0.txt"),
    ("Vol 7 — pg2659",  "https://www.gutenberg.org/cache/epub/2659/pg2659.txt"),
]

for label, url in CANDIDATES:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            first_bytes = r.read(200).decode("utf-8", errors="replace")
            print(f"  OK   {label}")
            print(f"       {url}")
            print(f"       Preview: {first_bytes[:80].strip()}")
            print()
    except urllib.error.HTTPError as e:
        print(f"  {e.code}  {label}")
    except Exception as e:
        print(f"  ERR  {label}: {e}")

print("\nDone.")
