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
# Vols 2-7 use the /cache/epub/ path; vol 1 uses /files/
GUTENBERG_VOLS = [
    "https://www.gutenberg.org/files/2653/2653-0.txt",          # Vol 1: 1832–1843
    "https://www.gutenberg.org/cache/epub/2654/pg2654.txt",     # Vol 2: 1843–1858
    "https://www.gutenberg.org/cache/epub/2655/pg2655.txt",     # Vol 3: 1858
    "https://www.gutenberg.org/cache/epub/2656/pg2656.txt",     # Vol 4: 1858–1860
    "https://www.gutenberg.org/cache/epub/2657/pg2657.txt",     # Vol 5: 1858–1862
    "https://www.gutenberg.org/cache/epub/2658/pg2658.txt",     # Vol 6: 1862–1863
    "https://www.gutenberg.org/cache/epub/2659/pg2659.txt",     # Vol 7: 1863–1865
]

HEADERS = {"User-Agent": "Lincoln-Corpus-Builder/1.0 (academic research)"}

# ── Exact Gutenberg heading map ───────────────────────────────────────────────
# Maps LINC ID → (vol_index 0-6, exact heading string from Lapsley edition)
# Generated from list_gutenberg_sections.py diagnostic output.

GUTENBERG_TITLE_MAP: dict[str, tuple[int, str]] = {
    # Vol 1 (index 0): 1832–1843
    "LINC_001": (0, "ADDRESS BEFORE THE YOUNG MEN'S LYCEUM"),
    "LINC_002": (0, "COMMUNICATION TO THE PEOPLE OF SANGAMO COUNTY"),
    "LINC_003": (0, "PROTEST IN THE ILLINOIS LEGISLATURE"),
    "LINC_004": (0, "ADDRESS BEFORE THE SPRINGFIELD WASHINGTON TEMPERANCE SOCIETY"),
    "LINC_006": (0, "EULOGY ON HENRY CLAY"),

    # Vol 2 (index 1): 1843–1858
    "LINC_005": (1, "TEMPERANCE ADDRESS"),
    "LINC_007": (1, "RESOLUTIONS IN THE UNITED STATES HOUSE OF REPRESENTATIVES,"),
    "LINC_008": (1, "SPEECH ON DECLARATION OF WAR ON MEXICO"),
    "LINC_010": (1, "SPEECH DELIVERED AT WORCESTER, MASS., ON SEPT. 12, 1848."),
    "LINC_012": (1, "EULOGY ON HENRY CLAY,"),
    "LINC_016": (1, "SPEECH AT KALAMAZOO, MICHIGAN,"),
    "LINC_017": (1, "FRAGMENT OF SPEECH AT GALENA, ILLINOIS"),
    "LINC_112": (1, "GENERAL TAYLOR AND THE VETO"),

    # Vol 3 (index 2): 1858
    "LINC_018": (2, "HOUSE DIVIDED"),
    "LINC_019": (2, "SPEECH AT CHICAGO, JULY 10, 1858."),
    "LINC_020": (2, "SPEECH AT SPRINGFIELD, JULY 17, 1858."),
    "LINC_021": (2, "SPEECH AT LEWISTOWN, ILLINOIS,"),
    "LINC_022": (2, "FIRST JOINT DEBATE AT OTTAWA,"),
    "LINC_023": (2, "SECOND JOINT DEBATE AT FREEPORT,"),
    "LINC_024": (2, "THIRD JOINT DEBATE AT JONESBORO,"),
    "LINC_025": (2, "FOURTH JOINT DEBATE AT CHARLESTON,"),
    "LINC_026": (2, "FIFTH JOINT DEBATE AT GALESBURG,"),
    "LINC_027": (2, "SIXTH JOINT DEBATE AT QUINCY,"),
    "LINC_028": (2, "SEVENTH JOINT DEBATE AT ALTON,"),

    # Vol 4 (index 3): 1858–1860
    "LINC_029": (4, "FRAGMENT OF SPEECH AT EDWARDSVILLE, ILL.,"),
    "LINC_033": (3, "ADDRESS BEFORE THE WISCONSIN STATE AGRICULTURAL SOCIETY,"),
    "LINC_034": (3, "SPEECH AT ELWOOD, KANSAS,"),
    "LINC_037": (4, "FRAGMENT OF SPEECH AT LEAVENWORTH, KANSAS,"),
    "LINC_038": (3, "ADDRESS AT COOPER INSTITUTE,"),

    # Vol 5 (index 4): 1858–1862
    "LINC_030": (4, "SPEECH AT COLUMBUS, OHIO."),
    "LINC_031": (4, "SPEECH AT CINCINNATI OHIO, SEPTEMBER 17, 1859"),
    "LINC_039": (4, "SPEECH AT HARTFORD, CONNECTICUT,"),
    "LINC_040": (4, "SPEECH AT NEW HAVEN, CONNECTICUT, MARCH 6, 1860"),
    "LINC_044": (4, "FAREWELL ADDRESS AT SPRINGFIELD, ILLINOIS."),
    "LINC_046": (4, "ADDRESS TO THE LEGISLATURE OF OHIO AT COLUMBUS"),
    "LINC_047": (4, "ADDRESS AT PITTSBURGH, PENNSYLVANIA"),
    "LINC_048": (4, "ADDRESS TO THE LEGISLATURE OF NEW YORK, AT ALBANY,"),
    "LINC_049": (4, "ADDRESS TO THE SENATE OF NEW JERSEY"),
    "LINC_050": (4, "ADDRESS TO THE ASSEMBLY OF NEW JERSEY,"),
    "LINC_051": (4, "ADDRESS IN THE HALL OF INDEPENDENCE, PHILADELPHIA,"),
    "LINC_052": (4, "FIRST INAUGURAL ADDRESS."),
    "LINC_053": (4, "PROCLAMATION CALLING FOR 75,000 MILITIA,"),
    "LINC_054": (4, "MESSAGE TO CONGRESS IN SPECIAL SESSION,"),
    "LINC_055": (4, "FIRST ANNUAL MESSAGE TO CONGRESS,"),
    "LINC_100": (4, "ADDRESS AT CLEVELAND, OHIO,"),
    "LINC_119": (4, "PROCLAMATION OF A NATIONAL FAST-DAY, AUGUST 12, 1861."),

    # Vol 6 (index 5): 1862–1863
    "LINC_056": (5, "SECOND ANNUAL MESSAGE TO CONGRESS,"),
    "LINC_057": (5, "MESSAGE TO CONGRESS ON COMPENSATED EMANCIPATION,"),
    "LINC_060": (5, "ABOLISHING SLAVERY IN WASHINGTON, D.C."),
    "LINC_061": (5, "APPEAL TO BORDER-STATES IN FAVOR OF COMPENSATED EMANCIPATION."),
    "LINC_064": (5, "LETTER TO HORACE GREELEY,"),
    "LINC_065": (5, "PRELIMINARY EMANCIPATION PROCLAMATION,"),
    "LINC_071": (5, "ORDER OF RETALIATION,"),
    "LINC_073": (5, "PROCLAMATION FOR THANKSGIVING, JULY 15, 1863"),
    "LINC_108": (5, "REPLY TO REQUEST THE PRESIDENT ISSUE A PROCLAMATION OF EMANCIPATION."),
    "LINC_117": (5, "TO THE WORKING-MEN OF MANCHESTER, ENGLAND."),
    "LINC_118": (5, "TO THE WORKING-MEN OF LONDON, ENGLAND."),
    "LINC_120": (5, "PROCLAMATION APPOINTING A NATIONAL FAST-DAY."),

    # Vol 7 (index 6): 1863–1865
    "LINC_067": (6, "EMANCIPATION PROCLAMATION."),
    "LINC_074": (6, "ADDRESS AT GETTYSBURG,"),
    "LINC_075": (6, "THIRD ANNUAL MESSAGE TO CONGRESS,"),
    "LINC_076": (6, "PROCLAMATION OF AMNESTY AND RECONSTRUCTION. DECEMBER 8, 1863."),
    "LINC_078": (6, "CALL FOR 500,000 VOLUNTEERS,"),
    "LINC_079": (6, "SPEECH AT SANITARY FAIR, BALTIMORE,"),
    "LINC_080": (6, "ADDRESS TO THE 164TH OHIO REGIMENT,"),
    "LINC_081": (6, "ADDRESS TO THE 166TH OHIO REGIMENT,"),
    "LINC_082": (6, "ADDRESS TO THE 148TH OHIO REGIMENT,"),
    "LINC_086": (6, "MESSAGE TO CONGRESS ON THE THIRTEENTH AMENDMENT,"),
    "LINC_087": (6, "SECOND INAUGURAL ADDRESS."),
    "LINC_089": (6, "LAST PUBLIC ADDRESS,"),
    "LINC_102": (6, "MESSAGE ON THE TRENT AFFAIR,"),
    "LINC_109": (6, "ADDRESS TO AN INDIANA REGIMENT,"),
    "LINC_114": (6, "PROCLAMATION OFFERING PARDON TO DESERTERS,"),
    "LINC_115": (6, "MESSAGE ON THE FALL OF SAVANNAH,"),
    "LINC_116": (6, "LETTER TO ALBERT G. HODGES,"),
    "LINC_122": (6, "RESPONSE TO A PEACE PROPOSAL,"),
}

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


