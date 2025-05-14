# 1. 使用官方輕量 Python 映像
FROM python:3.11-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 複製並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 複製後端程式碼
COPY ./app /app/app

# 5. 暴露 8000 端口
EXPOSE 8000

# 6. 使用多工，提高 FastAPI 伺服器效能
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
