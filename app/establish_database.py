import psycopg2
from download_video import login_postgresql
# 改成你自己的 Render 資料庫資訊
try:
    conn = login_postgresql()
    print("成功")
except Exception as e:
        print(" 連線失敗：", e)
        
cursor = conn.cursor()
# 建立 videos 資料表
cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    description TEXT,
    summary TEXT,
    transcription TEXT,
    transcription_with_time JSONB,
    duration_str VARCHAR(20),
    embed_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# 建立 categories（靜態主題表）
cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    topic TEXT UNIQUE NOT NULL
);
""")

# 建立 video_categories（影片對應主題，多對多）
cursor.execute("""
CREATE TABLE IF NOT EXISTS video_categories (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE
);
""")

cursor.execute("""
INSERT INTO categories (topic) VALUES 
('Computer Science'),
('Law'),
('Mathematics'),
('Physics'),
('Chemistry'),
('Biology'),
('Earth Science'),
('History'),
('Geography'),
('Sports'),
('Literature'),
('Astronnomy'),
('Daily Life');
""")
conn.commit()
print("✅ 成功建立三個資料表！並插入categories")
cursor.close()
conn.close()