import psycopg2
import os

# 連線函式：改為 Railway (PortSQL)
def login_postgresql():
    print("🔐 正在登入 Railway PostgreSQL 資料庫...")
    
    try:
        DATABASE_URL = (
            os.getenv("DATABASE_URL") or 
            "postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@switchyard.proxy.rlwy.net:43353/railway"
        )
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ 成功連線到 PostgreSQL！")
        return conn
    except Exception as e:
        print("❌ 連線失敗：", e)
        exit()
