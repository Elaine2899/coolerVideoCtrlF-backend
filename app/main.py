from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import datetime
import logging
import os

# 修改導入方式
from app.config import settings
from app.db import get_db, init_db
from app.api import video_router, chroma_router
from app.chroma_client import ChromaDBClient

#載入postgresql連線
from app.db import login_postgresql

# 設定日誌
logger = logging.getLogger(__name__)

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
    """應用啟動時執行的初始化函數"""
    logger.info("🚀 Starting application...")
    
    # 初始化資料庫
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

    # 初始化 ChromaDB 連線
    try:
        logger.info("Initializing ChromaDB connection...")
        chroma_client = ChromaDBClient.get_instance()
        # 簡單的連接測試
        chroma_client.get_client()
        logger.info("✅ ChromaDB connection established")
    except Exception as e:
        logger.error(f"❌ ChromaDB connection failed: {str(e)}")
        # 不要立即失敗，讓應用程式繼續啟動
        logger.warning("⚠️ Application will start without ChromaDB functionality")

    logger.info("✨ Application startup complete")

# 註冊路由
app.include_router(video_router)
app.include_router(chroma_router)

# 健康檢查端點
@app.get("/health")
def health_check():
    port = os.environ.get("PORT")
    print(f"✅ /health called on PORT={port}")
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "port": port,
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
    
# test
logger.info("✅ FastAPI app instance created at root level")

# 根路由
@app.get("/")
async def root():
    return {
        "message": "Video Search API 運行",
        "version": settings.API_VERSION
    }

#timlin_test
@app.get("/show_videos")
def show_videos():#顯示多部影片回傳embed_urls ，未來應該是v_ids陣列進來
    v_id = 20 #試抓
    conn = login_postgresql()
    cursor = conn.cursor()
    cursor.execute("SELECT embed_url FROM videos WHERE id = %s", (v_id,))
    url = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return {
        "message": "成功顯示embed_url(內嵌碼)",
        "embed_url":url
    }
    '''
    show_videos_url = []
    conn = login_postgresql()
    cursor = conn.cursor()
    for v_id in v_ids:
        cursor.execute("SELECT embed_url FROM videos WHERE id = %s", (v_id,))
        url = cursor.fetchall()
        show_videos_url.add(url)
    print(show_videos_url)
    '''
    

# if __name__ == "__main__":
#     import uvicorn
#     port = int(os.getenv("PORT", "8080"))
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=port,
#         reload=settings.DEBUG
#     )