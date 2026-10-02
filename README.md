# RAG_AI
Personal Project that features AI that ingests text and can spit out answers based on the text it is trained.

# Current status of project
We still need to figure out what exactly we want to ingest. We decided to go for the full
thing. Probably not the best idea, but again...

I went for a simple directory read. This may be an alternative to ChromaDB, but I suppose that if the agent is doing
proactive work in needing to update stale documents, then this is probably not neessary.

The knowledge source is the [WARFRAME Wiki](https://wiki.warframe.com) (CC BY-NC-SA 3.0). See [docs/warframe-wiki-data.md](docs/warframe-wiki-data.md) for its size, disk requirements and the extraction plan.

# Requirements to Contribute
Runs fully locally with [Ollama](https://ollama.com): `llama3.2:3b` answers questions and `nomic-embed-text` builds the embeddings stored in ChromaDB.

## Setup (Windows)
1. Install Git if the PC doesn't have it: `winget install Git.Git`, then open a new terminal.
2. Clone the repo and open a terminal in its folder.
3. Run the setup script. It installs Python 3.12 and Ollama, pulls both models, creates `.venv` and installs `requirements.txt`. Anything already installed is skipped.
   ```
   powershell -ExecutionPolicy Bypass -File setup.ps1
   ```
4. Activate the environment before running anything: `.\.venv\Scripts\Activate.ps1`

PyCharm users: point the project interpreter at `.venv\Scripts\python.exe`.

The Python packages (llama-index core plus its Ollama and Chroma integrations, chromadb, pypdf) are listed in `requirements.txt`. If PyCharm misses any of them, install them all with `pip install -r requirements.txt` from the activated environment.

