import json, logging, shutil
from pathlib import Path

from llama_index.core import Document, StorageContext, VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')

logging.info("Fully loaded imports")

cfg = {
    "llm": {
        "model": "llama3.2:3b",
        "base_url": "http://localhost:11434",
        "temperature": 0.0,
        "request_timeout": 120.0,
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
        "collection_name": "ai_safety_rag",
    },
    "retrieval": {
        "similarity_top_k": 3,
    },
}
print(json.dumps(cfg, indent=2))

llm = Ollama(
    model=cfg["llm"] + cfg["model"],
    base_url=cfg["llm"] + cfg["base_url"],
    temperature=cfg["llm"]+ cfg["temperature"],
    request_timeout=cfg["llm"] + cfg["request_timeout"]
)

CORPUS_TEXT = ""

# TODO: Insert the directory that the LLM will be ingesting
documents = [Document(text=CORPUS_TEXT, metadata={"source": "warframe wiki"})]

splitter = SentenceSplitter(
    chunk_size=cfg["splitter"]["chunk_size"],
    chnk_overlap=cfg["splitter"]["chunk_overlap"]
)

nodes = splitter.get_nodes_from_documents(documents)


# Pull the data from your chosen directory
index = VectorStoreIndex()

# We do query since we're not necessarily finding files
query_engine = index.as_query_engine()

