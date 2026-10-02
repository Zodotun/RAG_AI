# RAG_AI
Personal Project that features AI that ingests text and can spit out answers based on the text it is trained.

# Current status of project
We still need to figure out what exactly we want to ingest. We decided to go for the full
thing. Probably not the best idea, but again...

I went for a simple directory read. This may be an alternative to ChromaDB, but I suppose that if the agent is doing
proactive work in needing to update stale documents, then this is probably not neessary.

# Requirements to Contribute
1. Install dependencies

For those who use PyCharm, install the following python packages:
- llama-index
- chromadb
- llama-index-embeddings-ollama
- llama-index-llms-ollama
- llama-index-vector-stores-chroma

For some reason, it may not install the specific packages that may be necessary to run, so you may install

