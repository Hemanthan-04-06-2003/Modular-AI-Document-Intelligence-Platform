from pathlib import Path
from typing import Any, List

from .config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


def load_and_split(file_path: str | Path) -> List[Any]:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    loader = PyPDFLoader(str(file_path))
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)
