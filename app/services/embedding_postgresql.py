import os
import json
import torch
import psycopg2
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
import re
from bertopic import BERTopic
from dotenv import load_dotenv
import google.generativeai as genai


# ---------- 資料庫設定 ----------
POSTGRES_USER = 'teammate'
POSTGRES_PASSWORD = 'cGu5jdTwy4JLriDMylTlzNmW4S9jJHNF'
POSTGRES_HOST = 'dpg-d0d4h8q4d50c73eeu1ng-a.oregon-postgres.render.com'
POSTGRES_PORT = '5432'
POSTGRES_DB = 'youtube_data_qkc5'

# ---------- 初始化模型 ----------
title_topic_embedder = SentenceTransformer('paraphrase-MiniLM-L6-v2', device='cuda' if torch.cuda.is_available() else 'cpu')#原本的embedder = SentenceTransformer('paraphrase-MiniLM-L6-v2')是384維度，和這個的1024不一樣
summary_embedder = SentenceTransformer('BAAI/bge-m3', device='cuda' if torch.cuda.is_available() else 'cpu')

# ---------- 工具函數 ----------
def clean_text(text):
    text = re.sub(r'WEBVTT.*?\n', '', text, flags=re.DOTALL)
    text = re.sub(r'\[[^\]]+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tt_get_embedding(text):
    return title_topic_embedder.encode(text, convert_to_tensor=True).to(title_topic_embedder.device)

def st_get_embedding(text):
    return summary_embedder.encode(text, convert_to_tensor=True).to(summary_embedder.device)

def update_topic_embeddings():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB
    )
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT topic FROM categories;")
    topics = [row[0] for row in cursor.fetchall()]

    for topic in topics:
        emb = tt_get_embedding(topic).cpu().numpy()
        emb_str = ','.join(map(str, emb))
        cursor.execute("""
            INSERT INTO topic_embedding (topic, topic_embedding)
            VALUES (%s, %s)
            ;
        """, (topic, emb_str))

    conn.commit()
    cursor.close()
    conn.close()

def update_video_embeddings():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary FROM videos;")
    videos = cursor.fetchall()

    for video_id, title, summary in tqdm(videos, desc="Updating video embeddings"):
        title = clean_text(title or "")
        summary = clean_text(summary or "")
        title_emb = tt_get_embedding(title).cpu().numpy()
        summary_emb = st_get_embedding(summary).cpu().numpy()
        title_str = ','.join(map(str, title_emb))
        summary_str = ','.join(map(str, summary_emb))

        cursor.execute("""
            INSERT INTO video_embeddings (video_id, title, summary, title_embedding, summary_embedding)
            VALUES (%s, %s, %s, %s, %s)
            ;
        """, (video_id, title, summary, title_str, summary_str))

    conn.commit()
    cursor.close()
    conn.close()


def expand_query_topic(query_emb, top_k=5):
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB
    )
    cursor = conn.cursor()
    cursor.execute("SELECT topic FROM categories;")
    topics = [row[0] for row in cursor.fetchall()]

    sims = []
    for topic in topics:
        topic_emb = tt_get_embedding(topic)
        sim_score = util.cos_sim(query_emb, topic_emb).item()
        sims.append((sim_score, topic))

    sims.sort(reverse=True)
    top_k_topics = [t for _, t in sims[:top_k]]

    cursor.close()
    conn.close()
    return top_k_topics

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 真正的topic expand，能生成更多input
def generate_related_queries(input_text):
    """
    使用 LLM (Gemini) 做語意相關詞擴展
    """
    # 1️⃣ 保底：原始 query
    related_queries = [input_text]

    # 2️⃣ LLM prompt
    prompt = (
        f"請列出5個與「{input_text}」密切相關的學術主題詞或關鍵詞(並依照相關程度排序)。"
        "請直接用英文詞語，輸出格式為一個Python list，不用包含``` python 或任何額外標記，只需輸出 Python list 即可，例如："
        "['artificial intelligence', 'deep learning', 'data mining', 'neural networks', 'computer science']"
    )

    # 3️⃣ 調用 LLM
    try:
        response = model.generate_content(
            [
                {"role": "user", "parts": [prompt]}
            ],
            generation_config={
                "temperature": 0.2
            }
        )
        output_text = response.text
        print(f"LLM原始輸出: {output_text}")  # 打印原始輸出
        # 移除程式碼塊的標記 (如果存在)
        if output_text.startswith("```python") and output_text.endswith("```"):
            output_text = output_text[len("```python"): -len("```")].strip()
        # 移除可能存在的換行符
        output_text = output_text.replace('\n', '')    
        # 嘗試將回傳內容直接 eval 成 list
        expanded_words = eval(output_text)
        
        if isinstance(expanded_words, list):
            related_queries.extend(expanded_words)
    except Exception as e:
        print(f"Gemini LLM擴展失敗：{e}")
        print(f"錯誤詳情：{e}")  # 打印更詳細的錯誤信息

    # 4️⃣ 去重
    related_queries = list(dict.fromkeys(related_queries))
    return related_queries

