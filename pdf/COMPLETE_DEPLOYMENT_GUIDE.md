# RAG QA 시스템 완전 배포 가이드

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [LangChain 프레임워크 이해](#langchain-프레임워크-이해)
3. [Vector DB 및 청킹 전략 확인](#vector-db-및-청킹-전략-확인)
4. [서버 업로드 방법](#서버-업로드-방법)
5. [Linux 서버 배포](#linux-서버-배포)
6. [시스템 구성도](#시스템-구성도)
7. [운영 및 관리](#운영-및-관리)

---

## 1. 시스템 개요

### 🏗️ 전체 아키텍처
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    사용자       │    │   Nginx         │    │  Flask App      │
│   (브라우저)    │◄──►│ 리버스 프록시    │◄──►│   (5000)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                               ┌──────▼──────┐
                                               │  야놀자 앱   │
                                               │   (5001)   │
                                               └──────┬──────┘
                                                      │
┌─────────────────┐    ┌─────────────────┐    ┌──────▼──────┐
│   Vector DB     │    │     Redis       │    │   Ollama    │
│   (ChromaDB)    │    │    캐시         │    │LLM 서버(11434)│
└─────────────────┘    └─────────────────┘    └─────────────┘
```

### 🎯 핵심 구성요소
- **웹서버**: Flask (메인 RAG 시스템)
- **API 문서**: Swagger/OpenAPI 통합
- **LLM 서버**: Ollama + 야놀자 모델
- **Vector DB**: ChromaDB (문서 임베딩 저장)
- **캐시**: Redis (응답 캐싱)
- **프록시**: Nginx (로드 밸런싱, SSL)

---

## 2. LangChain 프레임워크 이해

### 🔗 LangChain이란?
LangChain은 **LLM 애플리케이션 개발을 위한 종합 프레임워크**입니다.

### 📚 주요 기능
1. **문서 로더**: PDF, DOCX, TXT 등 다양한 형식 지원
2. **텍스트 스플리터**: 문서를 적절한 크기로 청킹
3. **임베딩**: 텍스트를 벡터로 변환
4. **벡터스토어**: 벡터 DB 연결 및 관리
5. **체인**: RAG 파이프라인 구성
6. **메모리**: 대화 컨텍스트 관리

### 🔄 RAG 시스템에서의 역할
```
문서 → LangChain → 청킹 → 임베딩 → Vector DB
                                      ↓
사용자 질문 → 임베딩 → 유사도 검색 → 컨텍스트 → LLM
```

### 💻 코드 예시
```python
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma

# 문서 로드
loader = PyPDFLoader("document.pdf")
documents = loader.load()

# 청킹 전략
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150
)
chunks = text_splitter.split_documents(documents)

# 임베딩 및 벡터 저장
embeddings = HuggingFaceEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)
```

---

## 3. Vector DB 및 청킹 전략 확인

### 🔍 Vector DB 상태 확인
```bash
# Vector DB 데이터 확인
python3 check_vectordb.py
```

**실행 결과 예시:**
```
🔍 Vector DB 데이터 확인 중...
============================================================
📁 Vector DB 경로: ./data/vectordb
📊 컬렉션 목록:

1. 컬렉션명: custom_chunks
   - 문서 수: 92개
   - 메타데이터 필드: [source, chunk_index, chunking_strategy]

2. 컬렉션명: basic_chunks  
   - 문서 수: 92개
   - 메타데이터 필드: [source, chunk_index, file_type]

📊 문서 수 통계:
   - 기본 청킹: 92개
   - 커스텀 청킹: 92개
   - 전체: 184개

💾 디스크 사용량:
   - Vector DB 총 크기: 79.53 MB
```

### ✂️ 청킹 전략 테스트
```bash
# 청킹 전략 확인
python3 check_chunking.py
```

**실행 결과 예시:**
```
✂️ Chunking 전략 확인
============================================================
📋 사용 가능한 청킹 전략:
   1. basic - 기본 청킹 (800자/150중첩)
   2. semantic - 의미 기반 청킹  
   3. hybrid - 하이브리드 청킹
   4. custom_delimiter - 커스텀 구분자 (/$$/)

🔹 CUSTOM_DELIMITER 전략 테스트:
📊 청킹 결과:
   - 청크 개수: 3
   - 평균 청크 크기: 104.3자

   청크 #1: 제1장 연회비 안내...
   청크 #2: 제2장 연회비 면제 조건...
   청크 #3: 제3장 특별 혜택...
```

### 📈 청킹 전략 비교

| 전략 | 특징 | 사용 시기 |
|------|------|-----------|
| **Basic** | 고정 크기 분할 | 일반 문서 |
| **Semantic** | 의미 단위 분할 | 구조화된 문서 |
| **Hybrid** | 기본+의미 결합 | 복합 문서 |
| **Custom Delimiter** | 구분자 기반 | 특별 포맷 문서 |

---

## 4. 서버 업로드 방법

### 📁 업로드할 파일 목록
```
rag-qa-system/
├── app.py                    # 메인 Flask 앱
├── yanolja_app.py           # 야놀자 전용 앱  
├── config.py                # 설정 파일
├── yanolja_config.py        # 야놀자 설정
├── yanolja_llm_client.py    # LLM 클라이언트
├── requirements.txt         # Python 의존성
├── .env                     # 환경 변수
├── models/                  # 모델 클래스들
│   ├── embeddings.py
│   ├── vectorstore.py
│   └── dual_llm.py
├── routes/                  # API 라우트
│   ├── chat.py
│   └── unified_benchmark.py
├── services/                # 서비스 로직
│   ├── chunking_strategies.py
│   ├── document_processor.py
│   └── rag_chain.py  
├── templates/               # HTML 템플릿
│   ├── main_rag_system.html
│   └── yanolja_main.html
├── static/                  # 정적 파일
├── data/                    # 데이터 파일
│   └── vectordb/           # Vector DB
└── check_*.py              # 확인 스크립트
```

### 🚀 업로드 방법

#### 방법 1: SCP를 사용한 업로드
```bash
# 전체 프로젝트 압축
cd /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/
tar -czf rag-qa-system.tar.gz rag-qa-system/

# 서버로 업로드
scp rag-qa-system.tar.gz user@your-server.com:/tmp/

# 서버에서 압축 해제
ssh user@your-server.com
cd /tmp
sudo tar -xzf rag-qa-system.tar.gz -C /opt/
sudo chown -R $USER:$USER /opt/rag-qa-system
```

#### 방법 2: Rsync를 사용한 동기화
```bash
# 효율적인 파일 동기화
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system/ \
    user@your-server.com:/opt/rag-qa-system/
```

#### 방법 3: Git을 사용한 배포
```bash
# 로컬에서 Git 저장소 초기화
cd /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system
git init
git add .
git commit -m "Initial commit"
git remote add origin https://your-git-repository.git
git push -u origin main

# 서버에서 클론
ssh user@your-server.com
cd /opt
git clone https://your-git-repository.git rag-qa-system
```

#### 방법 4: 스테이징 배포 스크립트
```bash
#!/bin/bash
# deploy.sh 

SERVER="user@your-server.com"
LOCAL_PATH="/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system"
REMOTE_PATH="/opt/rag-qa-system"

echo "🚀 RAG QA 시스템 배포 시작..."

# 1. 백업 생성
ssh $SERVER "sudo cp -r $REMOTE_PATH ${REMOTE_PATH}.backup.$(date +%Y%m%d_%H%M%S)"

# 2. 파일 업로드
rsync -avz --delete \
    --exclude='data/vectordb' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    $LOCAL_PATH/ $SERVER:$REMOTE_PATH/

# 3. 서비스 재시작
ssh $SERVER << 'EOF'
cd /opt/rag-qa-system
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rag-qa-system
sudo systemctl restart yanolja-app
EOF

echo "✅ 배포 완료!"
```

---

## 5. Linux 서버 배포

### 🖥️ 서버 요구사항

#### 최소 사양
- **OS**: Ubuntu 22.04 LTS 이상
- **CPU**: 8 cores (Intel/AMD)
- **RAM**: 16GB
- **Storage**: 100GB SSD
- **GPU**: RTX 3060 이상 (LLM 추론용)

#### 권장 사양  
- **CPU**: 16 cores
- **RAM**: 32GB
- **Storage**: 500GB NVMe SSD
- **GPU**: RTX 4070 이상

### 🔧 Step 1: 시스템 초기 설정

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y \
    python3.10 python3.10-venv python3-pip \
    git nginx supervisor redis-server sqlite3 \
    curl wget build-essential python3-dev \
    software-properties-common apt-transport-https

# NVIDIA 드라이버 설치 (GPU 사용 시)
sudo apt install nvidia-driver-530 nvidia-cuda-toolkit

# Docker 설치 (선택사항)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### ⚡ Step 2: Ollama 및 LLM 설치

```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 시스템 서비스 등록
sudo systemctl start ollama
sudo systemctl enable ollama

# 야놀자 모델 다운로드
ollama pull llama3.1:8b-instruct-q4_0
ollama pull llama3.1:70b-instruct-q4_0  
ollama pull llama3.2:3b-instruct-q8_0

# 모델 확인
ollama list
```

### 🐍 Step 3: Python 환경 설정

```bash
# 프로젝트 디렉토리로 이동
cd /opt/rag-qa-system

# 가상환경 생성
python3.10 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
nano .env  # 환경 변수 수정
```

### 🗃️ Step 4: 데이터베이스 초기화

```bash
# Vector DB 초기화
python3 load_documents.py

# 상태 확인
python3 check_vectordb.py
python3 check_chunking.py

# Redis 설정
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 🌐 Step 5: 웹서버 설정

#### Gunicorn 설정
```bash
# Gunicorn 설정 파일 생성
cat > gunicorn_config.py << 'EOF'
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
timeout = 120
keepalive = 2

accesslog = "/var/log/rag-qa-system/access.log"
errorlog = "/var/log/rag-qa-system/error.log"
loglevel = "info"

proc_name = 'rag-qa-system'
EOF
```

#### Systemd 서비스 등록
```bash
# 메인 앱 서비스
sudo tee /etc/systemd/system/rag-qa-system.service << 'EOF'
[Unit]
Description=RAG QA System Flask Application
After=network.target redis.service ollama.service

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/rag-qa-system
Environment="PATH=/opt/rag-qa-system/venv/bin"
ExecStart=/opt/rag-qa-system/venv/bin/gunicorn \
    --config /opt/rag-qa-system/gunicorn_config.py \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 야놀자 앱 서비스  
sudo tee /etc/systemd/system/yanolja-app.service << 'EOF'
[Unit]
Description=Yanolja RAG Application
After=network.target ollama.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/rag-qa-system
Environment="PATH=/opt/rag-qa-system/venv/bin"
Environment="FLASK_APP=yanolja_app.py"
ExecStart=/opt/rag-qa-system/venv/bin/python yanolja_app.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 🔄 Step 6: Nginx 리버스 프록시 설정

```bash
# Nginx 설정 파일
sudo tee /etc/nginx/sites-available/rag-qa-system << 'EOF'
upstream rag_qa_backend {
    server 127.0.0.1:5000;
}

upstream yanolja_backend {
    server 127.0.0.1:5001;
}

server {
    listen 80;
    server_name your-domain.com;  # 실제 도메인으로 변경
    
    client_max_body_size 100M;
    
    # 정적 파일
    location /static {
        alias /opt/rag-qa-system/static;
        expires 30d;
    }
    
    # 메인 애플리케이션  
    location / {
        proxy_pass http://rag_qa_backend;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;
    }
    
    # 야놀자 애플리케이션
    location /yanolja {
        proxy_pass http://yanolja_backend;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        
        # SSE 스트리밍 지원
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
    }
    
    # Swagger API 문서
    location /swagger {
        proxy_pass http://rag_qa_backend/swagger;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
    }
}
EOF

# 설정 활성화
sudo ln -s /etc/nginx/sites-available/rag-qa-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 🚀 Step 7: 서비스 시작

```bash
# 로그 디렉토리 생성
sudo mkdir -p /var/log/rag-qa-system
sudo chown ubuntu:ubuntu /var/log/rag-qa-system

# 서비스 리로드 및 시작
sudo systemctl daemon-reload

sudo systemctl start redis-server
sudo systemctl start ollama  
sudo systemctl start rag-qa-system
sudo systemctl start yanolja-app
sudo systemctl start nginx

# 부팅 시 자동 시작
sudo systemctl enable redis-server
sudo systemctl enable ollama
sudo systemctl enable rag-qa-system  
sudo systemctl enable yanolja-app
sudo systemctl enable nginx

# 상태 확인
sudo systemctl status rag-qa-system
sudo systemctl status yanolja-app
sudo systemctl status ollama
```

### 🔐 Step 8: 보안 설정

```bash
# 방화벽 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# SSL 인증서 설정 (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

---

## 6. 시스템 구성도

### 🏗️ 전체 시스템 아키텍처

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │   (Nginx:80,443)│
                    └─────────┬───────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
    │  Flask App     │ │ Yanolja App │ │   Static   │
    │   (5000)       │ │   (5001)    │ │   Files    │
    └─────────┬──────┘ └─────┬──────┘ └────────────┘
              │               │
              └───────┬───────┘
                      │
          ┌───────────▼───────────┐
          │     Service Layer     │
          └───────────┬───────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼───┐ ┌──────▼──────┐ ┌─────▼─────┐
│Vector │ │   Ollama    │ │   Redis   │
│  DB   │ │LLM(11434)   │ │ Cache(6379)│
│(Chroma│ │             │ │           │
│  DB)  │ └─────────────┘ └───────────┘
└───────┘
```

### 📊 데이터 플로우

```
1. 사용자 요청 → Nginx → Flask App
                         │
2. 질문 분석 ← ─ ─ ─ ─ ─ ─ ┘
   │
3. Vector DB 검색 → 유사 문서 검색
   │
4. 컨텍스트 생성 → Ollama LLM 호출
   │
5. 응답 생성 → 캐싱(Redis) → 사용자
```

### 🔄 RAG 파이프라인 상세

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    문서     │    │    청킹     │    │   임베딩    │  
│  (PDF,DOCX) │───►│ (4가지전략)  │───►│(HuggingFace)│
└─────────────┘    └─────────────┘    └──────┬──────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐
│  사용자응답  │    │ LLM 생성    │    │  Vector DB  │
│             │◄───│  (야놀자)   │    │ (ChromaDB)  │
└─────────────┘    └──────▲──────┘    └──────┬──────┘
                          │                  │
                   ┌──────┴──────┐    ┌──────▼──────┐
                   │ 프롬프트+    │    │ 유사도 검색  │
                   │  컨텍스트    │◄───│ (Top-K)    │
                   └─────────────┘    └─────────────┘
```

---

## 7. 운영 및 관리

### 📈 모니터링

#### 로그 확인
```bash
# 실시간 로그 모니터링
sudo journalctl -u rag-qa-system -f
sudo journalctl -u yanolja-app -f
tail -f /var/log/rag-qa-system/error.log

# Nginx 로그
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

#### 헬스체크 스크립트
```bash
#!/bin/bash
# healthcheck.sh

check_service() {
    if systemctl is-active --quiet $1; then
        echo "✅ $1 is running"
    else
        echo "❌ $1 is not running"
        sudo systemctl start $1
    fi
}

check_port() {
    if nc -z localhost $1; then
        echo "✅ Port $1 is open"  
    else
        echo "❌ Port $1 is closed"
    fi
}

echo "=== RAG QA System Health Check ==="
check_service "rag-qa-system"
check_service "yanolja-app" 
check_service "ollama"
check_service "redis-server"
check_service "nginx"

check_port 5000  # Flask
check_port 5001  # Yanolja  
check_port 11434 # Ollama
check_port 6379  # Redis
check_port 80    # Nginx

# API 헬스체크
curl -s http://localhost:5000/health
curl -s http://localhost:5001/health
```

### 💾 백업 및 복구

#### 자동 백업 스크립트
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/rag-qa-system"  
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Vector DB 백업
tar -czf $BACKUP_DIR/vectordb_$DATE.tar.gz /opt/rag-qa-system/data/vectordb

# 설정 파일 백업
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/rag-qa-system/.env /opt/rag-qa-system/*.py

# 로그 백업  
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /var/log/rag-qa-system

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "백업 완료: $DATE"
```

#### Cron 작업 등록
```bash
# 매일 새벽 3시 백업
echo "0 3 * * * /opt/rag-qa-system/backup.sh" | crontab -

# 매주 일요일 시스템 업데이트
echo "0 4 * * 0 sudo apt update && sudo apt upgrade -y" | crontab -
```

### 🔧 성능 튜닝

#### 시스템 최적화
```bash
# 파일 디스크립터 제한 증가
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 커널 파라미터 최적화  
sudo tee -a /etc/sysctl.conf << 'EOF'
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
EOF
sudo sysctl -p
```

#### Gunicorn 워커 최적화
```python
# gunicorn_config.py 튜닝
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # 비동기 처리
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
```

### 🚨 문제 해결

#### 일반적인 문제들

**1. 서비스 시작 실패**
```bash
# 로그 확인
sudo journalctl -xe -u rag-qa-system

# 포트 충돌 확인
sudo netstat -tlnp | grep 5000

# 프로세스 강제 종료
sudo pkill -f gunicorn
```

**2. Vector DB 접근 오류**
```bash
# 권한 확인
ls -la /opt/rag-qa-system/data/vectordb
sudo chown -R ubuntu:ubuntu /opt/rag-qa-system

# DB 재초기화
rm -rf /opt/rag-qa-system/data/vectordb/*
python3 load_documents.py
```

**3. LLM 연결 실패**
```bash
# Ollama 상태 확인
sudo systemctl status ollama
ollama list

# 모델 재다운로드
ollama pull llama3.1:8b-instruct-q4_0
```

**4. 메모리 부족**
```bash
# 메모리 사용량 확인
free -h
ps aux --sort=-%mem | head -10

# 스왑 추가
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 📊 성능 메트릭

#### 모니터링 지표
- **응답시간**: < 3초 (RAG 응답)
- **처리량**: > 100 requests/분
- **가용성**: > 99.9%
- **메모리 사용**: < 80%
- **CPU 사용**: < 70%
- **디스크 사용**: < 80%

#### 부하 테스트
```bash
# Apache Bench로 부하 테스트
ab -n 1000 -c 10 http://your-domain.com/health

# wrk로 더 정교한 테스트
wrk -t12 -c400 -d30s http://your-domain.com/
```

---

## 8. 배포 체크리스트 

### 📋 배포 전 체크리스트
- [ ] 서버 사양 확인 (CPU, RAM, GPU)
- [ ] Ubuntu 22.04 설치 완료
- [ ] 필수 패키지 설치
- [ ] Python 3.10 환경 설정
- [ ] Git 또는 파일 업로드 준비

### 🔧 설치 체크리스트  
- [ ] Ollama 설치 및 모델 다운로드
- [ ] Redis 서버 설치
- [ ] Nginx 설치 및 설정
- [ ] 프로젝트 파일 업로드
- [ ] Python 가상환경 및 의존성 설치
- [ ] 환경변수 설정 (.env)

### 🚀 실행 체크리스트
- [ ] Vector DB 초기화
- [ ] Systemd 서비스 등록  
- [ ] 서비스 시작 및 활성화
- [ ] Nginx 프록시 설정
- [ ] SSL 인증서 설정
- [ ] 방화벽 설정

### ✅ 검증 체크리스트
- [ ] 웹 인터페이스 접속 확인
- [ ] API 엔드포인트 테스트
- [ ] Swagger 문서 접근 확인
- [ ] 헬스체크 응답 확인
- [ ] 로그 생성 확인
- [ ] 백업 스크립트 테스트

### 📞 접속 URL 확인
- **메인 시스템**: http://your-domain.com
- **야놀자 앱**: http://your-domain.com/yanolja  
- **API 문서**: http://your-domain.com/swagger
- **헬스체크**: http://your-domain.com/health

---

## 9. 결론

이 가이드를 통해 RAG QA 시스템을 Linux 서버에 성공적으로 배포할 수 있습니다. 

### 🎯 핵심 포인트
1. **LangChain**: LLM 애플리케이션 개발 프레임워크
2. **Vector DB**: ChromaDB로 임베딩 벡터 저장
3. **청킹 전략**: 4가지 전략으로 문서 최적화
4. **배포 방법**: SCP, Rsync, Git 중 선택
5. **시스템 구성**: 웹서버 1개 + Swagger + LLM 서버

### 🔄 운영 팁
- 정기적인 백업 수행
- 로그 모니터링 
- 성능 지표 추적
- 보안 업데이트 적용

성공적인 배포를 위해 단계별로 천천히 진행하시고, 문제 발생 시 로그를 먼저 확인하시기 바랍니다!