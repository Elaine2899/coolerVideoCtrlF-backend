from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import datetime

from .config import settings
from .db import get_db, init_db
from .api import video_router, chroma_router
from .chroma_client import ChromaDBClient

# 創建 FastAPI 實例
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    debug=settings.DEBUG
)

# 設定 CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# 應用啟動時執行的函數
@app.on_event("startup")
async def startup():
    # 初始化資料庫
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

    # 初始化 ChromaDB 連線
    try:
        ChromaDBClient.get_instance()
        print("ChromaDB connection initialized successfully")
    except Exception as e:
        print(f"ChromaDB connection error: {e}")
        raise

# 註冊路由
app.include_router(video_router)
app.include_router(chroma_router)

# 健康檢查端點
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"status": "Database connection successful"}

@app.get("/chroma-check")
def chroma_check():
    try:
        client = ChromaDBClient.get_instance().get_client()
        collections = client.list_collections()
        return {
            "status": "ChromaDB connection successful",
            "collections": [c.name for c in collections]
        }
    except Exception as e:
        return {
            "status": "ChromaDB connection failed",
            "error": str(e)
        }

# 根路由
@app.get("/")
async def root():
    return {
        "message": "Video Search API 運行中",
        "version": settings.API_VERSION
    }