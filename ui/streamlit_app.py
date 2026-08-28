import requests
import streamlit as st


st.set_page_config(page_title="Conversational RAG", page_icon="💬")


def api_request(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{BASE}{path}", timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error(
            f"Cannot connect to the FastAPI server at {BASE}. "
            "Start it in a separate terminal with: "
            "`uvicorn app.main:app --reload`"
        )
        st.stop()
    except requests.RequestException as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        st.error(f"API request failed: {detail}")
        st.stop()


def load_thread_messages(thread_id: str):
    return api_request(
        "GET",
        f"/sessions/{user}/{thread_id}/messages",
    )["messages"]


BASE = st.sidebar.text_input("API URL", "http://localhost:8000").rstrip("/")
user = st.sidebar.text_input("User ID", "demo").strip() or "demo"

health = api_request("GET", "/health")
st.sidebar.success(f"API connected ({health['vector_db']} / {health['llm']})")

sessions = api_request("GET", f"/sessions/{user}")["sessions"]

if "thread" not in st.session_state:
    session = api_request("POST", "/sessions", json={"user_id": user})
    st.session_state.thread = session["thread_id"]
    st.session_state.messages = []
    st.rerun()

if st.sidebar.button("New session"):
    session = api_request("POST", "/sessions", json={"user_id": user})
    st.session_state.thread = session["thread_id"]
    st.session_state.messages = []
    st.rerun()

st.title("Conversational RAG")
st.caption(f"Session ID: `{st.session_state.thread}`")

st.sidebar.caption(f"{len(sessions)} session(s) for {user}")
if sessions:
    sessions = list(reversed(sessions))
    session_ids = [item["thread_id"] for item in sessions]
    session_labels = {
        thread_id: f"Session {index}"
        for index, thread_id in enumerate(session_ids, start=1)
    }
    selected_label = st.sidebar.selectbox(
        "Previous sessions",
        list(session_labels.values()),
        index=session_ids.index(st.session_state.thread) if st.session_state.thread in session_ids else 0,
    )
    selected = next(
        thread_id for thread_id, label in session_labels.items()
        if label == selected_label
    )
    if selected != st.session_state.thread:
        st.session_state.thread = selected
        st.session_state.messages = load_thread_messages(selected)
        st.rerun()

uploaded = st.file_uploader(
    "Upload PDF, Markdown, or HTML",
    type=["pdf", "md", "markdown", "html", "htm"],
)
if uploaded and st.button("Index document"):
    result = api_request(
        "POST",
        "/upload",
        files={"file": (uploaded.name, uploaded.getvalue())},
        data={"user_id": user, "thread_id": st.session_state.thread},
    )
    st.success(f"Indexed {result['chunks']} chunks from {result['filename']}.")
    st.info("The document is now available only in this session.")

for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask a question about your documentation")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    result = api_request(
        "POST",
        "/chat",
        json={
            "user_id": user,
            "thread_id": st.session_state.thread,
            "message": question,
        },
    )
    answer = result["answer"]
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)
