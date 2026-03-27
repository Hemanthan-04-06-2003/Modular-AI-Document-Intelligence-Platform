from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import create_access_token, decode_access_token, hash_password, verify_password
from .config import FRONTEND_DIR, LLM_PROVIDER
from .db import get_auth_connection, get_user_connection, init_auth_db, init_user_db, user_storage_dir
from .llm import is_ollama_available
from .models import (
    AuthResponse,
    ChatRequest,
    ChatResponse,
    FeatureIdea,
    HealthResponse,
    ResetPasswordRequest,
    SigninRequest,
    SignupRequest,
    UploadResponse,
    UserProfile,
)
from .rag_service import RAGService


app = FastAPI(title="RAG Knowledge Workspace", version="2.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_auth_db()
service = RAGService()


def _owner_id(user_id: int) -> str:
    return f"user-{user_id}"


def _ensure_user_workspace(user_id: int) -> None:
    init_user_db(user_id)
    service.load_user_documents(_owner_id(user_id), user_storage_dir(user_id))


def get_current_user(authorization: str | None = Header(default=None)) -> UserProfile:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from None

    with get_auth_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="User not found.")

    _ensure_user_workspace(user_id)
    return UserProfile(id=row["id"], name=row["name"], email=row["email"])


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest) -> AuthResponse:
    email = payload.email.strip().lower()
    created_at = datetime.now(UTC).isoformat()

    with get_auth_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing is not None:
            raise HTTPException(status_code=400, detail="Email is already registered.")

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name.strip(), email, hash_password(payload.password), created_at),
        )
        conn.commit()
        user_id = int(cursor.lastrowid)

    init_user_db(user_id)
    user = UserProfile(id=user_id, name=payload.name.strip(), email=email)
    token = create_access_token(user_id=user.id, email=user.email)
    return AuthResponse(access_token=token, user=user)


@app.post("/api/auth/signin", response_model=AuthResponse)
def signin(payload: SigninRequest) -> AuthResponse:
    email = payload.email.strip().lower()
    with get_auth_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    init_user_db(int(row["id"]))
    user = UserProfile(id=row["id"], name=row["name"], email=row["email"])
    token = create_access_token(user_id=user.id, email=user.email)
    return AuthResponse(access_token=token, user=user)


@app.post("/api/auth/reset-password")
def reset_password(payload: ResetPasswordRequest):
    email = payload.email.strip().lower()
    with get_auth_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Account not found for that email.")
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (hash_password(payload.new_password), email),
        )
        conn.commit()
    return {"status": "ok", "message": "Password updated successfully."}

@app.get("/api/auth/me", response_model=UserProfile)
def me(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    return current_user


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_provider=LLM_PROVIDER,
        ollama_available=is_ollama_available(),
        vector_backend_available=service.vector_backend_ready(),
        loaded_documents=service.document_count(),
    )


@app.get("/api/documents")
def list_documents(current_user: UserProfile = Depends(get_current_user)):
    return service.list_documents(_owner_id(current_user.id))


@app.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
) -> UploadResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    storage_dir = user_storage_dir(current_user.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / file.filename
    content = await file.read()
    destination.write_bytes(content)

    doc_id = f"doc-{uuid4().hex[:8]}"
    owner_id = _owner_id(current_user.id)
    document = service.ingest_pdf(owner_id=owner_id, doc_id=doc_id, file_name=file.filename, file_path=destination)

    with get_user_connection(current_user.id) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents (doc_id, name, file_path, chunk_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document.doc_id, document.name, str(destination), document.chunk_count, document.uploaded_at.isoformat()),
        )
        conn.commit()

    return UploadResponse(document=document, total_documents=service.document_count(owner_id))


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, current_user: UserProfile = Depends(get_current_user)):
    owner_id = _owner_id(current_user.id)
    try:
        record = service.delete_document(owner_id, doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.") from None

    file_path = user_storage_dir(current_user.id) / Path(record["path"]).name
    if file_path.exists():
        file_path.unlink()

    with get_user_connection(current_user.id) as conn:
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()

    return {"status": "ok", "message": "Document removed.", "remaining_documents": service.document_count(owner_id)}


@app.post("/api/chat", response_model=ChatResponse)
def ask_question(
    payload: ChatRequest,
    current_user: UserProfile = Depends(get_current_user),
) -> ChatResponse:
    owner_id = _owner_id(current_user.id)
    if service.document_count(owner_id) == 0:
        raise HTTPException(status_code=400, detail="Upload at least one PDF before asking questions.")

    try:
        response = service.ask(owner_id=owner_id, question=payload.question, doc_id=payload.doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.") from None

    with get_user_connection(current_user.id) as conn:
        conn.execute(
            """
            INSERT INTO chat_history (question, answer, created_at)
            VALUES (?, ?, ?)
            """,
            (payload.question, response.answer, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    return response


@app.get("/api/feature-ideas", response_model=list[FeatureIdea])
def feature_ideas() -> list[FeatureIdea]:
    return [
        FeatureIdea(
            title="Multi-document workspace",
            description="Query across multiple PDFs with document filters, source confidence, and per-file citations.",
            priority="high",
        ),
        FeatureIdea(
            title="Saved conversations",
            description="Persist question history, answers, and uploaded files directly inside each user's private workspace DB.",
            priority="high",
        ),
        FeatureIdea(
            title="Insight extraction",
            description="Generate summaries, key points, definitions, and quiz cards directly from the uploaded material.",
            priority="medium",
        ),
        FeatureIdea(
            title="Admin observability",
            description="Track indexing time, chunk counts, model status, and retrieval latency from a lightweight dashboard.",
            priority="medium",
        ),
    ]


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")

    @app.get("/")
    def serve_frontend() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "login.html")

    @app.get("/login")
    def serve_login() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "login.html")

    @app.get("/app")
    def serve_app() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "app.html")
