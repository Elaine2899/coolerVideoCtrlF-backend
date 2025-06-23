import os
import psycopg2
from datetime import timedelta
from sentence_transformers import SentenceTransformer
from app.chroma_client import ChromaDBClient

# === 共用工具 ===
def parse_time(ts):
    h, m, s = ts.split(":")
    return timedelta(hours=int(h), minutes=int(m), seconds=float(s))

def chunk_transcription(transcript_json, max_duration=3.0):
    """將字幕依照時間長度切成每段最多 max_duration 秒"""
    chunks = []
    current = {"start": "", "end": "", "text": ""}
    start_time = None

    for i, seg in enumerate(transcript_json):
        if not seg["start"] or not seg["end"]:
            continue

        seg_start = parse_time(seg["start"])
        seg_end = parse_time(seg["end"])

        if start_time is None:
            start_time = seg_start
            current["start"] = seg["start"]

        duration = (seg_end - start_time).total_seconds()

        if duration <= max_duration:
            current["text"] += " " + seg["content"].strip()
            current["end"] = seg["end"]
        else:
            if current["text"]:
                chunks.append(current.copy())
            current = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["content"].strip()
            }
            start_time = seg_start

    if current["text"]:
        chunks.append(current)

    return chunks

# === ChromaDB 初始化 ===
client = ChromaDBClient.get_instance().get_client()
collection_tt = client.get_or_create_collection(name="title_topic_emb")
collection_st = client.get_or_create_collection(name="summary_transcription_emb")
collection_chunk = client.get_or_create_collection(name="transcription_chunks_emb")

# === 模型初始化 ===
model_tt = SentenceTransformer("paraphrase-MiniLM-L6-v2")
model_st = SentenceTransformer("BAAI/bge-m3")

# === PostgreSQL 連線 ===
print("🔐 連線到 PostgreSQL 中...")
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@switchyard.proxy.rlwy.net:43353/railway"
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# === 抓影片基本資料 + 字幕 ===
cursor.execute("""
    SELECT 
        v.id AS video_id,
        v.url,
        STRING_AGG(c.topic, '; ') AS topic,
        v.title,
        v.summary,
        v.transcription,
        v.transcription_with_time
    FROM video_categories vc 
    JOIN videos v ON v.id = vc.video_id 
    JOIN categories c ON vc.category_id = c.id
    WHERE v.transcription_with_time IS NOT NULL AND v.id < 100
    GROUP BY v.id, v.url, v.title, v.summary, v.transcription, v.transcription_with_time
    ORDER BY v.id
""")
rows = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]

# === 已存在的 ID（避免重複） ===
existing_ids_tt = set(collection_tt.get()["ids"])
existing_ids_st = set(collection_st.get()["ids"])
existing_ids_chunk = set(collection_chunk.get()["ids"])

# === 欄位對應模型與 collection ===
field_mapping = {
    "title": (collection_tt, model_tt),
    "topic": (collection_tt, model_tt),
    "summary": (collection_st, model_st),
    "transcription": (collection_st, model_st),
}

for row in rows:
    row_dict = dict(zip(columns, row))
    video_id = str(row_dict["video_id"])
    url = row_dict["url"]
    title = row_dict["title"]
    t_with_time = row_dict["transcription_with_time"]

    # === 儲存 title/topic/summary/transcription 向量 ===
    for field, (collection, model) in field_mapping.items():
        content = (row_dict.get(field) or "").strip()
        if not content:
            continue

        uid = f"{video_id}_{field}"
        if (field in ["title", "topic"] and uid in existing_ids_tt) or \
           (field in ["summary", "transcription"] and uid in existing_ids_st):
            print(f"⚠️ 已存在：{uid}，跳過儲存")
            continue

        vector = model.encode([content])[0].tolist()
        collection.add(
            documents=[content],
            embeddings=[vector],
            ids=[uid],
            metadatas=[{
                "video_id": video_id,
                "field": field,
                "url": url,
                "title": title,
                "topic": row_dict["topic"]
            }]
        )

    # === 處理片段字幕向量 ===
    try:
        transcript = t_with_time
        chunks = chunk_transcription(transcript)
        print(f"\n📘 影片：{title} ({video_id})")
        print("✂️ 切割後字幕段落：")
        for i, chunk in enumerate(chunks):
            print(f"▶ Chunk {i}: {chunk['start']} ~ {chunk['end']}")
            print(f"🗣️  {chunk['text']}\n")

        for i, chunk in enumerate(chunks):
            chunk_id = f"{video_id}_chunk_{i}"
            if chunk_id in existing_ids_chunk:
                print(f"⚠️ 已存在：{chunk_id}，跳過")
                continue

            content = chunk["text"].strip()
            if not content:
                continue

            vector = model_st.encode([content])[0].tolist()
            collection_chunk.add(
                documents=[content],
                embeddings=[vector],
                ids=[chunk_id],
                metadatas=[{
                    "video_id": video_id,
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "text": content,
                    "url": url,
                    "title": title
                }]
            )
            print(f"✅ 儲存：{chunk_id} ({chunk['start']}~{chunk['end']})")

    except Exception as e:
        print(f"❌ 處理字幕片段失敗：video_id={video_id}，錯誤：{e}")
        continue

cursor.close()
conn.close()
print("✅ 已成功將所有影片欄位與字幕片段向量儲存完成！")