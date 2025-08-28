# 상업화 RAG QA 시스템 Dockerfile
FROM python:3.11-slim

# 시스템 패키지 설치 및 업데이트
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    sqlite3 \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY . .

# 필요한 디렉토리 생성
RUN mkdir -p /app/data /app/logs /app/s3 /app/s3-chunking /app/s3-common

# 권한 설정
RUN chmod +x /app/scripts/entrypoint.sh

# Nginx 설정
COPY docker/nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Supervisor 설정
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf

# 환경 변수
ENV PYTHONPATH=/app
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# 포트 노출
EXPOSE 80 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# 엔트리포인트
CMD ["/app/scripts/entrypoint.sh"]