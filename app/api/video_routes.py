from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
#from app.services.yt_utils import search_youtube_with_subtitles, download_and_save_to_postgresql
from app.services.embedding_utils import search_videos_with_vectorDB
from app.services.llm_expand import generate_related_queries
from app.services.learning_map import generate_learning_map
from app.services.db_utils import login_postgresql
from app.chroma_client import ChromaDBClient
from typing import Optional
from fastapi import Query

router = APIRouter()

'''
@router.get("/videos")
def read_videos(db: Session = Depends(get_db)):
    videos = db.execute("SELECT * FROM videos").fetchall()
    return videos
'''

### 目前這get /search是要傳回去推薦影片的，但還沒有寫:(
@router.get("/search")
async def search_videos(query: Optional[str] = Query(None)):
    try:
        if query:
            # 有查詢字 → 搜尋影片
            expanded_queries = generate_related_queries(query)
            _, results = search_videos_with_vectorDB(query, k=5)
        else:
            # 沒查詢字 → 推薦影片（你要實作這個 function）
            expanded_queries = []
            #results = get_recommended_videos() 未來要推薦影片函式
            results = []

        response = {
            "query": query,
            "expanded_queries": expanded_queries,
            "results": [
                {
                    "score": score,
                    "video_id": vid,
                    "title": title,
                    "summary": summary,
                    "url": embed_url
                }
                for score, vid, title, summary, embed_url in results
            ]
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋失敗: {str(e)}")

@router.get("/learning_map")
async def get_learning_map(query: Optional[str] = Query(None)):
    try:
        if not query:
            # 如果沒有提供 query，就回傳空的學習地圖結構
            return {
                "query": None,
                "learning_map": {}
            }

        learning_map = generate_learning_map(query)

        if not learning_map:
            raise HTTPException(status_code=404, detail="無法生成學習地圖")

        return {
            "query": query,
            "learning_map": learning_map
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成學習地圖失敗: {str(e)}")

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