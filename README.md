# RAG_AI
A Warframe question-answering bot. It downloads articles from the [WARFRAME Wiki](https://wiki.warframe.com), stores them in a local vector database, and answers questions with a small local model, citing the wiki pages it used.

Everything runs locally and for free with [Ollama](https://ollama.com): no API keys, no accounts.

```
> python main.py "What are Ash's four abilities, and what is his passive?"

1. Shuriken  2. Smoke Screen  3. Teleport  4. Blade Storm
His passive is: Bleed effects inflicted on enemies do 25% increased damage and last 50% longer.

Sources:
  0.62  Ash/Main  https://wiki.warframe.com/w/Ash/Main
  0.62  Ash  https://wiki.warframe.com/w/Ash
```

## How it works

| Step | Script | What it does | Output |
|---|---|---|---|
| 1. Fetch | `fetch_wiki.py` | Downloads wiki articles and converts them to clean text (keeps infobox stats and tables, drops menus and navboxes) | `data/wiki/*.md` |
| 2. Ingest | `ingest.py` | Splits each page into ~512-token chunks and embeds them with `nomic-embed-text` | `chroma_db/` |
| 3. Ask | `main.py` | Finds the 5 chunks closest to your question and has `llama3.2:3b` answer from only those | answer + sources |

Shared settings (models, chunk size, how many chunks to retrieve) live in [`config.py`](config.py). `wiki_text.py` is the HTML-to-text cleaner used by step 1.

`data/` and `chroma_db/` are **not** in the repo (see [.gitignore](.gitignore)). Each computer builds its own copy by running steps 1 and 2. That takes about half an hour once.

## What you need
- **Windows, macOS or Linux.** The setup script is Windows-only; Mac/Linux steps are below.
- **~4 GB free disk** (models 2.3 GB, Python packages 0.5 GB, wiki text and database under 1 GB for the starter set).
- **8 GB+ RAM.** An NVIDIA GPU (or Apple Silicon) makes answers much faster but isn't required.
- An internet connection for setup and step 1. After that it works offline.

## Step-by-step setup

### Windows
1. Install Git if you don't have it: open PowerShell and run `winget install Git.Git`, then close and reopen PowerShell.
2. Clone the repo and go into it:
   ```
   git clone https://github.com/Zodotun/RAG_AI_TCG.git
   cd RAG_AI_TCG
   ```
3. Run the setup script. It installs Python 3.12 and Ollama if missing, downloads both models (~2.3 GB), creates a `.venv` folder and installs the Python packages. Re-running it is safe.
   ```
   powershell -ExecutionPolicy Bypass -File setup.ps1
   ```
4. Activate the environment. Do this every time you open a new terminal for this project:
   ```
   .\.venv\Scripts\Activate.ps1
   ```
   Your prompt should now start with `(.venv)`.

### macOS / Linux
1. Install Python 3.12 (python.org, or `brew install python@3.12`) and Ollama (download from https://ollama.com, or `curl -fsSL https://ollama.com/install.sh | sh` on Linux).
2. Clone the repo and set it up:
   ```
   git clone https://github.com/Zodotun/RAG_AI_TCG.git
   cd RAG_AI_TCG
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### PyCharm
Point the project interpreter at `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (Mac/Linux). If PyCharm says packages are missing, run `pip install -r requirements.txt` from the activated environment.

## Running it
Ollama must be running. On Windows and macOS it starts by itself after install (look for the llama icon in the tray or menu bar). If a script says it can't connect to `localhost:11434`, start it with `ollama serve` in a separate terminal.

### 1. Download the wiki pages (~25 minutes, once)
```
python fetch_wiki.py
```
This downloads the starter set: every Warframe, Warframe ability and weapon article (about 1,500 pages). It goes slowly on purpose, one page per second, to be polite to the wiki. You can stop it with Ctrl+C at any time; running it again skips pages it already has.

Want to try it in 1 minute first? Download just a few pages:
```
python fetch_wiki.py --category Warframes --limit 20
```
Other options:
```
python fetch_wiki.py --category Mods                  # add a whole wiki category
python fetch_wiki.py --title "Excalibur" --title "Mag" # specific pages
python fetch_wiki.py --refresh                        # re-download pages already on disk
```
Category names are the ones on the wiki, e.g. https://wiki.warframe.com/w/Category:Mods → `--category Mods`.

### 2. Build the database
```
python ingest.py
```
Rebuilds `chroma_db/` from everything in `data/wiki/`. A few minutes with a GPU, longer on CPU only. For a quick test: `python ingest.py --limit 50`.

Re-run this whenever you download more pages or change `chunk_size` in `config.py`.

### 3. Ask questions
```
python main.py "How do I get Atlas Prime?"
python main.py          # interactive mode: keep asking, press Enter on an empty line to quit
```
The first question takes longer while the model loads. After that, expect roughly 5–30 seconds per answer depending on your hardware.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Connection refused` / `localhost:11434` | Ollama isn't running. Start the Ollama app, or run `ollama serve` in another terminal. |
| `model "llama3.2:3b" not found` | Run `ollama pull llama3.2:3b` and `ollama pull nomic-embed-text`. |
| `The database is empty` | Run `python fetch_wiki.py` and then `python ingest.py`. |
| `No pages in ./data/wiki` | Step 1 hasn't been run, or you're not in the repo folder. |
| `ModuleNotFoundError` | The environment isn't active. Run `.\.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate`. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again. |
| Answers are very slow | Check `ollama ps`. If it doesn't say `100% GPU`, the model is running on CPU, which is normal without a supported GPU. Keep `context_window` in `config.py` at 8192 or lower. |
| Answer says "I don't know" for something on the wiki | The page may not be downloaded yet. Fetch its category or title, then re-run `ingest.py`. |

## Ideas for next steps
- Write ~20 test questions with known answers, so we can tell whether changes (chunk size, `similarity_top_k`, a bigger model) actually help.
- Download more of the wiki (Mods, Resources, Missions, Relics). The full wiki is ~11k pages, about 3 hours at the polite rate. See [docs/warframe-wiki-data.md](docs/warframe-wiki-data.md).
- Try a bigger model, e.g. `ollama pull llama3.1:8b`, and change `model` in `config.py`.
- A simple web UI (Streamlit or Gradio) on top of `main.py`.

## Data and license
Wiki text comes from the [WARFRAME Wiki](https://wiki.warframe.com) under **CC BY-NC-SA 3.0**: fine for this non-commercial project as long as we credit the wiki. Answers link back to the source pages. More detail, including sizes and the download rules we follow, is in [docs/warframe-wiki-data.md](docs/warframe-wiki-data.md).
