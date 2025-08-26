# 야놀자 RAG QA 시스템 설치 가이드

## 목차
1. [시스템 요구사항](#1-시스템-요구사항)
2. [기본 패키지 설치](#2-기본-패키지-설치)
3. [Ollama LLM 설치](#3-ollama-llm-설치)
4. [야놀자 모델 설치](#4-야놀자-모델-설치)
5. [Python 환경 구성](#5-python-환경-구성)
6. [서비스 설정](#6-서비스-설정)
7. [운영 관리](#7-운영-관리)
8. [문제 해결](#8-문제-해결)

---

## 1. 시스템 요구사항

### 하드웨어
- **CPU**: 4코어 이상 권장
- **RAM**: 최소 16GB (32GB 권장)
- **저장공간**: 50GB 이상 (모델 파일용)
- **OS**: Ubuntu 20.04 LTS 이상

### 소프트웨어
- Python 3.9+
- Redis Server
- Nginx (선택사항)

---

## 2. 기본 패키지 설치

### 시스템 업데이트
```bash
sudo apt update && sudo apt upgrade -y
```

### 필수 패키지 설치
```bash
sudo apt install -y \
    python3.9 \
    python3.9-venv \
    python3.9-dev \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    redis-server \
    nginx \
    supervisor \
    htop \
    net-tools
```

### Python 기본 버전 설정
```bash
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
python3 --version  # 3.9.x 확인
```

---

## 3. Ollama LLM 설치

### Ollama 설치
```bash
# 공식 설치 스크립트 실행
curl -fsSL https://ollama.com/install.sh | sh

# 설치 확인
ollama --version

# 서비스 활성화
sudo systemctl enable ollama
sudo systemctl start ollama

# 서비스 상태 확인
sudo systemctl status ollama
```

### Ollama 서비스 관리
```bash
# 서비스 시작
sudo systemctl start ollama

# 서비스 중지
sudo systemctl stop ollama

# 서비스 재시작
sudo systemctl restart ollama

# 로그 확인
sudo journalctl -u ollama -f
```

---

## 4. 야놀자 모델 설치

### 야놀자 특화 모델
야놀자 시스템은 용도별로 최적화된 4개의 모델을 사용합니다:

| 용도 | 모델명 | 크기 | 용도 |
|------|--------|------|------|
| 여행 상담 | llama3.1:8b-instruct-q4_0 | 4.7GB | 여행지, 맛집, 액티비티 추천 |
| 숙박 추천 | qwen2.5:7b-instruct | 4.4GB | 호텔/숙박 특화 추천 |
| 고객서비스 | solar:10.7b-instruct-v1-q4_0 | 6GB | 예약/취소/환불 안내 |
| 범용 | llama3.2:3b-instruct-korean | 2GB | 일반 질의응답 |

### 모델 다운로드
```bash
# 여행 상담 AI 모델
ollama pull llama3.1:8b-instruct-q4_0

# 숙박 추천 AI 모델  
ollama pull qwen2.5:7b-instruct

# 고객서비스 AI 모델 (메모리 충분시)
ollama pull solar:10.7b-instruct-v1-q4_0

# 범용 한국어 AI 모델
ollama pull llama3.2:3b-instruct-korean

# 설치된 모델 확인
ollama list
```

### 경량 모델 옵션 (메모리 부족시)
```bash
# 경량 모델만 설치
ollama pull llama3.2:3b-instruct-korean
ollama pull phi3:mini  # 3.8B 파라미터
ollama pull gemma:2b   # 2B 파라미터
```

---

## 5. Python 환경 구성

### 프로젝트 디렉토리 생성
```bash
# 야놀자 전용 디렉토리 생성
sudo mkdir -p /opt/yanolja/rag-system
sudo chown -R $USER:$USER /opt/yanolja
cd /opt/yanolja/rag-system
```

### 소스코드 배포
```bash
# Git clone 방식
git clone <repository-url> .

# 또는 SCP로 파일 전송
scp -r /local/path/to/rag-qa-system/* user@server:/opt/yanolja/rag-system/
```

### Python 가상환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip wheel setuptools

# 의존성 설치
pip install -r requirements.txt
```

### 환경변수 설정
```bash
# .env 파일 생성
cat > .env << 'EOF'
# 야놀자 프로젝트 설정
PROJECT_NAME=YANOLJA_RAG_SYSTEM
SECRET_KEY=yanolja-secret-key-$(date +%s)
FLASK_DEBUG=False
FLASK_PORT=5000
FLASK_HOST=0.0.0.0

# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434

# 야놀자 모델 설정
YANOLJA_TRAVEL_MODEL=llama3.1:8b-instruct-q4_0
YANOLJA_HOTEL_MODEL=qwen2.5:7b-instruct
YANOLJA_CS_MODEL=solar:10.7b-instruct-v1-q4_0
YANOLJA_GENERAL_MODEL=llama3.2:3b-instruct-korean

# 벡터 DB 설정
CHROMA_PERSIST_DIRECTORY=/opt/yanolja/rag-system/data/vectordb
CHROMA_COLLECTION_NAME=yanolja_documents

# 문서 처리
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_FILE_SIZE=52428800

# 야놀자 비즈니스 설정
YANOLJA_API_TIMEOUT=30
YANOLJA_MAX_RETRIES=3
YANOLJA_CACHE_TTL=3600
YANOLJA_MAX_CONCURRENT=4
YANOLJA_STREAMING=True

# 로깅
LOG_LEVEL=INFO
LOG_FILE=/opt/yanolja/logs/yanolja-rag.log
EOF
```

### 디렉토리 구조 생성
```bash
# 필수 디렉토리 생성
mkdir -p data/{documents,vectordb}
mkdir -p logs
mkdir -p static
mkdir -p templates

# 권한 설정
chmod -R 755 data/
chmod -R 755 logs/
```

---

## 6. 서비스 설정

### Redis 설정
```bash
# Redis 시작
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Redis 연결 테스트
redis-cli ping
# 응답: PONG
```

### Systemd 서비스 등록
```bash
# 야놀자 RAG 서비스 파일 생성
sudo tee /etc/systemd/system/yanolja-rag.service << 'EOF'
[Unit]
Description=Yanolja RAG QA System
After=network.target redis.service ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/yanolja/rag-system
Environment="PATH=/opt/yanolja/rag-system/venv/bin"
Environment="PYTHONPATH=/opt/yanolja/rag-system"
ExecStart=/opt/yanolja/rag-system/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/yanolja/logs/yanolja-rag.log
StandardError=append:/opt/yanolja/logs/yanolja-rag-error.log

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable yanolja-rag
sudo systemctl start yanolja-rag

# 서비스 상태 확인
sudo systemctl status yanolja-rag
```

### Nginx 리버스 프록시 설정
```bash
# Nginx 설정 파일 생성
sudo tee /etc/nginx/sites-available/yanolja-rag << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 실제 도메인으로 변경

    client_max_body_size 50M;  # 파일 업로드 크기 제한

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 타임아웃 설정 (LLM 응답 시간 고려)
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 정적 파일 직접 서빙
    location /static {
        alias /opt/yanolja/rag-system/static;
        expires 1d;
    }
}
EOF

# 설정 활성화
sudo ln -s /etc/nginx/sites-available/yanolja-rag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 7. 운영 관리

### 서비스 모니터링
```bash
# 실시간 로그 확인
tail -f /opt/yanolja/logs/yanolja-rag.log

# 시스템 리소스 모니터링
htop

# Ollama 프로세스 확인
ps aux | grep ollama

# 메모리 사용량 확인
free -h

# 디스크 사용량 확인
df -h /opt/yanolja
```

### 모델 관리
```bash
# 실행 중인 모델 확인
ollama ps

# 특정 모델 테스트
ollama run llama3.1:8b-instruct-q4_0 "안녕하세요"

# 모델 제거 (공간 확보)
ollama rm model-name

# 모델 정보 확인
ollama show llama3.1:8b-instruct-q4_0
```

### 백업 및 복구
```bash
# 벡터 DB 백업
tar -czf vectordb-backup-$(date +%Y%m%d).tar.gz /opt/yanolja/rag-system/data/vectordb

# 문서 백업
tar -czf documents-backup-$(date +%Y%m%d).tar.gz /opt/yanolja/rag-system/data/documents

# 전체 백업
tar -czf yanolja-rag-backup-$(date +%Y%m%d).tar.gz /opt/yanolja/rag-system
```

---

## 8. 문제 해결

### 일반적인 문제들

#### Ollama 연결 실패
```bash
# Ollama 서비스 확인
sudo systemctl status ollama

# 포트 확인
sudo netstat -tlnp | grep 11434

# 서비스 재시작
sudo systemctl restart ollama
```

#### 메모리 부족
```bash
# 사용하지 않는 모델 제거
ollama list
ollama rm unused-model

# 스왑 메모리 추가
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### Python 모듈 오류
```bash
# 가상환경 재활성화
deactivate
source /opt/yanolja/rag-system/venv/bin/activate

# 패키지 재설치
pip install --upgrade -r requirements.txt
```

### 성능 최적화

#### 모델 응답 속도 개선
```bash
# .env 파일에서 동시 요청 수 조정
YANOLJA_MAX_CONCURRENT=2  # 메모리 부족시 줄이기

# 캐시 TTL 증가
YANOLJA_CACHE_TTL=7200  # 2시간
```

#### 시스템 튜닝
```bash
# 파일 디스크립터 제한 증가
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 시스템 재시작
sudo reboot
```

---

## 빠른 설치 스크립트

전체 설치를 자동화하는 스크립트:

```bash
#!/bin/bash
# install_yanolja_all.sh

set -e

echo "🏨 야놀자 RAG 시스템 전체 설치 시작..."

# 1. 시스템 패키지 설치
echo "📦 [1/6] 시스템 패키지 설치..."
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev python3-pip \
    git curl wget build-essential redis-server nginx supervisor htop net-tools

# 2. Ollama 설치
echo "🤖 [2/6] Ollama 설치..."
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama

# 3. 야놀자 모델 다운로드
echo "📥 [3/6] 야놀자 AI 모델 다운로드..."
ollama pull llama3.1:8b-instruct-q4_0
ollama pull qwen2.5:7b-instruct
ollama pull llama3.2:3b-instruct-korean

# 4. 프로젝트 설정
echo "🔧 [4/6] 프로젝트 설정..."
sudo mkdir -p /opt/yanolja/rag-system
sudo chown -R $USER:$USER /opt/yanolja
cd /opt/yanolja/rag-system

# 5. Python 환경 구성
echo "🐍 [5/6] Python 환경 구성..."
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools

# 6. 서비스 시작
echo "🚀 [6/6] 서비스 시작..."
sudo systemctl start redis
mkdir -p data/{documents,vectordb} logs static templates

echo "✅ 야놀자 RAG 시스템 설치 완료!"
echo "📍 접속 주소: http://localhost:5000"
echo "📚 API 문서: http://localhost:5000/swagger/"
```

---

## 설치 후 확인사항

1. **서비스 상태 확인**
   ```bash
   sudo systemctl status ollama redis yanolja-rag
   ```

2. **웹 인터페이스 접속**
   - 메인 페이지: `http://your-server:5000`
   - API 문서: `http://your-server:5000/swagger/`

3. **모델 테스트**
   ```bash
   curl -X POST http://localhost:5000/api/yanolja/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "안녕하세요", "model_type": "travel"}'
   ```

---

## 지원 및 문의

- 프로젝트 담당자: 야놀자 AI팀
- 기술 지원: support@yanolja.com
- 문서 버전: 1.0.0
- 최종 업데이트: 2024-12-28