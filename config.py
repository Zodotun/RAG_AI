"""Shared settings for ingest.py and main.py, so both always use the same models and database."""
import chromadb
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

cfg = {
    "llm": {
        "model": "llama3.2:3b",
        "base_url": "http://localhost:11434",
        "temperature": 0.0,
        "request_timeout": 300.0,
        # Without a cap, llama-index asks Ollama for the model's full 131k context (~18 GB), which spills
        # onto the CPU and makes every answer take over a minute. 5 chunks of 512 tokens fit easily in 8k.
        "context_window": 8192,
    },
    "embedding": {
        "model": "nomic-embed-text",
        "base_url": "http://localhost:11434",
    },
    "splitter": {
        "chunk_size": 512,
        "chunk_overlap": 50,
    },
    "chroma": {
        "persist_dir": "./chroma_db",
        "collection_name": "warframe_wiki",
    },
    "retrieval": {
        "similarity_top_k": 5,
    },
    "data_dir": "./data/wiki",
}


def make_llm():
    c = cfg["llm"]
    return Ollama(model=c["model"], base_url=c["base_url"], temperature=c["temperature"],
                  request_timeout=c["request_timeout"], context_window=c["context_window"])


def make_embed_model():
    c = cfg["embedding"]
    # nomic-embed-text was trained with these task prefixes; retrieval is noticeably worse without them.
    return OllamaEmbedding(model_name=c["model"], base_url=c["base_url"], embed_batch_size=64,
                           query_instruction="search_query:", text_instruction="search_document:")


def use_local_models():
    """Point LlamaIndex at Ollama so nothing silently falls back to OpenAI defaults."""
    Settings.llm = make_llm()
    Settings.embed_model = make_embed_model()


def chroma_client():
    return chromadb.PersistentClient(path=cfg["chroma"]["persist_dir"])


def vector_store(client=None):
    client = client or chroma_client()
    collection = client.get_or_create_collection(cfg["chroma"]["collection_name"])
    return ChromaVectorStore(chroma_collection=collection)
