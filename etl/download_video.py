import subprocess
import os
import re
import json
import psycopg2
from datetime import datetime
from getpass import getpass
from urllib.parse import quote_plus
from transformers import pipeline, AutoTokenizer

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from dotenv import load_dotenv
load_dotenv()
import configparser


from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import json, re, os
from datetime import datetime

def load_api_key(config_file="config.ini"):
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"❌ 找不到 {config_file}，請放在專案根目錄！")

    config = configparser.ConfigParser()
    config.read(config_file)

    if 'gemini' not in config:
        raise configparser.NoSectionError("gemini")
    
    try:
        return config.get('gemini', 'api_key')
    except configparser.NoOptionError:
        raise configparser.NoOptionError("api_key", "gemini")

# ✅ 呼叫
api_key = load_api_key()

# 初始化 Gemini API
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    google_api_key=api_key,
   
)

# 初始化 Summarizer 與 Tokenizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")
tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-6-6")

def time_str_to_str(time_str):
    parts = time_str.split(":")
    if len(parts) == 3:
        return f"{int(parts[1]):02}:{int(parts[2]):02}"
    elif len(parts) == 2:
        return f"{int(parts[0]):02}:{int(parts[1]):02}"
    return "00:00"

def seconds_to_time_str(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}"

def login_postgresql():
    print(" 請登入 PostgreSQL 資料庫")
    
    try:
        DATABASE_URL = (
            os.getenv("DATABASE_URL") or 
            "postgresql://postgres:pMHQKXAVRWXxhylnCiKOmslOKgVbjdvM@switchyard.proxy.rlwy.net:43353/railway"
        )
        conn = psycopg2.connect(DATABASE_URL)
        print(" 成功連線到 PostgreSQL！")
        return conn
    except Exception as e:
        print(" 連線失敗：", e)
        exit()

def search_youtube_with_subtitles(keyword, max_results=10):
    yt_dlp_path = r"C:\\Users\\Tim\\AppData\\Roaming\\Python\\Python311\\Scripts\\yt-dlp.exe"
    print(f"\U0001f50d 搜尋關鍵字：{keyword}")
    command = [
        yt_dlp_path,
        f"ytsearch{max_results}:{keyword}",
        "--dump-json",
        "--no-warnings"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        valid_videos = []
        for line in lines:
            video_data = json.loads(line)
            if video_data.get("subtitles") or video_data.get("automatic_captions"):
                valid_videos.append({
                    "title": video_data.get("title"),
                    "url": video_data.get("webpage_url"),
                    "description": video_data.get("description"),
                    "duration": video_data.get("duration_string"),
                    "channel": video_data.get("channel")
                })
        return valid_videos
    except subprocess.CalledProcessError as e:
        print(" 執行 yt-dlp 發生錯誤：", e)
        return []

def split_text_by_tokens(text, max_tokens=800):
    words = text.split()
    chunks = []
    current = []
    for word in words:
        current.append(word)
        token_len = len(tokenizer(" ".join(current))["input_ids"])
        if token_len > max_tokens:
            chunks.append(" ".join(current[:-1]))
            current = [word]
    if current:
        chunks.append(" ".join(current))
    return chunks

def generate_summary_local(subtitle_text):
    if len(subtitle_text) < 200:
        return subtitle_text.strip()
    try:
        chunks = split_text_by_tokens(subtitle_text)
        partial_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"\U0001f9e9 正在處理第 {i+1} 段摘要...")
            input_length = len(tokenizer(chunk)["input_ids"])
            if input_length < 20:  # 可依實際需求調整閾值
                partial_summaries.append(chunk.strip())
                continue
            result = summarizer(chunk, max_length=100, min_length=30, do_sample=False)
            partial_summaries.append(result[0]['summary_text'])
        return "\n".join(partial_summaries)
    except Exception as e:
        print(" 摘要失敗，回傳前段文字：", e)
        return subtitle_text[:400]

def predict_topic_with_gemini(summary_text):
    messages = [
        SystemMessage(content=f"這是一段YouTube影片的摘要內容：{summary_text}。請根據以下主題分類中，選出最適合的2個主題（只回傳英文主題名稱，用逗號分隔）：Computer Science, Law, Mathematics, Physics, Chemistry, Biology, Earth Science, History, Geography, Sports, Astronomy,Daily Life。請勿自行創造其他分類。"),
        HumanMessage(content="根據摘要來判斷最適合的分類是哪種")
    ]
    result = llm.invoke(messages)
    return result.content


