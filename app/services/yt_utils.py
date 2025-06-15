import subprocess
import os
import json
import re
import shutil
from datetime import datetime
from configparser import ConfigParser
from transformers import pipeline, AutoTokenizer

'''
config = ConfigParser()
config.read("config.ini")
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    google_api_key="AIzaSyBNBn7je9hOrk5ny-TjabghvHCXr6ZXHbQ",
    convert_system_message_to_human=True,
)
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")
tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-6-6")

def clean_text(text):
    text = re.sub(r'WEBVTT.*?\n', '', text, flags=re.DOTALL)
    text = re.sub(r'\[[^\]]+\]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_yt_dlp_path():
    return shutil.which("yt-dlp") or os.path.join(os.environ.get("CONDA_PREFIX", ""), "Scripts", "yt-dlp.exe")

def search_youtube_with_subtitles(keyword, max_results=10):
    yt_dlp_path = get_yt_dlp_path()
    command = [yt_dlp_path, f"ytsearch{max_results}:{keyword}", "--dump-json", "--no-warnings"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    videos = []
    for line in result.stdout.strip().split('\n'):
        data = json.loads(line)
        if data.get("subtitles") or data.get("automatic_captions"):
            videos.append({"title": data["title"], "url": data["webpage_url"], "description": data["description"], "duration": data["duration_string"], "channel": data["channel"]})
    return videos

def predict_topic_with_gemini(summary):
    messages = [
        SystemMessage(content=f"這是一段影片摘要：{summary}。請從列表中選出最適主題（英文）"),
        HumanMessage(content="選出主題")
    ]
    return llm.invoke(messages).content

def download_and_save_to_postgresql(video_url, title, description, conn, language="en"):
    yt_dlp_path = get_yt_dlp_path()
    command = [yt_dlp_path, "--write-auto-sub", "--sub-lang", language, "--skip-download", "--output", "-", video_url]
    subprocess.run(command, check=True)
    vtt_file = next((f for f in os.listdir() if f.endswith(f"{language}.vtt")), None)
    with open(vtt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    os.remove(vtt_file)
    text = clean_text("".join(lines))
    summary = text if len(text) < 200 else summarizer(text[:800])[0]['summary_text']
    topics = predict_topic_with_gemini(summary).split(',')
    embed_url = f"https://www.youtube.com/embed/{video_url.split('v=')[-1].split('&')[0]}"
    cur = conn.cursor()
    cur.execute("SELECT id FROM videos WHERE url = %s", (video_url,))
    if cur.fetchone(): return
    cur.execute("""
        INSERT INTO videos (url, title, description, summary, transcription, embed_url, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, (video_url, title, description, summary, text, embed_url, datetime.utcnow()))
    vid = cur.fetchone()[0]
    for topic in map(str.strip, topics):
        cur.execute("SELECT id FROM categories WHERE topic = %s", (topic,))
        res = cur.fetchone()
        if res:
            cur.execute("INSERT INTO video_categories (video_id, category_id) VALUES (%s, %s)", (vid, res[0]))
    conn.commit()
'''