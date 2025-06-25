from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
#from app.services.yt_utils import search_youtube_with_subtitles, download_and_save_to_postgresql
from app.services.vectordb_search_for_main import search_videos_with_vectorDB
from app.services.llm_expand import generate_related_queries
from app.services.learning_map import generate_learning_map
from app.services.db_utils import login_postgresql
from app.chroma_client import ChromaDBClient
from typing import Optional
from fastapi import Query
from fastapi import HTTPException

from datetime import datetime

#後端新增一個解密 JWT 的函數（用於後續需要身份的 API）
from fastapi import Request
from jose import jwt#要加入requirement.txt
from datetime import timedelta
from pydantic import BaseModel

router = APIRouter()

SECRET_KEY = "qwu8X34j1n!s9@Fkd9vsh27@#jsaL90skdF0=93M"  # 記得放在環境變數或 .env 中，以及railway的變數裡面
ALGORITHM = "HS256"

def get_current_user(request: Request):#用來解碼前端傳進來的token
    token = request.headers.get("authorization")
    print("token:", token)
    print("SECRET_KEY:", SECRET_KEY)
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    try:
        payload = jwt.decode(token[7:], SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Token decode failed")

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

def save_learning_map_to_db(new_map_id,conn,cur,user_id: int, query: str, learning_map: dict):
    for phase_idx, (phase_key, phase) in enumerate(sorted(learning_map.items()), start=1):
        phase_title = phase.get("title", "")
        items = phase.get("items", [])

        for item in items:
            item_title = item.get("title", "")
            steps = item.get("steps", [])
            keywords = item.get("keywords", [])
            video = item.get("video", [])

            video_url = video[4] if len(video) > 4 else None
            video_title = video[2] if len(video) > 2 else None
            video_summary = video[3] if len(video) > 3 else None

            cur.execute("""
                INSERT INTO learning_map (
                    user_id, map_id, phase_number, phase_title, item_title,
                    step_list, keyword_list, video_url, video_title, video_summary, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                user_id, new_map_id, phase_idx, phase_title, item_title,
                steps, keywords, video_url, video_title, video_summary, datetime.utcnow()
            ))
    conn.commit()

@router.get("/learning_map")
async def get_learning_map(query: Optional[str] = Query(None),user_id: int = Depends(get_current_user)):
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
        conn = login_postgresql()
        cur = conn.cursor()
        # 在儲存一張地圖前，先取得新 map_id
        cur.execute("SELECT COALESCE(MAX(map_id), 0) FROM learning_map WHERE user_id = %s", (user_id,))
        current_max_map_id = cur.fetchone()[0]
        new_map_id = current_max_map_id + 1
        # 儲存到資料庫
        save_learning_map_to_db(new_map_id,conn,cur,user_id=user_id, query=query, learning_map=learning_map)
        cur.close()
        conn.close()
        return {
            "message":"成功儲存並製作學習地圖",
            "query": query,
            "learning_map": learning_map
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成學習地圖失敗: {str(e)}")

#拿取學習地圖
@router.get("/show_learning_map")
async def show_learning_map(user_id: int = Depends(get_current_user)):
    conn = login_postgresql()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM learning_map WHERE user_id = %s",(user_id,))
    learning_map = cursor.fetchall()
    conn.close()
    return{
        "learning_map": learning_map
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

# 使用者註冊(已經成功加入timlin)
@router.post("/user_register")#之後改回post，前端傳入帳密
def user_register(user_name,email,password):
    # 前端傳入名稱、信箱、密碼
    conn = login_postgresql()  # 呼叫函數
    cursor = conn.cursor()
    now = datetime.now()
    # user_name = "TimLin" #先預設 之後改
    # email = 'aa0909095679@gmail.com'
    # password = '000'
    try:
        # 檢查 email 是否已存在
        cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
        result = cursor.fetchone()
        if result is not None:
            return {"status": "Email already registered"}

        # 寫入新使用者
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s);
        """, (user_name, email, password, now, now))

        conn.commit()
        return {"status": "User registered successfully"}

    except Exception as e:
        return {"status": "Error", "message": str(e)}

    finally:
        cursor.close()
        conn.close()

# 使用者登入(已經成功登入timlin)
class LoginRequest(BaseModel):
    user_name: str
    email: str
    password: str

@router.post("/user_login")
def user_login(user_name,email,password):#data: LoginRequest
    '''
    user_name = data.user_name
    email = data.email
    password = data.password'''
    #前端傳入名稱、信箱、密碼
    conn = login_postgresql()
    cursor = conn.cursor()
    # user_name = 'TimLin'#先預設 之後改
    # email = "aa0909095679@gmail.com"
    # password = '000'
    try:
        # 查詢確認資訊是否符合
        cursor.execute("""
            SELECT id FROM users 
            WHERE email = %s AND password_hash = %s AND username = %s;
        """, (email, password, user_name))
        
        result = cursor.fetchone()
        if result is None:
            return {"status": "Login failed. Check credentials."}
        
        user_id = result[0]
        # 產生 token（有效期 7 天）
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        return {"status": "User login successfully",
                 "access_token": token#回傳前端token
            }

    except Exception as e:
        return {"status": "Error", "message": str(e)}

    finally:
        cursor.close()
        conn.close()


#記錄點下影片的資訊，需要判斷是誰、哪一部影片、從哪看到哪
@router.post("/click_video")
def click_video(user_id: int = Depends(get_current_user),video_id=1, watched_from_sec=0, watched_to_sec=0):
    conn = login_postgresql()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_video_history (user_id, video_id, watched_from_sec, watched_to_sec, date_time)
        VALUES (%s, %s, %s, %s, NOW())
    """, (user_id, video_id, watched_from_sec, watched_to_sec))

    conn.commit()
    conn.close()

    return {"message": "Click recorded"}

#簡易推薦片邏輯
@router.get("/recommend")
def recommend(user_id: int = Depends(get_current_user)):
    conn = login_postgresql()
    cursor = conn.cursor()

    # Step 1: 統計使用者最近觀看過哪些影片類別（TOP 3）
    cursor.execute("""
        SELECT vc.category_id, COUNT(*) AS watch_count
        FROM user_video_history h
        JOIN video_categories vc ON h.video_id = vc.video_id
        WHERE h.user_id = %s
        GROUP BY vc.category_id
        ORDER BY watch_count DESC
        LIMIT 3
    """, (user_id,))
    
    favorite_categories = [row[0] for row in cursor.fetchall()]
    if not favorite_categories:
        return {"message": "沒有觀看紀錄", "videos": []}

    # Step 2: 從這些類別中找「沒看過的影片」來推薦
    cursor.execute("""
        SELECT DISTINCT v.id, v.title,v.embed_url,v.created_at
        FROM videos v
        JOIN video_categories vc ON v.id = vc.video_id
        WHERE vc.category_id = ANY(%s)
        AND v.id NOT IN (
            SELECT video_id FROM user_video_history WHERE user_id = %s
        )
        ORDER BY v.created_at DESC
        LIMIT 10
    """, (favorite_categories, user_id))

    videos = cursor.fetchall()
    conn.close()

    return {
        "recommended_categories": favorite_categories,
        "videos": videos
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