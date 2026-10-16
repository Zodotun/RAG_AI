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

## Getting the data — how `fetch_wiki.py` does it (2026-10-15)
- There is **no official full database dump** for the new wiki. `Special:Export` exports individual pages as wikitext only.
- The wiki's `robots.txt` disallows `/*api.php`, `/*?action=`, `/w/Special:` and the REST endpoints, so the downloader uses **none of them**. It only requests normal article pages (`/w/<Title>`) and category pages (`/w/Category:<Name>`), which robots.txt allows. Category pages give the list of articles to fetch.
- It stays polite: a `User-Agent` naming this project and its GitHub URL, one request at a time, 1 second apart, backing off on `429`/`5xx`.
- The starter set (Warframes, Warframe Abilities, Primary/Secondary/Melee Weapons; `Conclave:` PvP pages skipped) is ~1,500 pages, ~25 minutes, ~10 MB of text.
- The full wiki (~11k pages) would take ~3 hours at this rate. Still worth a courtesy message on the wiki or its Discord before doing a full download.
- Not done yet: incremental updates. `--refresh` re-downloads everything; a smarter version could compare each page's `revision` (saved in the file header) to the live one.

## How this fits the project steps
Step 3 ("load documents") becomes three parts:

1. **Fetch** — `fetch_wiki.py` downloads each article's rendered text to `data/wiki/<Title>.md`, with the title, URL and last-edited time at the top, so answers can link back to the page.
2. **Clean** — strip navboxes, reference lists, "See also" and giant tables. This keeps the database small and stops the model quoting navigation menus.
3. **Ingest** — split into chunks, embed with `nomic-embed-text` and store in `chroma_db/` (the plan we already have).

`data/` and `chroma_db/` are in `.gitignore`. The wiki text is large, licensed separately and easy to re-download, so **each computer fetches its own copy** by running the script. Only code goes to GitHub.

### Measured timings (2026-10-15, RTX 3080)
- Fetch: 1 page/second by design.
- Embedding: 125 chunks in 4 seconds with `embed_batch_size=64` (it took 67 s with the default batch of 10). The starter set is ~5 chunks per page.
- Answers from `llama3.2:3b`: ~28 s for the first question including model load, faster after. Capping `context_window` at 8192 matters: without it the model was loaded with a 131k context (18 GB) and spilled half onto the CPU.
- CPU-only machines will be noticeably slower at both embedding and answering.
