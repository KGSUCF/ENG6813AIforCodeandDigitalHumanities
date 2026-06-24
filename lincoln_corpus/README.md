# Lincoln Corpus

A curated digital humanities corpus of Abraham Lincoln's speeches, messages,
proclamations, and addresses, spanning his career from 1832 to 1865.

## Corpus overview

| Stat | Value |
|------|-------|
| Total speeches indexed | 125 |
| Speeches with text files | 15 |
| Date range | March 9, 1832 – April 11, 1865 |
| Primary sources | UCSB American Presidency Project; U of Michigan Collected Works |

## Structure

```
lincoln_corpus/
├── speeches/          ← Individual .txt files, one per speech
├── metadata/
│   └── corpus_index.csv   ← Full index with dates, topics, URLs
└── scripts/
    └── download_speeches.py   ← Run locally to fetch remaining texts
```

## Speech filename convention

`YYYY-MM-DD_short-title.txt`

Each file begins with a metadata header:

```
TITLE: ...
DATE:  ...
LOCATION: ...
TYPE:  ...
TOPICS: ...
SOURCE: ...
============================================================

[speech text]
```

## Periods covered

| Period | Years | Representative speeches |
|--------|-------|------------------------|
| Pre-congressional | 1832–1846 | Lyceum Address, Temperance Address, Eulogy on Clay |
| Congressional | 1847–1849 | Spot Resolutions, Mexican War speech, Internal Improvements |
| Rise to prominence | 1854–1860 | Peoria Speech, House Divided, Lincoln-Douglas Debates, Cooper Union |
| President-elect | 1860–1861 | Farewell Address, Inaugural journey speeches |
| Presidency: 1861 | 1861 | First Inaugural, July 4 Message, First Annual Message |
| Presidency: 1862 | 1862 | Compensated Emancipation messages, Greeley letter, Preliminary EP |
| Presidency: 1863 | 1863 | Final Emancipation Proclamation, Conkling letter, Gettysburg Address |
| Presidency: 1864 | 1864 | Baltimore Sanitary Fair, re-election response, Fourth Annual Message |
| Presidency: 1865 | 1865 | Second Inaugural, Last Public Address |

## Topics covered

- **Slavery & emancipation** — moral arguments, wartime necessity, proclamations
- **Union & secession** — constitutional theory, nationalism, the meaning of the republic
- **War policy** — military strategy, conscription, prisoner of war policy
- **Reconstruction** — amnesty, loyalty oaths, Black suffrage
- **Free labor ideology** — the right to rise, economic opportunity, immigration
- **Economy** — banking, tariffs, internal improvements, agriculture
- **Democracy & elections** — the meaning of self-government, wartime elections
- **Race & equality** — evolving views on Black citizenship and suffrage
- **Religion & Providence** — theodicy of the war, national fast days
- **Foreign policy** — Trent Affair, British relations, international labor solidarity

## Downloading remaining speeches

The 15 speeches already in `speeches/` were obtained from a GitHub source
(rwilleynyc/presidential_speech_corpora). To download the remaining ~110
speeches, run the downloader on your **local machine** (not in a cloud
environment):

```bash
cd lincoln_corpus/scripts
pip install requests beautifulsoup4
python download_speeches.py
```

The script reads `metadata/corpus_index.csv`, fetches each speech not yet
in the corpus from the UCSB American Presidency Project or the University of
Michigan Collected Works of Abraham Lincoln, and saves it to `speeches/`.

Use `--delay 3` to be polite to the servers; the default is 2 seconds.

## Primary sources

- **UCSB American Presidency Project**: https://www.presidency.ucsb.edu
  (presidential documents, inaugurals, annual messages, proclamations)
- **Collected Works of Abraham Lincoln** (U of Michigan):
  https://quod.lib.umich.edu/l/lincoln/
  (comprehensive 8-volume scholarly edition edited by Roy P. Basler, 1953)
- **Abraham Lincoln Online**: https://www.abrahamlincolnonline.org
  (selected speeches with annotations)

## Metadata fields (corpus_index.csv)

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (LINC_001 … LINC_125) |
| `title` | Full speech title |
| `date` | ISO date (YYYY-MM-DD) |
| `year` | Year (for easy filtering) |
| `location` | City, State where delivered |
| `period` | Career period (see table above) |
| `type` | Document type: speech, address, message, proclamation, debate, letter, eulogy |
| `topics` | Comma-separated thematic tags |
| `filename` | Filename in `speeches/` (blank if not yet downloaded) |
| `in_corpus` | `yes` if text file exists; `no` otherwise |
| `source_url` | URL to fetch the text |
| `notes` | Editorial notes |

## License

All speech texts are in the public domain (19th century US government documents
and Lincoln's own writings). The metadata and scripts in this repository are
released under CC0.
