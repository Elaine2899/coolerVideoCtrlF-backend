# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
import logging
from sqlalchemy.exc import SQLAlchemyError
from .config import settings
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ 優先吃 Railway 環境變數
logger.info(f"Using Database URL: {settings.DATABASE_URL}")

if not settings.DATABASE_URL:
    logger.error("❌ No database URL configured!")
    raise ValueError("❌ DATABASE_URL or DATABASE_PUBLIC_URL is missing")

# ✅ 建立 engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,               # 連線池大小
    max_overflow=10,           # 允許的溢出連接數
    pool_timeout=30,           # 獲取連接的超時時間
    pool_recycle=1800          # 連接回收時間（秒）
)

# ✅ 建立 session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ 統一 model Base class
Base = declarative_base()

# 初始化資料庫，建立所有定義的表格
def init_db():
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database initialized successfully")
            return
        except SQLAlchemyError as e:
            retry_count += 1
            logger.error(f"❌ Database initialization attempt {retry_count} failed: {e}")
            if retry_count == max_retries:
                raise
            time.sleep(2 ** retry_count)  # 指數退避

# ✅ 給 router 調用用的 Session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
