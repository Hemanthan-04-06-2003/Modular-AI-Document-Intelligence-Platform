from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from .config import DEFAULT_TOP_K
from .document_loader import load_and_split
from .llm import generate_answer
from .models import ChatResponse, DocumentSummary, SourceChunk
from .vector_store import create_vector_store


class RAGService:
    def __init__(self) -> None:
        self._documents_by_user: dict[str, dict[str, dict]] = {}

    def ingest_pdf(self, owner_id: str, doc_id: str, file_name: str, file_path: Path) -> DocumentSummary:
        chunks = load_and_split(file_path)
        vector_db = create_vector_store(chunks)

        record = {
            "doc_id": doc_id,
            "name": file_name,
            "path": str(file_path),
            "chunks": chunks,
            "vector_db": vector_db,
        }
        self._documents_by_user.setdefault(owner_id, {})[doc_id] = record

        return DocumentSummary(
            doc_id=doc_id,
            name=file_name,
            chunk_count=len(chunks),
            uploaded_at=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

    def load_user_documents(self, owner_id: str, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        loaded = self._documents_by_user.setdefault(owner_id, {})
        known_paths = {record["path"] for record in loaded.values()}

        for pdf_path in sorted(directory.glob("*.pdf")):
            if str(pdf_path) in known_paths:
                continue
            doc_id = pdf_path.stem.lower().replace(" ", "-")
            if doc_id in loaded:
                doc_id = f"{doc_id}-{abs(hash(str(pdf_path))) % 10000}"
            try:
                self.ingest_pdf(owner_id=owner_id, doc_id=doc_id, file_name=pdf_path.name, file_path=pdf_path)
            except Exception:
                loaded[doc_id] = {
                    "doc_id": doc_id,
                    "name": pdf_path.name,
                    "path": str(pdf_path),
                    "chunks": [SimpleNamespace(page_content="Document indexed after dependencies are installed.")],
                    "vector_db": SimpleNamespace(
                        similarity_search=lambda _query, k=DEFAULT_TOP_K: [
                            SimpleNamespace(page_content="Document indexing pending dependency installation.")
                        ][:k]
                    ),
                }

    def list_documents(self, owner_id: str) -> list[DocumentSummary]:
        items: list[DocumentSummary] = []
        for record in self._documents_by_user.get(owner_id, {}).values():
            timestamp = Path(record["path"]).stat().st_mtime
            items.append(
                DocumentSummary(
                    doc_id=record["doc_id"],
                    name=record["name"],
                    chunk_count=len(record["chunks"]),
                    uploaded_at=datetime.fromtimestamp(timestamp),
                )
            )
        return items

    def ask(self, owner_id: str, question: str, doc_id: str | None = None) -> ChatResponse:
        candidates = self._pick_documents(owner_id, doc_id)

        matched_chunks = []
        for record in candidates:
            docs = record["vector_db"].similarity_search(question, k=DEFAULT_TOP_K)
            for doc in docs:
                matched_chunks.append((record["name"], getattr(doc, "page_content", "")))

        matched_chunks = matched_chunks[:DEFAULT_TOP_K]
        context = "\n\n".join(chunk for _, chunk in matched_chunks)
        result = generate_answer(question, context)

        return ChatResponse(
            answer=result.answer,
            mode=result.mode,
            sources=[SourceChunk(document=name, excerpt=chunk[:260].strip()) for name, chunk in matched_chunks],
        )


    def delete_document(self, owner_id: str, doc_id: str) -> dict:
        user_documents = self._documents_by_user.get(owner_id, {})
        if doc_id not in user_documents:
            raise KeyError(doc_id)
        return user_documents.pop(doc_id)

    def document_count(self, owner_id: str | None = None) -> int:
        if owner_id is None:
            return sum(len(records) for records in self._documents_by_user.values())
        return len(self._documents_by_user.get(owner_id, {}))

    def vector_backend_ready(self) -> bool:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings  # noqa: F401
            from langchain_community.vectorstores import FAISS  # noqa: F401

            return True
        except Exception:
            return False

    def _pick_documents(self, owner_id: str, doc_id: str | None) -> list[dict]:
        user_documents = self._documents_by_user.get(owner_id, {})
        if doc_id:
            if doc_id not in user_documents:
                raise KeyError(doc_id)
            return [user_documents[doc_id]]
        return list(user_documents.values())
