# RAG Knowledge Workspace

This project now uses a dedicated backend API and a custom web frontend instead of Streamlit.

## Backend status

- The original project logic was valid in spirit, but it was not a standalone backend.
- The old app mixed UI, upload, indexing, and question answering in one Streamlit file.
- It also depended on Python packages that are not currently installed in this environment.
- The original LLM path used `Ollama(model="llama3")`, but `ollama` is not installed locally here.

## New structure

- `backend/main.py`: FastAPI app with health, upload, chat, and feature endpoints.
- `backend/rag_service.py`: document ingestion, retrieval, and answer assembly.
- `frontend/`: elegant static UI served by the backend.

## Run

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open `http://127.0.0.1:8000`.

