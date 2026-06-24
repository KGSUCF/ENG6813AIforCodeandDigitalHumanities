"""
Lincoln Corpus Downloader — v3
===============================
Sources tried in order for each speech:
  1. Wikisource raw API  (major famous speeches)
  2. Abraham Lincoln Online (abrahamlincolnonline.org)
  3. Project Gutenberg plain-text volumes (bulk matching)

REQUIREMENTS: Python 3.6+ — NO installs needed (stdlib only).

HOW TO RUN (from your ABC/lincoln folder):
    python download_speeches.py

Only speeches not yet in your folder will be downloaded.
"""

import csv
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from html.parser import HTMLParser

# ── Source maps ───────────────────────────────────────────────────────────────

# Wikisource raw wikitext API — strips cleanly to plain text
WIKISOURCE = {
    "LINC_004": "https://en.wikisource.org/w/index.php?title=Perpetuation_of_Our_Political_Institutions&action=raw",
    "LINC_018": "https://en.wikisource.org/w/index.php?title=House_Divided_Speech&action=raw",
    "LINC_038": "https://en.wikisource.org/w/index.php?title=Cooper_Union_address&action=raw",
    "LINC_044": "https://en.wikisource.org/w/index.php?title=Farewell_Address_at_Springfield&action=raw",
    "LINC_052": "https://en.wikisource.org/w/index.php?title=Abraham_Lincoln%27s_First_Inaugural_Address&action=raw",
    "LINC_053": "https://en.wikisource.org/w/index.php?title=Proclamation_Calling_the_Militia_and_Convening_Congress&action=raw",
    "LINC_064": "https://en.wikisource.org/w/index.php?title=Letter_to_Horace_Greeley_(August_22,_1862)&action=raw",
    "LINC_065": "https://en.wikisource.org/w/index.php?title=Preliminary_Emancipation_Proclamation&action=raw",
    "LINC_067": "https://en.wikisource.org/w/index.php?title=Emancipation_Proclamation&action=raw",
    "LINC_073": "https://en.wikisource.org/w/index.php?title=Proclamation_of_Thanksgiving_(1863)&action=raw",
    "LINC_074": "https://en.wikisource.org/w/index.php?title=Gettysburg_Address&action=raw",
    "LINC_076": "https://en.wikisource.org/w/index.php?title=Proclamation_of_Amnesty_and_Reconstruction&action=raw",
    "LINC_086": "https://en.wikisource.org/w/index.php?title=Message_to_Congress_on_the_Thirteenth_Amendment&action=raw",
    "LINC_087": "https://en.wikisource.org/w/index.php?title=Abraham_Lincoln%27s_Second_Inaugural_Address&action=raw",
    "LINC_089": "https://en.wikisource.org/w/index.php?title=Last_public_address_(Lincoln)&action=raw",
    "LINC_117": "https://en.wikisource.org/w/index.php?title=Reply_to_Working_Men_of_Manchester&action=raw",
    "LINC_119": "https://en.wikisource.org/w/index.php?title=Proclamation_of_a_National_Fast_Day_(1861)&action=raw",
    "LINC_120": "https://en.wikisource.org/w/index.php?title=Proclamation_Appointing_a_National_Fast_Day&action=raw",
}

# Abraham Lincoln Online — individual speech pages, plain HTML, no blocking
ALINC_BASE = "https://www.abrahamlincolnonline.org/lincoln/speeches/"
ALINC = {
    "LINC_005": "temperance.htm",
    "LINC_007": "spot.htm",
    "LINC_008": "mexico.htm",
    "LINC_010": "worcester.htm",
    "LINC_012": "taylor.htm",
    "LINC_016": "kalamazoo.htm",
    "LINC_017": "galena.htm",
    "LINC_019": "chicago.htm",
    "LINC_020": "spfld2.htm",
    "LINC_021": "lewistown.htm",
    "LINC_029": "edwardsville.htm",
    "LINC_030": "columbus2.htm",
    "LINC_031": "cincinnati.htm",
    "LINC_033": "milwaukee.htm",
    "LINC_034": "elwood.htm",
    "LINC_039": "hartford.htm",
    "LINC_040": "newhaven.htm",
    "LINC_046": "columbus3.htm",
    "LINC_047": "pittsburgh.htm",
    "LINC_049": "trenton1.htm",
    "LINC_050": "trenton2.htm",
    "LINC_051": "philadel.htm",
    "LINC_060": "emassdist.htm",
    "LINC_061": "border.htm",
    "LINC_071": "order.htm",
    "LINC_078": "500thou.htm",
    "LINC_079": "sanit2.htm",
    "LINC_080": "164ohio.htm",
    "LINC_081": "166ohio.htm",
    "LINC_082": "148ohio.htm",
    "LINC_102": "trent.htm",
    "LINC_108": "chicago2.htm",
    "LINC_109": "140ind.htm",
    "LINC_114": "deserter.htm",
    "LINC_115": "savannah.htm",
    "LINC_116": "hodges.htm",
    "LINC_118": "london.htm",
    "LINC_122": "peace.htm",
    "LINC_125": "transmit.htm",
}

