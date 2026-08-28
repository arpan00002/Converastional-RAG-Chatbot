import re
import hashlib
from typing import TypedDict

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from .config import settings
from .ingestion import load_file, split_documents


class GraphState(TypedDict, total=False):
    question: str
    history: list[tuple[str, str]]
    user_id: str
    thread_id: str
    intent: str
    needs_history: bool
    rewritten_query: str
    retrieval_strategy: str
    documents: list[Document]
    context: str
    summary: str
    memory_decision: str
    answer: str


class RAG:
    """Conversational RAG with explicit, inspectable LangGraph agent nodes."""

    def __init__(self):
        self.vectorstore = None
        self.vectorstores = {}
        self.documents: list[Document] = []
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_chroma import Chroma

            embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
            self._embeddings = embeddings
            self._chroma_class = Chroma
        except Exception:
            # The keyword fallback keeps the API usable if embedding model startup
            # is unavailable; Chroma remains the configured production store.
            self.vectorstore = None

        graph = StateGraph(GraphState)
        graph.add_node("query_understanding", self._query_understanding)
        graph.add_node("query_rewriting", self._query_rewriting)
        graph.add_node("retrieval_router", self._retrieval_router)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("context_synthesis", self._context_synthesis)
        graph.add_node("conversation_summarization", self._conversation_summarization)
        graph.add_node("memory_management", self._memory_management)
        graph.add_node("orchestrator", self._orchestrator)
        graph.set_entry_point("orchestrator")
        graph.add_edge("orchestrator", "query_understanding")
        graph.add_conditional_edges(
            "query_understanding",
            lambda state: "query_rewriting" if state["needs_history"] else "retrieval_router",
        )
        graph.add_edge("query_rewriting", "retrieval_router")
        graph.add_edge("retrieval_router", "retrieve")
        graph.add_edge("retrieve", "context_synthesis")
        graph.add_edge("context_synthesis", "conversation_summarization")
        graph.add_edge("conversation_summarization", "memory_management")
        graph.add_edge("memory_management", END)
        self.graph = graph.compile()

    def _store_for(self, user_id: str, thread_id: str):
        key = f"{user_id}:{thread_id}"
        if key not in self.vectorstores:
            collection = "rag_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
            self.vectorstores[key] = self._chroma_class(
                persist_directory=settings.chroma_dir,
                collection_name=collection,
                embedding_function=self._embeddings,
            )
        return self.vectorstores[key]

    def ingest(self, path: str, user_id: str, thread_id: str) -> int:
        chunks = split_documents(load_file(path))
        for chunk in chunks:
            chunk.metadata["user_id"] = user_id
            chunk.metadata["thread_id"] = thread_id
            chunk.metadata["code_blocks"] = str(chunk.metadata.get("code_blocks", []))
            chunk.metadata["section_headers"] = str(chunk.metadata.get("section_headers", []))
        self.documents.extend(chunks)
        if self._chroma_available():
            self._store_for(user_id, thread_id).add_documents(chunks)
        return len(chunks)

    def retrieve(self, query: str, user_id: str = "", thread_id: str = "") -> list[Document]:
        scoped = [
            doc for doc in self.documents
            if doc.metadata.get("user_id") == user_id
            and doc.metadata.get("thread_id") == thread_id
        ]
        if self._chroma_available() and user_id and thread_id:
            store = self._store_for(user_id, thread_id)
            try:
                filtered = store.similarity_search(query, k=settings.top_k)
            except (ValueError, RuntimeError):
                filtered = []
            if filtered:
                return filtered
            # Query broadly for records written by a previous API process, then
            # enforce ownership in Python. This also supports generic follow-ups
            # such as "explain" that have little lexical overlap with a document.
            try:
                candidates = store.similarity_search(
                    query,
                    k=max(settings.top_k * 5, 20),
                )
                if candidates:
                    return candidates[: settings.top_k]
            except (ValueError, RuntimeError):
                pass
            # Chroma can return no result while newly-added chunks are still
            # being indexed; rank the same thread's local chunks below.
        terms = set(query.lower().split())
        normalized_query = query.lower().replace("?", "").strip()
        if "resume" in normalized_query or "summary" in normalized_query or "summar" in normalized_query:
            terms.update({"name", "resume", "experience", "skills", "summary", "profile"})
        ranked = sorted(
            scoped,
            key=lambda doc: len(terms & set(doc.page_content.lower().split())),
            reverse=True,
        )
        return ranked[: settings.top_k]

    def _chroma_available(self) -> bool:
        return self.vectorstore is not None or hasattr(self, "_chroma_class")

    def answer(self, question: str, history: list[tuple[str, str]], user_id: str, thread_id: str) -> str:
        return self.graph.invoke(
            {"question": question, "history": history, "user_id": user_id, "thread_id": thread_id}
        )["answer"]

    def _orchestrator(self, state: GraphState) -> GraphState:
        return state

    def _query_understanding(self, state: GraphState) -> GraphState:
        question = state["question"].lower().strip()
        greeting_pattern = r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)([\s!.?,]|$)"
        if re.match(greeting_pattern, question):
            return {"intent": "greeting", "needs_history": False}
        context_words = ("it", "this", "that", "they", "previous", "earlier", "above")
        return {
            "intent": "question",
            "needs_history": bool(state.get("history")) and any(
                word in question.split() for word in context_words
            ),
        }

    def _query_rewriting(self, state: GraphState) -> GraphState:
        history = state.get("history", [])
        recent = " ".join(content for _, content in history[-4:])
        return {"rewritten_query": f"{recent}\nCurrent question: {state['question']}"}

    def _retrieval_router(self, state: GraphState) -> GraphState:
        query = state.get("rewritten_query", state["question"])
        strategy = "semantic_code_search" if "code" in query.lower() or "example" in query.lower() else "semantic_search"
        return {"retrieval_strategy": strategy, "rewritten_query": query}

    def _retrieve(self, state: GraphState) -> GraphState:
        return {
            "documents": self.retrieve(
                state.get("rewritten_query", state["question"]),
                state.get("user_id", ""),
                state.get("thread_id", ""),
            )
        }

    def _context_synthesis(self, state: GraphState) -> GraphState:
        if state.get("intent") == "greeting":
            return {
                "context": "",
                "answer": "Hello! I can help you find answers in the indexed technical documentation. What would you like to know?",
            }
        documents = state.get("documents", [])
        context = "\n\n".join(
            f"[Document: {doc.metadata.get('source', 'uploaded document')}]\n{doc.page_content}"
            for doc in documents
        )
        history = "\n".join(f"{role}: {content}" for role, content in state.get("history", [])[-6:])
        if not documents:
            return {
                "context": "",
                "answer": "I could not find relevant information in this session's uploaded documents.",
            }
        if settings.groq_api_key:
            from langchain_groq import ChatGroq

            llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful documentation assistant. Answer using the supplied context. "
                        "The context is authoritative: extract names, ownership, dates, and facts directly "
                        "from it. For a summary request, provide 3-6 concise key points. For questions about "
                        "a resume or document, identify the person only if their name appears in the context. "
                        "Never claim the context is empty when it contains relevant text. If the answer truly "
                        "is not present, say so plainly.\nHistory:\n{history}\nContext:\n{context}",
                    ),
                    ("human", "{question}"),
                ]
            )
            answer = llm.invoke(prompt.format_messages(history=history, context=context, question=state["question"])).content
        else:
            terms = set(state["question"].lower().split())
            sentences = [s.strip() for s in context.replace("\n", " ").split(".") if s.strip()]
            hits = [sentence for sentence in sentences if terms & set(sentence.lower().split())]
            answer = (". ".join(hits[:4]) or "I could not find that in the indexed documents.") + ("." if hits else "")
        return {"context": context, "answer": answer}

    def _conversation_summarization(self, state: GraphState) -> GraphState:
        history = state.get("history", [])
        summary = " ".join(content for _, content in history[-8:])
        return {"summary": summary[:2000]}

    def _memory_management(self, state: GraphState) -> GraphState:
        return {"memory_decision": "retain_recent_turns_and_summary"}
