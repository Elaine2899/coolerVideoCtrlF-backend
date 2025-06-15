import numpy as np
import torch
from chromadb import HttpClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer
from app.services.db_utils import login_postgresql
from app.services.llm_expand import generate_related_queries
from app.chroma_client import ChromaDBClient

# ==== 遠端 ChromaDB 設定 ====
"""
HOST = "chroma-production-84ca.up.railway.app"
PORT = 443
USE_SSL = True

# 初始化 HttpClient
client = HttpClient(host=HOST, port=PORT, ssl=USE_SSL)
"""
client = ChromaDBClient.get_instance().get_client()

# ==== 嵌入模型（本地端運算） ====
model_tt = SentenceTransformer("paraphrase-MiniLM-L6-v2")
model_st = SentenceTransformer("BAAI/bge-m3")

# 給 collection 用的嵌入函式
embedding_func_tt = SentenceTransformerEmbeddingFunction(model_name="paraphrase-MiniLM-L6-v2")
embedding_func_st = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-m3")

# ==== Collection 初始化（遠端） ====
col_tt = client.get_or_create_collection("title_topic_emb", embedding_function=embedding_func_tt)
col_st = client.get_or_create_collection("summary_transcription_emb", embedding_function=embedding_func_st)
col_chunk = client.get_or_create_collection("transcription_chunks_emb", embedding_function=embedding_func_st)

# ==== 工具函數 ====
def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)

def get_best_chunk_start(video_id: str, query: str):
    query_emb = model_st.encode([query])[0]
    res = col_chunk.get(where={"video_id": video_id}, include=["embeddings", "metadatas"])
    best = max(zip(res["embeddings"], res["metadatas"]), key=lambda p: cosine_similarity(query_emb, p[0]), default=(None, None))
    return best[1]["start"] if best[1] else None

def search_videos_with_vectorDB(query: str, k=5):
    expanded = generate_related_queries(query)
    all_tt = col_tt.get(include=["embeddings", "metadatas"])
    all_st = col_st.get(include=["embeddings", "metadatas"])
    scores = {}
    for q in expanded:
        q_tt = model_tt.encode(q).tolist()
        q_st = model_st.encode(q).tolist()
        for emb, meta in zip(all_tt["embeddings"], all_tt["metadatas"]):
            vid = meta["video_id"]
            field = meta["field"]
            scores.setdefault(vid, {"title": 0, "topic": 0, "summary": 0})
            if field in scores[vid]:
                scores[vid][field] += cosine_similarity(q_tt, emb) + 1
        for emb, meta in zip(all_st["embeddings"], all_st["metadatas"]):
            vid = meta["video_id"]
            field = meta["field"]
            if field == "summary":
                scores.setdefault(vid, {"title": 0, "topic": 0, "summary": 0})
                scores[vid]["summary"] += cosine_similarity(q_st, emb) + 1
    result = sorted(((0.4*v["title"] + 0.3*v["topic"] + 0.3*v["summary"], vid) for vid,v in scores.items()), reverse=True)[:k]
    final = []
    conn = login_postgresql()
    cur = conn.cursor()
    for score, vid in result:
        cur.execute("SELECT title, summary, embed_url FROM videos WHERE id = %s", (vid,))
        title, summary, embed_url = cur.fetchone()
        start = next((get_best_chunk_start(vid, q) for q in expanded if get_best_chunk_start(vid, q)), None)
        seconds = sum(float(x) * 60**i for i, x in enumerate(reversed(start.split(":")))) if start else 0
        embed_url = embed_url.split("?")[0] + f"?start={int(seconds)}" if embed_url else ""
        final.append((score, vid, title, summary, embed_url))
    return expanded, final
