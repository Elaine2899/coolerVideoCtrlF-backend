from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db

router = APIRouter()

@router.get("/videos")
def read_videos(db: Session = Depends(get_db)):
    videos = db.execute("SELECT * FROM videos").fetchall()
    return videos
