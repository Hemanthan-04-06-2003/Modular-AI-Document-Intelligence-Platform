import sqlite3
from pathlib import Path

from .config import AUTH_DB_PATH, STORAGE_DIR


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_auth_connection() -> sqlite3.Connection:
    return _connect(AUTH_DB_PATH)


def user_storage_dir(user_id: int) -> Path:
    return STORAGE_DIR / f"user-{user_id}"


def user_db_path(user_id: int) -> Path:
    return user_storage_dir(user_id) / "workspace.db"


def get_user_connection(user_id: int) -> sqlite3.Connection:
    return _connect(user_db_path(user_id))


def init_auth_db() -> None:
    with get_auth_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def init_user_db(user_id: int) -> None:
    storage_dir = user_storage_dir(user_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    with get_user_connection(user_id) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