# Gutenberg 7-volume plain-text URLs (Lapsley edition, public domain)
GUTENBERG_VOLS = [
    "https://www.gutenberg.org/files/2653/2653-0.txt",  # Vol 1: 1832–1843
    "https://www.gutenberg.org/files/2654/2654-0.txt",  # Vol 2: 1843–1858
    "https://www.gutenberg.org/files/2655/2655-0.txt",  # Vol 3: 1858
    "https://www.gutenberg.org/files/2656/2656-0.txt",  # Vol 4: 1858–1860
    "https://www.gutenberg.org/files/2657/2657-0.txt",  # Vol 5: 1858–1862
    "https://www.gutenberg.org/files/2658/2658-0.txt",  # Vol 6: 1862–1863
    "https://www.gutenberg.org/files/2659/2659-0.txt",  # Vol 7: 1863–1865
]

HEADERS = {"User-Agent": "Lincoln-Corpus-Builder/1.0 (academic research)"}

# ── HTTP ──────────────────────────────────────────────────────────────────────

def fetch(url: str) -> str | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ct)
            return raw.decode(m.group(1) if m else "utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}", end=" ")
    except Exception as e:
        print(f"ERR({type(e).__name__})", end=" ")
    return None

# ── Text cleaners ─────────────────────────────────────────────────────────────

def clean_wikitext(t: str) -> str:
    t = re.sub(r"\{\{[^}]*\}\}", "", t)
    t = re.sub(r"\[\[(File|Image):[^\]]*\]\]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", t)
    t = re.sub(r"={2,}([^=]+)={2,}", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


class _StripHTML(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "aside", "noscript"}
    def __init__(self):
        super().__init__()
        self._depth = 0
        self._parts = []
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._depth += 1
    def handle_endtag(self, tag):
        if tag in self.SKIP and self._depth:
            self._depth -= 1
    def handle_data(self, data):
        if not self._depth:
            self._parts.append(data)
    def result(self):
        t = " ".join(self._parts)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"[ \t]+", " ", t)
        return t.strip()

def strip_html(html: str) -> str:
    p = _StripHTML()
    p.feed(html)
    return p.result()

# ── Gutenberg volume cache & search ──────────────────────────────────────────

_vol_cache: list[str] = []

def load_gutenberg_volumes():
    global _vol_cache
    if _vol_cache:
        return
    print("\n  [Gutenberg] Downloading 7 volumes (one-time, ~5 MB total)...")
    for i, url in enumerate(GUTENBERG_VOLS, 1):
        print(f"    Vol {i}...", end=" ", flush=True)
        text = fetch(url)
        if text:
            _vol_cache.append(text)
            print(f"ok ({len(text):,} chars)")
        else:
            _vol_cache.append("")
            print("failed")
    print()


