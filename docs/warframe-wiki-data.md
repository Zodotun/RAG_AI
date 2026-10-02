# Warframe Wiki as the data source

Research notes from 2026-10-02 on pulling https://wiki.warframe.com into this RAG project.

## The source

| | |
|---|---|
| Wiki | https://wiki.warframe.com (official wiki, MediaWiki 1.45, hosted by Weird Gloop; moved off Fandom) |
| Articles | **10,944** non-redirect pages in the main namespace (11,564 counting a few special cases) |
| Words in articles | ~10.6 million (wiki search index count) |
| Images | ~96,800 — **not needed**, we only embed text |
| License | **CC BY-NC-SA 3.0** — fine for a personal, non-commercial project; must credit the wiki, and anything we redistribute must use the same license |
| Old Fandom wiki | `warframe.fandom.com` is outdated and blocks scripted requests (403) — don't use it |

## How big is it on disk?

Measured by summing every article's size through the wiki API and rendering a random sample of 25 pages to plain text.

| What | Size |
|---|---|
| Raw wikitext (source markup) for all articles | ~73 MB |
| Rendered plain text, everything included | ~270 MB (inflated by navigation boxes and big tables repeated on many pages) |
| Rendered plain text after cleanup (strip navboxes, references, giant tables) | **~60–100 MB** expected |
| Chroma database (768-dim `nomic-embed-text` vectors + stored text) | **~0.2–1 GB**, depending on how much cleanup we do (~30k–140k chunks at ~7 KB each) |

Whole project on one PC:

| Piece | Size |
|---|---|
| Ollama models (`llama3.2:3b` + `nomic-embed-text`) | 2.2 GB (measured) |
| Python `.venv` | 0.5 GB (measured) |
| Downloaded wiki text (`data/`) | 0.1–0.3 GB |
| Chroma database (`chroma_db/`) | 0.2–1 GB |
| **Total** | **~3–4 GB** |

### Pages worth skipping
- `WarframeUsageData2020.json` (6.6 MB of raw JSON) and `Weapon Comparison/CSV` — data dumps, not prose.
- `Update NN` patch-note pages (hundreds of KB each) — useful for "when did X change" questions, but noisy. Start without them; add later as a separate collection.

## Why plain wikitext isn't enough
Many stats (weapon damage, Warframe abilities, drop tables) aren't in the page source. Pages call templates and Lua modules that fill the numbers in at render time. We need the **rendered** text (`action=parse`, or the TextExtracts extension, which is installed), not the raw wikitext.

## Getting the data — open question
- There is **no official full database dump** for the new wiki. `Special:Export` exports individual pages as wikitext only.
- The MediaWiki API works (`https://wiki.warframe.com/api.php`), but the wiki's `robots.txt` has `Disallow: /*api.php`. That's aimed at crawlers, but it means **a bulk download should be slow and polite**, or cleared with the wiki admins first:
  - a descriptive `User-Agent` naming this project
  - one request at a time, ~1 per second, with `maxlag=5`
  - ~11k pages at that rate is **~3 hours, done once**. After that, fetch only pages changed since the last run (`list=recentchanges`).
- Decide before writing the downloader: ask on the wiki (or its Discord) whether bulk API use for a personal project is OK.

## How this fits the project steps
Step 3 ("load documents") becomes three parts:

1. **Fetch** — `fetch_wiki.py` downloads each article's rendered text to `data/wiki/<Title>.md`, with the title, URL and last-edited time at the top, so answers can link back to the page.
2. **Clean** — strip navboxes, reference lists, "See also" and giant tables. This keeps the database small and stops the model quoting navigation menus.
3. **Ingest** — split into chunks, embed with `nomic-embed-text` and store in `chroma_db/` (the plan we already have).

`data/` and `chroma_db/` are in `.gitignore`. The wiki text is large, licensed separately and easy to re-download, so **each computer fetches its own copy** by running the script. Only code goes to GitHub.

### Rough timings on this PC (CPU only, no usable GPU)
- Fetch: ~3 hours once, minutes for later updates.
- Embedding: roughly 15 minutes to 2 hours depending on chunk count. Test on a small slice first, e.g. 200 Warframe and weapon pages.
- Answers from `llama3.2:3b` on CPU: a few seconds to ~30 seconds each.
