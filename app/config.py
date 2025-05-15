import os
import logging
import chromadb
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    # API Settings
    API_TITLE = "Video Search API"
    API_VERSION = "1.0"
    API_DESCRIPTION = "基於 FastAPI 的影片搜尋 API"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", "8000"))

    # Database Settings
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        os.getenv("POSTGRES_URL", "postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@switchyard.proxy.rlwy.net:43353/railway")
    )
    
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    # ChromaDB Settings
    CHROMA_HOST = os.getenv("CHROMA_HOST", os.getenv("CHROMADB_URL", "localhost"))
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_URL = os.getenv("CHROMADB_URL", f"http://{CHROMA_HOST}:{CHROMA_PORT}")
    CHROMA_API_KEY = os.getenv("CHROMADB_API_KEY", os.getenv("CHROMA_API_KEY"))
    CHROMA_AUTH_ENABLED = os.getenv("CHROMA_AUTH_ENABLED", "false").lower() == "true"
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "video_embeddings")

    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS Settings
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE"]
    CORS_HEADERS: List[str] = ["*"]

    # Cache Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_EXPIRE_IN_SECONDS: int = int(os.getenv("CACHE_EXPIRE_IN_SECONDS", "3600"))

    def __init__(self):
        self._validate_settings()
        self._log_config()
    
    def _validate_settings(self):
        """驗證關鍵設定"""
        if not self.DATABASE_URL:
            raise ValueError("Database URL is not configured")
        if not self.CHROMA_URL:
            raise ValueError("ChromaDB URL is not configured")

    def _log_config(self):
        """記錄重要配置信息"""
        safe_db_url = self.DATABASE_URL.split("@")[-1] if self.DATABASE_URL else "Not configured"
        logger.info(f"Database URL: postgresql://*****@{safe_db_url}")
        logger.info(f"ChromaDB URL: {self.CHROMA_URL}")
        logger.info(f"API Version: {self.API_VERSION}")
        logger.info(f"Debug Mode: {self.DEBUG}")
        if "*" in self.CORS_ORIGINS:
            logger.warning("Warning: CORS is set to allow all origins (*)")

class ChromaDBClient:
    _instance = None
    _client = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ChromaDBClient()
        return cls._instance
    
    def __init__(self):
        try:
            kwargs = {
                "host": settings.CHROMA_HOST,
                "port": settings.CHROMA_PORT,
            }
            
            if settings.CHROMA_API_KEY:
                kwargs["api_key"] = settings.CHROMA_API_KEY
                
            self._client = chromadb.HttpClient(**kwargs)
            logger.info(f"ChromaDB client initialized with URL: {settings.CHROMA_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

settings = Settings()