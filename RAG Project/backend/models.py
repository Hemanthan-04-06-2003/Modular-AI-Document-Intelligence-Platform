from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    ollama_available: bool
    vector_backend_available: bool
    loaded_documents: int


class DocumentSummary(BaseModel):
    doc_id: str
    name: str
    chunk_count: int
    uploaded_at: datetime


class UploadResponse(BaseModel):
    document: DocumentSummary
    total_documents: int


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class SigninRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)




class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    new_password: str = Field(..., min_length=6, max_length=128)


class UserProfile(BaseModel):
    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)
    doc_id: Optional[str] = None


class SourceChunk(BaseModel):
    document: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    mode: str
    sources: List[SourceChunk]


class FeatureIdea(BaseModel):
    title: str
    description: str
    priority: str
