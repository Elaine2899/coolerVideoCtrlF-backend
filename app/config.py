import os
from typing import List
from dotenv import load_dotenv
import logging

# 設定基本日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

class Settings:
    # API 設定
    API_VERSION = "1.0.0"
    API_TITLE = "Video Search API"
    API_DESCRIPTION = "基於 FastAPI 的影片搜尋 API"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # 資料庫設定
    DATABASE_URL = (
        os.getenv("DATABASE_URL") or 
        os.getenv("DATABASE_PUBLIC_URL") or 
        "postgresql://postgres:postgres@railway.railway.internal:5432/railway"
    )
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    
    # ChromaDB 設定
    CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "video_embeddings")
    
    # CORS 設定
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE"]
    CORS_HEADERS: List[str] = ["*"]
    
    # 安全性設定
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 快取設定
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_EXPIRE_IN_SECONDS: int = int(os.getenv("CACHE_EXPIRE_IN_SECONDS", "3600"))

    def __init__(self):
        # 移除敏感資訊
        safe_db_url = self.DATABASE_URL.replace(
            self.DATABASE_URL.split("@")[0], "postgresql://****:****"
        )
        logger.info(f"Using Database URL: {safe_db_url}")
        self._log_config()
    
    def _log_config(self):
        """記錄重要配置信息"""
        logger.info(f"API Version: {self.API_VERSION}")
        logger.info(f"Debug Mode: {self.DEBUG}")
        logger.info(f"Database URL: {self.DATABASE_URL}")
        logger.info(f"ChromaDB: {self.CHROMA_HOST}:{self.CHROMA_PORT}")
        if "*" in self.CORS_ORIGINS:
            logger.warning("Warning: CORS is set to allow all origins (*)")

settings = Settings()