# Image pipeline huấn luyện (skelty-poc:0.1). Build từ thư mục gốc repo:
#   docker build -t skelty-poc:0.1 .
# Phiên bản scikit-learn ở đây phải khớp serving/requirements.txt (model.joblib do image này sinh ra).
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 ARTIFACT_ROOT=/data PYTHONPATH=/app/pipeline
WORKDIR /app
COPY pipeline/requirements.txt pipeline/requirements.txt
RUN pip install --no-cache-dir -r pipeline/requirements.txt
COPY pipeline/*.py pipeline/
