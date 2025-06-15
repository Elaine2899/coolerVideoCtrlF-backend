from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.yt_utils import search_youtube_with_subtitles, download_and_save_to_postgresql
from app.services.embedding_utils import search_videos_with_vectorDB
from app.services.db_utils import login_postgresql
from app.chroma_client import ChromaDBClient

from datetime import datetime#timlin_test，用來新增歷史影片的觀看時間(哪一天什麼時候觀看的)

router = APIRouter()

'''
@router.get("/videos")
def read_videos(db: Session = Depends(get_db)):
    videos = db.execute("SELECT * FROM videos").fetchall()
    return videos
'''


@router.get("/search")
def search(query: str):
    expanded_queries, results = search_videos_with_vectorDB(query, top_k=5)
    return {
        "query": query,
        "expanded_queries": expanded_queries,
        "results": results
    }

@router.get("/videos")
def get_all_videos():
    conn = login_postgresql()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, duration_str FROM videos")
    data = cursor.fetchall()
    conn.close()
    return {"videos": data}

@router.get("/topics")
def get_all_topics():
    conn = login_postgresql()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories")
    data = cursor.fetchall()
    conn.close()
    return {"topics": data}

@router.get("/video-to-topic")
def get_video_topic_relations():
    conn = login_postgresql()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM video_categories")
    data = cursor.fetchall()
    conn.close()
    return {"relations": data}


@router.get("/video-embeddings")
def get_video_chunk_counts():
    # 1. 拿到 collection
    client = ChromaDBClient.get_instance().get_client()
    col_chunk = client.get_collection("transcription_chunks_emb")

    # 2. 抓出所有 metadatas
    chunks = col_chunk.get(include=["metadatas"])
    
    # 3. 統計每個 video_id 有幾個 chunk
    count_map = {}
    for metadata in chunks.get("metadatas", []):
        video_id = metadata.get("video_id")
        if video_id:
            count_map[video_id] = count_map.get(video_id, 0) + 1

    # 4. 組成回傳格式
    result = [
        {"video_id": vid, "chunk_count": count}
        for vid, count in count_map.items()
    ]

    return {
        "total_videos": len(result),
        "videos": result
    }

#抓影片的連結，但先用不到
'''
@router.post("/yt-catch")
def yt_catch(keyword: str):
    videos = search_youtube_with_subtitles(keyword)
    conn = login_postgresql()
    for video in videos:
        download_and_save_to_postgresql(
            video_url=video["url"],
            title=video["title"],
            description=video.get("description", ""),
            conn=conn
        )
    conn.close()
    return {"keyword": keyword, "videos": videos}
'''
########################################################(timlin_test 新增歷史紀錄、推薦影片)
@router.post("/history")# 新增歷史紀錄，當點進影片後離開，會紀錄是誰觀看、看了什麼、甚麼時候看的、看了多久，記錄這些資料
def add_watch_history():
    conn = login_postgresql()
    cursor = conn.cursor()
    user_id = 1#先預設1
    video_id = 1#先預設1
    watch_duration = 100#先預設100秒

    cursor.execute("""
        INSERT INTO history (user_id, video_id, click_time, watch_duration)
        VALUES (%s, %s, %s, %s)
    """, (user_id, video_id, datetime.now(), watch_duration))

    conn.commit()
    conn.close()
    return {"message": "History recorded successfully."}

@router.get("/recommend")
def recommend_by_category(user_id: int):
    conn = login_postgresql()
    cursor = conn.cursor()

    # Step 1: 取得使用者最近看的影片的類別
    cursor.execute("""
        SELECT v.category_id
        FROM history h
        JOIN videos v ON h.video_id = v.id
        WHERE h.user_id = %s
        ORDER BY h.click_time DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {"message": "No history found for this user.", "videos": []}
    
    category_id = row[0]

    # Step 2: 推薦相同類別中未看過的影片
    cursor.execute("""
        SELECT v.id, v.title, v.duration_sec,v.embed_url
        FROM videos v
        WHERE v.category_id = %s
          AND v.id NOT IN (
              SELECT video_id FROM history WHERE user_id = %s
          )
        ORDER BY upload_time DESC
        LIMIT 5
    """, (category_id, user_id))
    
    videos = cursor.fetchall()
    conn.close()

    return {
        "category_id": category_id,
        "recommended_videos": videos
    }