def search_gutenberg(title: str) -> str | None:
    """Search Gutenberg volumes for a speech matching key words from title."""
    stopwords = {"the", "a", "an", "of", "on", "at", "to", "in", "and",
                 "for", "by", "with", "no", "reply", "address", "speech",
                 "message", "letter", "proclamation", "annual", "special",
                 "illinois", "ohio", "indiana", "kansas", "pennsylvania"}
    keywords = [
        w.upper() for w in re.findall(r"[a-zA-Z]+", title)
        if w.lower() not in stopwords and len(w) > 3
    ][:6]
    if len(keywords) < 2:
        return None

    for vol_text in _vol_cache:
        if not vol_text:
            continue
        lines = vol_text.split("\n")
        for i, line in enumerate(lines):
            s = line.strip()
            if not s or len(s) < 5:
                continue
            # Heading: mostly uppercase, no lowercase letters
            if re.search(r"[a-z]", s):
                continue
            upper = s.upper()
            hits = sum(1 for kw in keywords if kw in upper)
            if hits >= min(3, len(keywords)):
                # Extract text until next heading
                body_lines = []
                j = i + 1
                while j < min(len(lines), i + 3000):
                    l = lines[j]
                    stripped = l.strip()
                    # Stop at next all-caps heading (5+ words, no lowercase)
                    if (stripped and len(stripped) > 15
                            and not re.search(r"[a-z]", stripped)
                            and j > i + 10):
                        break
                    body_lines.append(l)
                    j += 1
                body = "\n".join(body_lines).strip()
                if len(body) > 300:
                    return body
    return None

# ── Fetch from a single source ────────────────────────────────────────────────

def get_speech_text(speech_id: str, title: str) -> tuple[str | None, str]:
    """Try each source in order. Returns (text, source_label)."""

    # 1. Wikisource
    ws_url = WIKISOURCE.get(speech_id)
    if ws_url:
        raw = fetch(ws_url)
        if raw and len(raw) > 100:
            text = clean_wikitext(raw)
            if len(text) > 100:
                return text, ws_url

    # 2. Abraham Lincoln Online
    alinc_file = ALINC.get(speech_id)
    if alinc_file:
        url = ALINC_BASE + alinc_file
        html = fetch(url)
        if html and len(html) > 500:
            text = strip_html(html)
            if len(text) > 100:
                return text, url

    # 3. Gutenberg volumes
    load_gutenberg_volumes()
    text = search_gutenberg(title)
    if text and len(text) > 100:
        return text, "Project Gutenberg Collected Works"

    return None, ""

# ── Main ──────────────────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60]

def make_filename(row: dict) -> str:
    return f"{row.get('date','0000-00-00')}_{slugify(row.get('title','untitled'))}.txt"

def main():
    here = Path(__file__).parent.resolve()
    index_path = here / "corpus_index.csv"
    if not index_path.exists():
        index_path = here.parent / "metadata" / "corpus_index.csv"
    if not index_path.exists():
        print("Cannot find corpus_index.csv — make sure it is in the same folder.")
        return

    out_dir = here
    with open(index_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Index loaded: {len(rows)} speeches")
    print(f"Saving to: {out_dir}\n")

    downloaded, skipped, failed = 0, 0, []

    for row in rows:
        sid   = row["id"]
        title = row["title"]
        already = row.get("in_corpus", "").strip().lower() == "yes"

        if already:
            skipped += 1
            continue

        filename = row.get("filename") or make_filename(row)
        dest = out_dir / filename
        if dest.exists():
            skipped += 1
            continue

        print(f"  [{sid}] {title[:55]}...", end=" ", flush=True)
        text, source = get_speech_text(sid, title)

        if not text or len(text) < 100:
            print("not found")
            failed.append((sid, title))
            time.sleep(0.5)
            continue

        header = (
            f"TITLE: {title}\n"
            f"DATE: {row.get('date','')}\n"
            f"LOCATION: {row.get('location','')}\n"
            f"TYPE: {row.get('type','')}\n"
            f"TOPICS: {row.get('topics','')}\n"
            f"SOURCE: {source}\n"
            f"{'='*60}\n\n"
        )
        dest.write_text(header + text, encoding="utf-8")
        print(f"saved ({len(text):,} chars)")
        downloaded += 1
        time.sleep(0.5)

    print(f"\n{'─'*50}")
    print(f"Downloaded : {downloaded}")
    print(f"Skipped    : {skipped}  (already in corpus)")
    print(f"Not found  : {len(failed)}")
    if failed:
        print("\nStill not found:")
        for fid, ftitle in failed:
            print(f"  {fid}: {ftitle[:70]}")

if __name__ == "__main__":
    main()
