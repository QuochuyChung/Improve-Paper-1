# Build từ thư mục gốc repo: docker build -f serving/Dockerfile -t skelty-serving:0.1 .
# Phiên bản scikit-learn phải khớp với image pipeline (skelty-poc:0.1) đã sinh model.joblib.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 ARTIFACT_ROOT=/data STATS_WINDOW=200
WORKDIR /app
COPY serving/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY serving/app.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
