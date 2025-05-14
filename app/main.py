from fastapi import FastAPI, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

app = FastAPI()

# DATABASE_URL = postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@postgres.railway.internal:5432/railway
DATABASE_URL = os.getenv("postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@postgres.railway.internal:5432/railway")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ 提供給 router 使用的 get_db 函數
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"status": "Database connection successful"}
