import re
from pathlib import Path
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_file(path: str) -> list[Document]:
    p=Path(path); ext=p.suffix.lower()
    if ext==".pdf":
        from pypdf import PdfReader
        documents = [
            Document(
                page_content=x.extract_text() or "",
                metadata={"source":p.name, "document_type": "pdf", "page": i + 1},
            )
            for i, x in enumerate(PdfReader(path).pages)
        ]
        if not any(doc.page_content.strip() for doc in documents):
            raise ValueError(
                "PDF contains no extractable text. It may be scanned or malformed; "
                "upload a text-based PDF or Markdown/HTML document."
            )
        return documents
    raw=p.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html",".htm"):
        soup=BeautifulSoup(raw,"html.parser"); title=soup.title.string if soup.title else p.stem; text=soup.get_text("\n")
    else: title=p.stem; text=raw
    blocks=re.findall(r"```(?:\w+)?\s*(.*?)```",raw,re.S)
    headings = re.findall(r"^\s*(?:#{1,6}\s+|<h[1-6][^>]*>)(.*?)(?:</h[1-6]>)?\s*$", raw, re.M | re.I)
    version_match = re.search(r"\bversion\s*[:=]?\s*([0-9]+(?:\.[0-9]+)*)", raw, re.I)
    return [Document(page_content=text, metadata={
        "source": p.name,
        "title": title,
        "document_type": "html" if ext in (".html", ".htm") else "markdown",
        "version": version_match.group(1) if version_match else "unspecified",
        "section_headers": headings,
        "code_blocks": blocks,
    })]

def split_documents(docs):
    splitter=RecursiveCharacterTextSplitter(chunk_size=900,chunk_overlap=120)
    return splitter.split_documents(docs)
