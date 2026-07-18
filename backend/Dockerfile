FROM python:3.12-slim

# Cài tesseract + gói tiếng Việt cho OCR fallback
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-vie \
      libgl1 \
      libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements trước để tận dụng Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code vào /app/backend/ (giữ đúng cấu trúc import `backend.xxx`)
COPY . ./backend/

EXPOSE 8000

# main.py sys.path.append("../../") sẽ thêm /app vào path
# → import backend.kb.kb đúng vì có /app/backend/kb/kb.py
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
