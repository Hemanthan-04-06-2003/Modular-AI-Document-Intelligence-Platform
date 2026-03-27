from typing import Any, Iterable, List


class KeywordVectorStore:
    """Simple fallback retriever when vector dependencies are unavailable."""

    def __init__(self, chunks: Iterable[Any]):
        self._chunks = list(chunks)

    def similarity_search(self, query: str, k: int = 4) -> List[Any]:
        terms = [term.lower() for term in query.split() if term.strip()]

        def score(chunk: Any) -> int:
            content = getattr(chunk, "page_content", "").lower()
            return sum(content.count(term) for term in terms)

        ranked = sorted(self._chunks, key=score, reverse=True)
        return ranked[:k]


def create_vector_store(chunks: List[Any]) -> Any:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS

        embedding_model = HuggingFaceEmbeddings()
        return FAISS.from_documents(chunks, embedding_model)
    except Exception:
        return KeywordVectorStore(chunks)
