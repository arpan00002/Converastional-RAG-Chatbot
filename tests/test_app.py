from fastapi.testclient import TestClient
from app.main import app, rag
def test_health():
    r=TestClient(app).get("/health"); assert r.status_code==200 and r.json()["status"]=="ok"
def test_session_and_chat():
    c=TestClient(app); s=c.post("/sessions",json={"user_id":"test"}).json()
    r=c.post("/chat",json={"user_id":"test","thread_id":s["thread_id"],"message":"hello"})
    assert r.status_code==200 and "answer" in r.json()
    history = c.get(f"/sessions/test/{s['thread_id']}/messages")
    assert history.status_code == 200
    assert [item["role"] for item in history.json()["messages"]] == ["user", "assistant"]

def test_documents_are_thread_scoped():
    c = TestClient(app)
    first = c.post("/sessions", json={"user_id": "scope-test"}).json()["thread_id"]
    second = c.post("/sessions", json={"user_id": "scope-test"}).json()["thread_id"]
    upload = c.post(
        "/upload",
        files={"file": ("private.md", b"# Private\nThis is only for the first session.")},
        data={"user_id": "scope-test", "thread_id": first},
    )
    assert upload.status_code == 200
    assert upload.json()["status"] == "indexed"
    assert not rag.retrieve("What is private?", "scope-test", second)
    assert rag.retrieve("whose resume is this?", "scope-test", first)
    assert rag.retrieve("explain", "scope-test", first)

def test_faiss_question_uses_uploaded_context():
    c = TestClient(app)
    session = c.post("/sessions", json={"user_id": "faiss-answer-test"}).json()
    text = b"FAISS is a raw indexing library focused on vector similarity calculations."
    upload = c.post(
        "/upload",
        files={"file": ("vector-db.md", text)},
        data={"user_id": "faiss-answer-test", "thread_id": session["thread_id"]},
    )
    assert upload.status_code == 200
    response = c.post(
        "/chat",
        json={
            "user_id": "faiss-answer-test",
            "thread_id": session["thread_id"],
            "message": "what is faiss",
        },
    )
    assert response.status_code == 200
    assert "raw indexing library" in response.json()["answer"].lower()