def get_videos_by_topic_expansion(query):
    """
    完全保留你的第二版資料庫查詢邏輯
    """
    query_emb = tt_get_embedding(query)
    expanded_topics = expand_query_topic(query_emb)

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB
    )
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM categories WHERE topic = ANY(%s);", (expanded_topics,))
    category_ids = [row[0] for row in cursor.fetchall()]

    if not category_ids:
        cursor.close()
        conn.close()
        return []

    cursor.execute("SELECT DISTINCT video_id FROM video_categories WHERE category_id = ANY(%s);", (category_ids,))
    matched_ids = [row[0] for row in cursor.fetchall()]

    if not matched_ids:
        cursor.close()
        conn.close()
        return []

    # ✅ 重點修改：JOIN videos 撈 url
    cursor.execute("""
        SELECT ve.video_id, ve.title, ve.summary, ve.title_embedding, ve.summary_embedding, v.url
        FROM video_embeddings ve
        JOIN videos v ON ve.video_id = v.id
        WHERE ve.video_id = ANY(%s);
    """, (matched_ids,))
    videos = cursor.fetchall()
    cursor.close()
    conn.close()

    return videos  # ✔ 提供 raw data，下一層處理

def retrieve_top_k(query, k=5):
    raw_videos = get_videos_by_topic_expansion(query)  # ✔ 撈資料
    results = []

    query_emb = title_topic_embedder.encode(query, convert_to_tensor=True).to(title_topic_embedder.device)
    expanded_queries = generate_related_queries(query)
    weights = [1.0 - 0.1 * i for i in range(len(expanded_queries))]

    for v in raw_videos:
        video_id, title, summary, title_emb_str, summary_emb_str, url = v
        title_emb = torch.tensor(np.fromstring(title_emb_str, sep=',', dtype=np.float32)).to(query_emb.device)
        summary_emb = torch.tensor(np.fromstring(summary_emb_str, sep=',', dtype=np.float32)).to(query_emb.device)

        topics = []  # ❗️可選，你可以再查 video_categories → categories 拿 topic strings

        total_score = 0
        total_weight = 0
        for query_text, weight in zip(expanded_queries, weights):
            q_title_emb = title_topic_embedder.encode(query_text, convert_to_tensor=True).to(title_emb.device)
            q_summary_emb = summary_embedder.encode(query_text, convert_to_tensor=True).to(summary_emb.device)

            title_score = util.cos_sim(q_title_emb, title_emb).item()
            summary_score = util.cos_sim(q_summary_emb, summary_emb).item()

            topic_scores = []
            for topic in topics:
                t_emb = title_topic_embedder.encode(topic, convert_to_tensor=True).to(q_title_emb.device)
                topic_scores.append(util.cos_sim(q_title_emb, t_emb).item())
            topic_score = np.mean(topic_scores) if topic_scores else 0

            single_score = 0.4 * title_score + 0.3 * summary_score + 0.3 * topic_score
            total_score += weight * single_score
            total_weight += weight

        final_score = total_score / total_weight if total_weight > 0 else 0
        results.append((final_score, video_id, title, summary, url))  # 可加其他資訊

    results.sort(reverse=True, key=lambda x: x[0])
    return expanded_queries,results[:k]

if __name__ == '__main__':
    update_topic_embeddings()
    update_video_embeddings()

