import os, tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from .memory import Memory
from .rag import RAG
from .config import settings

app=FastAPI(title="Conversational RAG API",version="1.0.0")
memory=Memory(); rag=RAG()
class SessionIn(BaseModel): user_id: str
class ChatIn(BaseModel): user_id: str; thread_id: str; message: str

@app.get("/health")
def health():
    provider = "openai" if settings.openai_api_key else ("groq" if settings.groq_api_key else "local")
    return {
        "status": "ok",
        "vector_db": settings.vector_db,
        "embedding_model": settings.embedding_model,
        "llm": provider,
        "model": settings.groq_model if provider == "groq" else None,
    }
@app.post("/sessions")
def create_session(x:SessionIn): return {"thread_id":memory.create(x.user_id),"user_id":x.user_id}
@app.get("/sessions/{user_id}")
def list_sessions(user_id:str): return {"sessions":memory.sessions(user_id)}

@app.get("/sessions/{user_id}/{thread_id}/messages")
def session_messages(user_id: str, thread_id: str):
    if not memory.has_session(user_id, thread_id):
        raise HTTPException(404, "Unknown session")
    return {
        "thread_id": thread_id,
        "messages": [
            {"role": role, "content": content}
            for role, content in memory.history(thread_id, limit=100)
        ],
    }
@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    thread_id: str = Form(...),
):
    if not file.filename.lower().endswith((".pdf",".md",".markdown",".html",".htm")): raise HTTPException(400,"Only PDF, Markdown, and HTML are supported")
    data=await file.read()
    with tempfile.NamedTemporaryFile(delete=False,suffix=os.path.splitext(file.filename)[1]) as f: f.write(data); path=f.name
    if not any(s["thread_id"] == thread_id for s in memory.sessions(user_id)):
        raise HTTPException(404, "Unknown session")
    try:
        chunks = rag.ingest(path, user_id, thread_id)
        return {
            "filename": file.filename,
            "chunks": chunks,
            "status": "indexed",
            "user_id": user_id,
            "thread_id": thread_id,
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally: os.unlink(path)
@app.post("/chat")
def chat(x:ChatIn):
    if not memory.has_session(x.user_id, x.thread_id): raise HTTPException(404,"Unknown session")
    memory.add(x.thread_id,x.user_id,"user",x.message); answer=rag.answer(x.message,memory.history(x.thread_id), x.user_id, x.thread_id); memory.add(x.thread_id,x.user_id,"assistant",answer)
    return {"thread_id":x.thread_id,"answer":answer}
