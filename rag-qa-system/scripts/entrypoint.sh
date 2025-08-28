#!/bin/bash
set -e

echo "🚀 RAG QA System 시작 중..."

# 환경 변수 확인
echo "환경 확인:"
echo "- Python 버전: $(python --version)"
echo "- 작업 디렉토리: $(pwd)"
echo "- FLASK_ENV: ${FLASK_ENV}"

# 필요한 디렉토리 생성
mkdir -p /app/data /app/logs /app/s3 /app/s3-chunking /app/s3-common

# 데이터베이스 초기화 (첫 실행시)
if [ ! -f "/app/data/initialized" ]; then
    echo "🔧 데이터베이스 초기화 중..."
    python -c "
from services.commercial_features import commercial_system
from services.security_monitoring import monitoring_system
from services.real_time_learning import learning_system

# 초기화 수행
print('상업화 시스템 초기화...')
user = commercial_system.user_db.create_user('admin', 'admin@example.com', 'enterprise')
print(f'관리자 계정 생성: API 키 = {user.api_key}')

print('보안 모니터링 초기화...')
monitoring_system.start_continuous_monitoring(60)

print('학습 시스템 초기화...')
learning_system.start_continuous_learning(24)

print('초기화 완료!')
"
    touch /app/data/initialized
    echo "✅ 초기화 완료"
fi

# 벡터 DB 초기화 (문서가 있는 경우)
if [ "$(ls -A /app/s3 2>/dev/null)" ] || [ "$(ls -A /app/s3-chunking 2>/dev/null)" ]; then
    echo "📚 문서 로딩 중..."
    python load_documents.py
    echo "✅ 문서 로딩 완료"
else
    echo "⚠️ 문서 폴더가 비어있습니다. s3, s3-chunking 폴더에 문서를 추가해주세요."
fi

# 헬스체크 엔드포인트 추가
echo "🏥 헬스체크 설정 중..."
cat > /tmp/health_check.py << 'EOF'
from flask import Flask, jsonify
import sys
import os
sys.path.append('/app')

app = Flask(__name__)

@app.route('/health')
def health_check():
    try:
        # 기본 시스템 상태 확인
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # 데이터베이스 연결 확인
        import sqlite3
        conn = sqlite3.connect('/app/data/users.db')
        conn.close()
        
        status = {
            "status": "healthy",
            "timestamp": "$(date -Iseconds)",
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_free": psutil.disk_usage('/').free
            },
            "services": {
                "database": "ok",
                "vector_store": "ok"
            }
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": "$(date -Iseconds)"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
EOF

# 헬스체크 서버를 백그라운드에서 실행
python /tmp/health_check.py &

# 메인 애플리케이션 실행 준비
echo "🎯 메인 애플리케이션 시작..."

# 프로덕션 환경에서는 Gunicorn 사용
if [ "$FLASK_ENV" = "production" ]; then
    echo "🏭 프로덕션 모드로 시작 (Gunicorn)"
    exec gunicorn --bind 0.0.0.0:5001 \
                  --workers 4 \
                  --worker-class gevent \
                  --worker-connections 1000 \
                  --timeout 300 \
                  --keep-alive 2 \
                  --max-requests 1000 \
                  --max-requests-jitter 100 \
                  --preload \
                  --access-logfile /app/logs/access.log \
                  --error-logfile /app/logs/error.log \
                  --log-level info \
                  app:app
else
    echo "🔧 개발 모드로 시작 (Flask)"
    exec python app.py
fi