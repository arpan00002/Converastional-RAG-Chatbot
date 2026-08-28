# Conversational RAG System Demo Script

**Target duration:** 6–7 minutes  
**Demo URL:** Add the published video link here after recording  
**Repository URL:** Add the GitHub repository URL here

## 0:00–0:30 — Introduction

**Show:** Project title and running application.

**Say:**

“This is a conversational Retrieval-Augmented Generation system built with
LangChain, LangGraph, ChromaDB, SQLite, FastAPI, Streamlit, and Groq. It supports
technical document ingestion, semantic retrieval, multi-turn conversations,
persistent memory, and isolated sessions for multiple users.”

## 0:30–1:15 — Architecture and folder structure

**Show:** `README.md`, `docs/architecture.md`, and the project folder.

**Say:**

“The Streamlit interface communicates with FastAPI. FastAPI manages sessions,
uploads, and chat requests. Uploaded PDF, Markdown, or HTML documents are split
into chunks, embedded with `all-MiniLM-L6-v2`, and stored in ChromaDB. Conversation
messages are persisted in SQLite.”

“The main folders are:

- `app/` for configuration, ingestion, memory, API routes, and RAG orchestration
- `ui/` for the Streamlit interface
- `docs/` for architecture, deployment, benchmarking, FAQs, and sample technical documents
- `tests/` for automated tests
- `Dockerfile` and `docker-compose.yml` for container setup”

**Show:** The LangGraph diagram in `docs/architecture.md` or the Mermaid diagram
in `README.md`.

“The LangGraph flow contains explicit nodes for orchestration, query
understanding, query rewriting, retrieval routing, retrieval, context synthesis,
conversation summarization, and memory management.”

## 1:15–1:45 — Start the application and API documentation

**Show:** Two terminals.

**Terminal 1:**

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Terminal 2:**

```powershell
.venv\Scripts\python.exe -m streamlit run ui\streamlit_app.py
```

**Say:**

“The FastAPI server exposes OpenAPI documentation automatically at
`http://localhost:8000/docs`. The main endpoints are health, session creation,
session listing, session message history, document upload, and chat.”

**Show:** `http://localhost:8000/docs`, then open `/health`.

“The health endpoint confirms the Chroma vector database and the configured Groq
model, `openai/gpt-oss-20b`.”

## 1:45–2:45 — Document upload and indexing

**Show:** Streamlit upload control.

**Say:**

“I’ll create a new session before uploading a document. Each uploaded document is
associated with the active user and thread.”

1. Click **New session**.
2. Upload a Markdown, HTML, or text-based PDF document.
3. Click **Index document**.

“The upload endpoint extracts text, detects document type, title, version,
section headers, pages for PDFs, and fenced code blocks. The text is divided into
overlapping chunks and embedded before being persisted in the session’s Chroma
collection.”

“The original temporary upload file is removed after indexing. The indexed
embeddings remain in `data/chroma`.”

## 2:45–3:45 — Retrieval question

**Show:** Chat window.

**Ask:**

```text
What are the main deliverables?
```

or, for the FAISS sample:

```text
What is FAISS?
```

**Say:**

“The query is routed through the LangGraph workflow. The retrieval node searches
only the active user and thread collection. The context synthesis node passes the
retrieved chunks to Groq, which generates an answer grounded in the uploaded
document.”

“If semantic retrieval has no direct match, the application also uses a
thread-scoped fallback for recently indexed content and generic follow-up
questions.”

## 3:45–4:45 — Multi-turn conversation and query rewriting

**Ask:**

```text
What is FAISS?
```

Then ask:

```text
How is it different from Chroma?
```

Then ask:

```text
Which one provides metadata filtering?
```

**Say:**

“The second and third questions depend on earlier context. The query understanding
node detects conversational references, and the query rewriting node combines
recent history with the current question before retrieval.”

“This allows the assistant to resolve terms such as ‘it’, ‘this’, or ‘which one’
using the current conversation rather than treating every question as isolated.”

## 4:45–5:30 — Persistent memory and previous sessions

**Show:** The sidebar session list.

**Say:**

“Sessions are stored in SQLite. The oldest session is displayed as Session 1,
followed by Session 2 and later sessions. The actual thread ID is shown on the
main screen after a session is selected.”

1. Ask one question and note the answer.
2. Select another session.
3. Select the original session again.

“When I return to the original session, its persisted chat history is loaded.
The conversation context is restored, and follow-up questions continue with that
thread’s memory.”

“Documents are also isolated by user and thread. A new session cannot retrieve
documents uploaded to an older session.”

## 5:30–6:00 — Greeting and new-session reset

**Ask:**

```text
Hello
```

**Say:**

“Greetings are handled naturally by the query understanding node without
unnecessary document retrieval.”

1. Click **New session**.

“Creating a new session clears the visible chat, creates a new thread, and
reinitializes the screen. The new thread starts without the previous session’s
conversation or documents.”

## 6:00–6:40 — README, Docker, tests, and deliverables

**Show:** `README.md`, `requirements.txt`, `Dockerfile`, and `docker-compose.yml`.

**Say:**

“The README contains setup instructions for PowerShell, Command Prompt, and Git
Bash, API examples, architecture, sample conversations, and benchmark guidance.”

“Docker Compose includes the application, ChromaDB, and PostgreSQL services.
SQLite remains the default local memory store for this prototype.”

**Show:** Test terminal.

```powershell
.venv\Scripts\python.exe -m pytest -q
```

“The automated tests cover health, session chat, persisted message history,
thread-scoped document isolation, and the FAISS retrieval flow.”

## 6:40–7:00 — Closing

**Say:**

“This prototype demonstrates a complete conversational RAG workflow with
LangGraph orchestration, ChromaDB retrieval, Groq generation, persistent
conversation memory, multi-user session isolation, document metadata extraction,
FastAPI endpoints, and a functional Streamlit interface.”

“The final GitHub repository and recorded demo video link are included in the
submission materials.”
