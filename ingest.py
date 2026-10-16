"""Embed the downloaded wiki pages (data/wiki/*.md) into the Chroma database (chroma_db/).

Run fetch_wiki.py first. Rebuilds the collection from scratch each time.
  python ingest.py              # everything in data/wiki
  python ingest.py --limit 50   # quick test on the first 50 pages
"""
import argparse
import logging
import time
from pathlib import Path

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from config import cfg, chroma_client, use_local_models, vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")


def load_page(path):
    """Split a fetch_wiki.py file into (metadata, body)."""
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if raw.startswith("---\n"):
        header, _, body = raw[4:].partition("\n---\n")
        for line in header.splitlines():
            key, _, value = line.partition(": ")
            meta[key] = value
    meta.setdefault("title", path.stem)
    return meta, body.strip()


def load_documents(data_dir, limit=None):
    paths = sorted(Path(data_dir).glob("*.md"))[:limit]
    docs = []
    for p in paths:
        meta, body = load_page(p)
        if not body:
            continue
        doc = Document(text=body, metadata=meta, id_=meta["title"])
        # The title helps both retrieval and the answer; the URL and revision are only for citations.
        doc.excluded_embed_metadata_keys = ["url", "revision", "last_edited"]
        doc.excluded_llm_metadata_keys = ["revision", "last_edited"]
        docs.append(doc)
    return docs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, help="only ingest the first N pages")
    args = ap.parse_args()

    docs = load_documents(cfg["data_dir"], args.limit)
    if not docs:
        raise SystemExit(f"No pages in {cfg['data_dir']}. Run `python fetch_wiki.py` first.")
    logging.info("Loaded %d pages", len(docs))

    splitter = SentenceSplitter(chunk_size=cfg["splitter"]["chunk_size"],
                                chunk_overlap=cfg["splitter"]["chunk_overlap"])
    nodes = splitter.get_nodes_from_documents(docs, show_progress=True)
    logging.info("Split into %d chunks", len(nodes))

    use_local_models()
    client = chroma_client()
    name = cfg["chroma"]["collection_name"]
    if name in [c.name for c in client.list_collections()]:
        client.delete_collection(name)
    storage = StorageContext.from_defaults(vector_store=vector_store(client))

    start = time.time()
    VectorStoreIndex(nodes, storage_context=storage, show_progress=True)
    logging.info("Embedded %d chunks in %.0fs -> %s", len(nodes), time.time() - start, cfg["chroma"]["persist_dir"])


if __name__ == "__main__":
    main()
