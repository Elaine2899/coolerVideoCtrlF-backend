from chromadb import PersistentClient
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import torch
from embedding_postgresql import generate_related_queries  # 確保你引入 LLM 擴展函數
import psycopg2
import os

# === 初始化 ChromaDB client & collection ===
client = PersistentClient(path="D:/Chroma", settings=Settings(allow_reset=True))
collection_tt = client.get_or_create_collection(name="title_topic_emb")
collection_st = client.get_or_create_collection(name="summary_transcription_emb")
collection_chunks = client.get_or_create_collection(name="transcription_chunks_emb")

# === 模型 ===
model_tt = SentenceTransformer("paraphrase-MiniLM-L6-v2", device='cuda' if torch.cuda.is_available() else 'cpu')
model_st = SentenceTransformer("BAAI/bge-m3", device='cuda' if torch.cuda.is_available() else 'cpu')

# === 公用 cosine similarity 函數 ===
def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)

# === 查詢字幕片段最相關的起始時間（取前一段） ===
def get_best_chunk_start(video_id: str, query: str):
    query_emb = model_st.encode([query])[0]
    res = collection_chunks.get(where={"video_id": video_id}, include=["embeddings", "metadatas"])
    if not res["ids"]:
        return None

    best_idx = -1
    best_score = -1

    for i, (emb, meta) in enumerate(zip(res["embeddings"], res["metadatas"])):
        score = cosine_similarity(query_emb, emb)
        if score > best_score:
            best_score = score
            best_idx = i

    if best_idx < 0:
        return None
    if best_idx == 0:
        return res["metadatas"][0]["start"]
    return res["metadatas"][best_idx - 1]["start"]

# === 主流程 ===
def search_videos_with_vectorDB(query: str, k=5):
    expanded_queries = generate_related_queries(query)

    # 所有影片向量
    all_tt = collection_tt.get(include=["embeddings", "metadatas"])
    all_st = collection_st.get(include=["embeddings", "metadatas"])

    video_scores = {}

    for query_text in expanded_queries:
        q_tt_emb = model_tt.encode(query_text).tolist()
        q_st_emb = model_st.encode(query_text).tolist()

        for emb, meta in zip(all_tt["embeddings"], all_tt["metadatas"]):
            vid = meta["video_id"]
            field = meta["field"]
            score = cosine_similarity(q_tt_emb, emb) + 1  # 保證為正
            video_scores.setdefault(vid, {"title": 0, "topic": 0, "summary": 0})
            if field in video_scores[vid]:
                video_scores[vid][field] += score

        for emb, meta in zip(all_st["embeddings"], all_st["metadatas"]):
            vid = meta["video_id"]
            field = meta["field"]
            score = cosine_similarity(q_st_emb, emb) + 1
            video_scores.setdefault(vid, {"title": 0, "topic": 0, "summary": 0})
            if field == "summary":
                video_scores[vid]["summary"] += score

    # 加權分數彙總（title: 0.4, topic: 0.3, summary: 0.3）
    final_scores = []
    for vid, scores in video_scores.items():
        total = 0.4 * scores["title"] + 0.3 * scores["topic"] + 0.3 * scores["summary"]
        final_scores.append((total, vid))

    final_scores.sort(reverse=True)
    top_videos = final_scores[:k]

    # 取得影片資訊與推薦片段時間（改用 with 方式）
    results = []
    with psycopg2.connect("postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@switchyard.proxy.rlwy.net:43353/railway") as conn:
        with conn.cursor() as cursor:
            for total_score, vid in top_videos:
                cursor.execute("SELECT title, summary, embed_url FROM videos WHERE id = %s", (vid,))
                row = cursor.fetchone()
                title, summary, embed_url = row if row else ("", "", "")

                start = None
                for query_text in expanded_queries:
                    start = get_best_chunk_start(vid, query_text)
                    if start:
                        break

                # 將 "HH:MM:SS" 轉為秒數
                seconds = 0
                if start:
                    h, m, s = map(float, start.split(":"))
                    seconds = int(h * 3600 + m * 60 + s)

                if embed_url:
                    embed_url = embed_url.split("?")[0] + f"?start={seconds}"

                results.append((total_score, vid, title, summary, embed_url))

    return expanded_queries, results
