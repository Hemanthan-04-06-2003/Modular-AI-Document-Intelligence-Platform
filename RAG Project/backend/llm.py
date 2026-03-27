from dataclasses import dataclass

from .config import LLM_PROVIDER, OLLAMA_MODEL


@dataclass
class GenerationResult:
    answer: str
    mode: str


def get_ollama_llm_class():
    try:
        from langchain_ollama import OllamaLLM

        return OllamaLLM
    except Exception:
        try:
            from langchain_community.llms import Ollama

            return Ollama
        except Exception:
            return None


def is_ollama_available() -> bool:
    return get_ollama_llm_class() is not None


def generate_answer(question: str, context: str) -> GenerationResult:
    ollama_llm_class = get_ollama_llm_class()

    if LLM_PROVIDER == "ollama" and ollama_llm_class is not None:
        llm = ollama_llm_class(model=OLLAMA_MODEL)
        prompt = f"""
You are a precise RAG assistant. Use only the supplied context.
If the answer is not present, say that clearly.

Context:
{context}

Question:
{question}
"""
        try:
            return GenerationResult(answer=llm.invoke(prompt), mode="llm")
        except Exception:
            pass

    preview = context[:1200].strip() or "No matching context was found."
    return GenerationResult(
        answer=(
            "LLM provider is not available yet, so this is a retrieval-only response.\n\n"
            f"Question: {question}\n\n"
            f"Best matching context:\n{preview}"
        ),
        mode="retrieval-only",
    )
