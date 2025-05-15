# 載入必要的套件
import os
import logging
import chromadb
from typing import List
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 設定日誌系統
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    # API 基本設定
    API_TITLE = "Video Search API"
    API_VERSION = "1.0"
    API_DESCRIPTION = "基於 FastAPI 的影片搜尋 API"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Railway 會自動設定 PORT 環境變數
    PORT = int(os.getenv("PORT", "8000"))

    # 資料庫設定
    # 優先使用 DATABASE_URL，若無則使用 POSTGRES_URL
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        os.getenv("POSTGRES_URL", "postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@switchyard.proxy.rlwy.net:43353/railway")
    )
    
    # 資料庫連線池設定
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))      # 連線池大小
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10")) # 最大溢出連線數
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30")) # 連線超時時間
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800")) # 連線回收時間

    # ChromaDB 設定
    # 使用 Railway 內部網絡地址
    CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma.railway.internal")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    
    # 內部網絡 URL
    CHROMA_INTERNAL_URL = f"http://{CHROMA_HOST}:{CHROMA_PORT}"
    # 外部網絡 URL (用於日誌和調試)
    CHROMA_PUBLIC_URL = "https://chroma-production-84ca.up.railway.app"
    
    # 實際使用內部 URL
    CHROMA_URL = CHROMA_INTERNAL_URL
    
    # 使用對應的服務名稱
    CHROMA_SERVICE_NAME = "chroma"
    CHROMA_PROJECT_ID = os.getenv("RAILWAY_PROJECT_ID")
    CHROMA_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")
    
    # 停用遙測
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    
    # 其他 ChromaDB 設定
    CHROMA_API_KEY = os.getenv("CHROMADB_API_KEY")
    
    # 重試設定
    CHROMA_RETRIES = int(os.getenv("CHROMA_RETRIES", "5"))
    CHROMA_RETRY_DELAY = int(os.getenv("CHROMA_RETRY_DELAY", "5"))

    # 安全性設定
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS 設定（跨域資源共享）
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE"]
    CORS_HEADERS: List[str] = ["*"]

    # 快取設定
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_EXPIRE_IN_SECONDS: int = int(os.getenv("CACHE_EXPIRE_IN_SECONDS", "3600"))

    def __init__(self):
        """初始化設定並進行驗證"""
        self._validate_settings()
        self._log_config()
    
    def _validate_settings(self):
        """驗證關鍵設定是否正確配置"""
        if not self.DATABASE_URL:
            raise ValueError("Database URL is not configured")
        if not self.CHROMA_URL:
            raise ValueError("ChromaDB URL is not configured")

    def _log_config(self):
        """記錄重要配置信息，但隱藏敏感資訊"""
        # 移除資料庫 URL 中的敏感資訊
        safe_db_url = self.DATABASE_URL.split("@")[-1] if self.DATABASE_URL else "Not configured"
        logger.info(f"Database URL: postgresql://*****@{safe_db_url}")
        logger.info(f"ChromaDB URL: {self.CHROMA_URL}")
        logger.info(f"ChromaDB Service: {self.CHROMA_SERVICE_NAME}")
        logger.info(f"ChromaDB Environment: {self.CHROMA_ENVIRONMENT}")
        logger.info(f"API Version: {self.API_VERSION}")
        logger.info(f"Debug Mode: {self.DEBUG}")
        logger.info(f"Attempting to connect to ChromaDB at: {self.CHROMA_URL}")
        logger.info(f"ChromaDB Host: {self.CHROMA_HOST}")
        logger.info(f"ChromaDB Service Name: {self.CHROMA_SERVICE_NAME}")
        logger.info(f"ChromaDB Internal URL: {self.CHROMA_INTERNAL_URL}")
        logger.info(f"ChromaDB Public URL: {self.CHROMA_PUBLIC_URL}")
        # 警告如果 CORS 設定為允許所有來源
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

# 建立全域設定實例
settings = Settings()