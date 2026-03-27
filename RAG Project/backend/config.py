from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
AUTH_DB_PATH = BASE_DIR / "auth.db"
STORAGE_DIR = BASE_DIR / "storage"

DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "700"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

LLM_PROVIDER = os.getenv("RAG_LLM_PROVIDER", "ollama").lower()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
AUTH_SECRET = os.getenv("RAG_AUTH_SECRET", "change-this-secret-in-production")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("RAG_TOKEN_EXPIRE_HOURS", "24"))
