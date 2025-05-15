from fastapi import FastAPI, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from dotenv import load_dotenv
load_dotenv()  # 加在所有 import 之前

import os
import datetime
print("DEBUG → DATABASE_URL: ", os.getenv("DATABASE_URL"))

# 創建 FastAPI 實例
app = FastAPI(title="Video Search API")

# 設定 CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在正式環境應該限制來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設定 PostgreSQL 連接
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@postgres.railway.internal:5432/railway")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"Database connection error: {e}")
    raise

# 提供給 router 使用的 get_db 函數
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化 DB 函數 (可被其他模組調用)
def init_db():
    try:
        # 這裡可以添加創建表格的邏輯，如果需要的話
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# 引入 API 路由
from app.api import chroma_routes, video_routes
from app.chroma_client import ChromaDBClient

# 應用啟動時執行的函數
@app.on_event("startup")
async def startup():
    # 初始化 PostgreSQL 連線
    init_db()
    # 初始化 ChromaDB 連線
    try:
        ChromaDBClient.get_instance()
        print("ChromaDB connection initialized successfully")
    except Exception as e:
        print(f"ChromaDB connection error: {e}")

# 註冊路由
app.include_router(video_routes.router)
app.include_router(chroma_routes.router)

# 原有的健康檢查端點
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"status": "Database connection successful"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }

# 根路由
@app.get("/")
async def root():
    return {"message": "Video Search API 運行中"}

# 新增 ChromaDB 健康檢查
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