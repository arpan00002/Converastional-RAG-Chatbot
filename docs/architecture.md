# Architecture
The API routes requests through a LangGraph-compatible RAG orchestration layer. Chroma stores embeddings by default; hosted vector storage can be selected with Pinecone settings. SQLite isolates messages by user and thread.