def download_and_save_to_postgresql(video_url, title, description, conn, language="en"):
    print(f"\U0001f3ac 處理影片：{video_url}")
    video_id = video_url.split("v=")[-1]

    try:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                # 優先使用手動字幕
                transcript = transcript_list.find_manually_created_transcript([language]).fetch()
            except NoTranscriptFound:
                # 若沒有手動字幕，再找自動字幕
                transcript = transcript_list.find_generated_transcript([language]).fetch()
        except (TranscriptsDisabled, NoTranscriptFound):
            print(f"❌ 此影片無 {language} 字幕：{video_url}")
            return
        structured_subtitles = []
        output_lines = []

        for i, entry in enumerate(transcript):
            start = entry.start
            duration = entry.duration
            content = entry.text.strip()

            # 格式化為 mm:ss
            mmss = time_str_to_str(seconds_to_time_str(start))

            # 移除 HTML 標籤與雜訊
            content = re.sub(r"<.*?>", "", content)
            content = re.sub(r"\[.*?\]", "", content)
            content = re.sub(r"\s+", " ", content)

            # 忽略空段落
            if not content:
                continue

            # 過濾重複
            if structured_subtitles and content in structured_subtitles[-1]["content"]:
                continue

            structured_subtitles.append({
                "start": mmss,
                "content": content
            })
            output_lines.append(content)

        subtitle_text = "\n".join(output_lines)

        # 儲存影片長度（取最後字幕結束時間）
        if transcript:
            last_end = transcript[-1].start + transcript[-1].duration
            duration_str = time_str_to_str(seconds_to_time_str(last_end))
            duration_sec = int(last_end)
            if duration_sec < 180:
                print(f" 影片長度僅 {duration_str}，少於 3 分鐘，略過儲存")
                return
            if duration_sec > 3600:
                print(f" 影片長度 {duration_str}，大於 1 小時，略過儲存")
                return
        else:
            duration_str = ""

        # 清理字幕內容
        subtitle_text = clean_text(subtitle_text)

        # 抽出內嵌網址
        embed_url = f"https://www.youtube.com/embed/{video_id}"

        # 做 summary + 主題分類
        summary = generate_summary_local(subtitle_text)
        assigned_categories = predict_topic_with_gemini(summary)
        assigned_categories = [t.strip() for t in assigned_categories.split(",")]

        cursor = conn.cursor()
        cursor.execute("SELECT id FROM videos WHERE url = %s", (video_url,))
        if cursor.fetchone():
            print(f" 影片已存在於資料庫中，略過：{video_url}")
            return

        # 儲存到資料庫
        cursor.execute("""
            INSERT INTO videos (url, title, description, summary, transcription, transcription_with_time, duration_str, embed_url, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            video_url, title, description, summary, subtitle_text,
            json.dumps(structured_subtitles, ensure_ascii=False),
            duration_str, embed_url, datetime.utcnow()
        ))

        new_video_id = cursor.fetchone()[0]
        for topic in assigned_categories:
            cursor.execute("SELECT id FROM categories WHERE topic = %s", (topic,))
            result = cursor.fetchone()
            if result:
                category_id = result[0]
                cursor.execute("INSERT INTO video_categories (video_id, category_id) VALUES (%s, %s)", (new_video_id, category_id))
            else:
                print(f"⚠️ 找不到分類：{topic}，略過此分類")

        conn.commit()
        print(f"✅ 成功儲存影片：{title}，主題：{', '.join(assigned_categories)}")

    except Exception as e:
        print("❌ 發生錯誤：", e)

def clean_text(text):#清理字幕檔
    text = re.sub(r'WEBVTT.*?\n', '', text, flags=re.DOTALL)
    text = re.sub(r'\[[^\]]+\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

if __name__ == "__main__":
    keyword = [     
    "how to improve C++"]

    conn = login_postgresql()

    for key in keyword:
        videos = search_youtube_with_subtitles(key, max_results=1)
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video['title']}")
            print(f"連結: {video['url']}")
            print(f"頻道: {video['channel']}")
            print(f"時長: {video['duration']}")
            download_and_save_to_postgresql(video['url'], video['title'], video.get('description', ''), conn)
    conn.close()