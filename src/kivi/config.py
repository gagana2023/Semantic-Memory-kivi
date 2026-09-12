from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("KIVI_DATABASE_PATH", "kivi.db")
    ollama_url: str = os.getenv("KIVI_OLLAMA_URL", "http://127.0.0.1:11434")
    extraction_model: str = os.getenv("KIVI_EXTRACTION_MODEL", "qwen3:8b")
    embedding_model: str = os.getenv("KIVI_EMBEDDING_MODEL", "nomic-embed-text")
    extraction_retry_cap: int = int(os.getenv("KIVI_EXTRACTION_RETRY_CAP", "3"))
    review_url: str = os.getenv("KIVI_REVIEW_URL", "http://127.0.0.1:8000")
    random_seed: int = int(os.getenv("KIVI_RANDOM_SEED", "7"))
