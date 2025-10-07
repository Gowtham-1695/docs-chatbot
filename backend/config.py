import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Configuration
    HF_API_KEY: str = os.getenv("HF_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # File Upload Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    
    # RAG Configuration
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    MAX_CHUNKS_FOR_CONTEXT: int = int(os.getenv("MAX_CHUNKS_FOR_CONTEXT", "5"))
    
    # Model Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "microsoft/DialoGPT-medium")
    
    # Hugging Face API URLs
    HF_INFERENCE_URL: str = "https://api-inference.huggingface.co/models"

settings = Settings()