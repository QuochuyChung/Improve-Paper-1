# Image drift monitor (skelty-monitor:0.1). Build từ thư mục gốc repo:
#   docker build -f monitoring/Dockerfile -t skelty-monitor:0.1 .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 ARTIFACT_ROOT=/data
WORKDIR /app
COPY monitoring/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY monitoring/drift_check.py .
USER 65532:65532
CMD ["python", "/app/drift_check.py"]
