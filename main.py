"""Ask questions about Warframe, answered from the wiki pages in chroma_db/ (built by ingest.py).

  python main.py "What does Excalibur's Exalted Blade do?"
  python main.py                 # interactive: type questions, empty line to quit
"""
import logging
import sys

from llama_index.core import PromptTemplate, VectorStoreIndex

from config import cfg, use_local_models, vector_store

logging.basicConfig(level=logging.WARNING)

QA_PROMPT = PromptTemplate(
    "You answer questions about the video game Warframe using only the wiki excerpts below.\n"
    "If the excerpts don't contain the answer, say you don't know. Don't make up stats or numbers.\n"
    "Keep the answer short.\n\n"
    "Wiki excerpts:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Question: {query_str}\n"
    "Answer: "
)


def build_query_engine():
    use_local_models()
    store = vector_store()
    if store._collection.count() == 0:
        raise SystemExit("The database is empty. Run `python fetch_wiki.py` then `python ingest.py` first.")
    index = VectorStoreIndex.from_vector_store(store)
    return index.as_query_engine(similarity_top_k=cfg["retrieval"]["similarity_top_k"],
                                 text_qa_template=QA_PROMPT)


def ask(engine, question):
    response = engine.query(question)
    print(f"\n{str(response).strip()}\n\nSources:")
    seen = set()
    for hit in response.source_nodes:
        title, url = hit.node.metadata.get("title"), hit.node.metadata.get("url", "")
        if title not in seen:
            seen.add(title)
            print(f"  {hit.score:.2f}  {title}  {url}")
    print()


def main():
    engine = build_query_engine()
    if len(sys.argv) > 1:
        ask(engine, " ".join(sys.argv[1:]))
        return
    while question := input("Question (empty to quit): ").strip():
        ask(engine, question)


if __name__ == "__main__":
    main()