def extract_gutenberg_section(vol_index: int, heading: str) -> str | None:
    """Extract text of a section from a Gutenberg volume by exact heading match."""
    if vol_index >= len(_vol_cache) or not _vol_cache[vol_index]:
        return None
    lines = _vol_cache[vol_index].split("\n")
    heading_upper = heading.upper().strip()
    start = None
    for i, line in enumerate(lines):
        if line.strip().upper() == heading_upper:
            start = i
            break
        # Also try prefix match for headings that may have trailing punctuation variance
        if line.strip().upper().startswith(heading_upper.rstrip(".,;")):
            start = i
            break
    if start is None:
        return None
    body_lines = []
    j = start + 1
    while j < min(len(lines), start + 4000):
        s = lines[j].strip()
        # Stop at next all-caps heading (no lowercase, long enough)
        if s and len(s) > 10 and not re.search(r"[a-z]", s) and j > start + 5:
            break
        body_lines.append(lines[j])
        j += 1
    body = "\n".join(body_lines).strip()
    return body if len(body) > 200 else None


def search_gutenberg(speech_id: str, title: str) -> str | None:
    """Look up a speech in Gutenberg volumes using exact title map, then fuzzy fallback."""
    # 1. Exact map lookup
    if speech_id in GUTENBERG_TITLE_MAP:
        vol_idx, heading = GUTENBERG_TITLE_MAP[speech_id]
        text = extract_gutenberg_section(vol_idx, heading)
        if text:
            return text

    # 2. Fuzzy keyword fallback across all volumes
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
            if not s or len(s) < 5 or re.search(r"[a-z]", s):
                continue
            hits = sum(1 for kw in keywords if kw in s.upper())
            if hits >= min(3, len(keywords)):
                body_lines = []
                j = i + 1
                while j < min(len(lines), i + 3000):
                    stripped = lines[j].strip()
                    if (stripped and len(stripped) > 15
                            and not re.search(r"[a-z]", stripped)
                            and j > i + 10):
                        break
                    body_lines.append(lines[j])
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
    text = search_gutenberg(speech_id, title)
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
