# 1. 使用官方輕量 Python 映像
# 選擇 slim 版本以減少映像大小，同時保持必要功能
FROM python:3.11-slim

# 2. 設定工作目錄
# 在容器中建立專用目錄，避免檔案混亂
WORKDIR /app

# 3. 複製並安裝依賴
# 先複製 requirements.txt 以利用 Docker 層快取機制
COPY requirements.txt .
# --no-cache-dir 可以減少映像大小
RUN pip install --no-cache-dir -r requirements.txt

# 安裝基本系統套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設置環境變數
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 4. 複製後端程式碼
COPY . /app/

# 5. 暴露 8000 端口
# Railway 會自動映射這個端口到外部
# 注意：實際端口可能會被 Railway 的環境變量覆蓋
EXPOSE 8080

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 使用uvicorn直接啟動，確保使用正確的PORT
# CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
# CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
# CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}

# 更新 CMD 使用 gunicorn 並設定多個工作者
# RUN pip install gunicorn

# 啟動命令
CMD gunicorn app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --log-level info