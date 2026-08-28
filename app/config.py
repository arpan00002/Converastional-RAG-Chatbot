from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    vector_db: str = "chroma"
    chroma_dir: str = "data/chroma"
    sqlite_path: str = "data/memory.db"
    top_k: int = 4
    embedding_model: str = "all-MiniLM-L6-v2"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "openai/gpt-oss-20b"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    pinecone_api_key: str | None = None
    pinecone_index: str | None = None

    def ensure_dirs(self):
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.chroma_dir).parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_dirs()
