# Linux 서버 배포 가이드 - RAG QA 시스템

## 시스템 구성 요약

### 필요한 서버 구성
1. **웹서버**: Flask 기반 Python 웹 애플리케이션
2. **API 문서**: Swagger/OpenAPI 
3. **LLM 서버**: Ollama 기반 야놀자 LLM

### 권장 서버 스펙
- **최소 사양**: 
  - CPU: 8 cores
  - RAM: 16GB
  - Storage: 100GB SSD
  - GPU: RTX 3060 이상 (LLM 서버)

- **권장 사양**:
  - CPU: 16 cores
  - RAM: 32GB
  - Storage: 500GB NVMe SSD
  - GPU: RTX 4070 이상

## 1. 서버 초기 설정

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    nginx \
    supervisor \
    redis-server \
    sqlite3 \
    curl \
    wget \
    build-essential \
    python3-dev

# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/rag-qa-system
sudo chown $USER:$USER /opt/rag-qa-system
```

## 2. 프로젝트 파일 업로드

### 방법 1: Git을 사용한 배포
```bash
cd /opt
git clone https://your-repository-url/rag-qa-system.git
cd rag-qa-system
```

### 방법 2: 직접 파일 전송
```bash
# 로컬에서 서버로 전체 프로젝트 전송
scp -r /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system user@server:/opt/

# 또는 rsync 사용 (더 효율적)
rsync -avz --progress \
    /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system/ \
    user@server:/opt/rag-qa-system/
```

## 3. Python 환경 설정

```bash
cd /opt/rag-qa-system

# 가상환경 생성
python3.10 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# requirements.txt 생성 (없는 경우)
cat > requirements.txt << EOF
flask==3.0.0
flask-cors==4.0.0
langchain==0.1.0
langchain-community==0.1.0
chromadb==0.4.22
sentence-transformers==2.2.2
openai==1.6.1
python-dotenv==1.0.0
pandas==2.1.4
numpy==1.26.2
scikit-learn==1.3.2
redis==5.0.1
sqlalchemy==2.0.23
flasgger==0.9.7.1
gunicorn==21.2.0
gevent==23.9.1
python-docx==1.1.0
pypdf==3.17.4
tiktoken==0.5.2
ollama==0.1.7
EOF

# 의존성 설치
pip install -r requirements.txt
```

## 4. Ollama 및 야놀자 LLM 설치

```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# Ollama 서비스 시작
sudo systemctl start ollama
sudo systemctl enable ollama

# 야놀자 모델 다운로드
ollama pull llama3.1:8b-instruct-q4_0
ollama pull llama3.1:70b-instruct-q4_0
ollama pull llama3.2:3b-instruct-q8_0

# 모델 확인
ollama list
```

## 5. 환경 변수 설정

```bash
# .env 파일 생성
cat > /opt/rag-qa-system/.env << EOF
# Flask 설정
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# LLM 설정
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=your-openai-api-key-if-needed

# 야놀자 모델 설정
YANOLJA_TRAVEL_MODEL=llama3.1:8b-instruct-q4_0
YANOLJA_HOTEL_MODEL=llama3.1:8b-instruct-q4_0
YANOLJA_CUSTOMER_SERVICE_MODEL=llama3.2:3b-instruct-q8_0
YANOLJA_BOOKING_MODEL=llama3.1:70b-instruct-q4_0

# Vector DB 설정
CHROMA_PERSIST_DIRECTORY=/opt/rag-qa-system/chroma_db
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Redis 캐시
REDIS_URL=redis://localhost:6379/0

# 로그 설정
LOG_LEVEL=INFO
LOG_FILE=/var/log/rag-qa-system/app.log
EOF

# 로그 디렉토리 생성
sudo mkdir -p /var/log/rag-qa-system
sudo chown $USER:$USER /var/log/rag-qa-system
```

## 6. 데이터 초기화

```bash
cd /opt/rag-qa-system

# 가상환경 활성화
source venv/bin/activate

# Vector DB 초기화 (문서 로드)
python load_documents.py

# DB 상태 확인
python check_vectordb.py
```

## 7. Gunicorn 설정

```bash
# Gunicorn 설정 파일 생성
cat > /opt/rag-qa-system/gunicorn_config.py << EOF
import multiprocessing

# 서버 소켓
bind = "0.0.0.0:5000"
backlog = 2048

# 워커 프로세스
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 2

# 로깅
accesslog = "/var/log/rag-qa-system/access.log"
errorlog = "/var/log/rag-qa-system/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 프로세스 네이밍
proc_name = 'rag-qa-system'

# 서버 메커니즘
daemon = False
pidfile = "/var/run/rag-qa-system.pid"
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None
EOF
```

## 8. Systemd 서비스 설정

### Flask 애플리케이션 서비스
```bash
sudo tee /etc/systemd/system/rag-qa-system.service << EOF
[Unit]
Description=RAG QA System Flask Application
After=network.target redis.service ollama.service

[Service]
Type=notify
User=$USER
Group=$USER
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
```

### 야놀자 앱 서비스 (별도 포트)
```bash
sudo tee /etc/systemd/system/yanolja-app.service << EOF
[Unit]
Description=Yanolja RAG Application
After=network.target ollama.service

[Service]
Type=simple
User=$USER
Group=$USER
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

## 9. Nginx 리버스 프록시 설정

```bash
# Nginx 설정 파일 생성
sudo tee /etc/nginx/sites-available/rag-qa-system << EOF
upstream rag_qa_backend {
    server 127.0.0.1:5000 fail_timeout=0;
}

upstream yanolja_backend {
    server 127.0.0.1:5001 fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com;  # 실제 도메인으로 변경

    # 파일 업로드 크기 제한
    client_max_body_size 100M;

    # 타임아웃 설정
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # 정적 파일
    location /static {
        alias /opt/rag-qa-system/static;
        expires 30d;
    }

    # 메인 애플리케이션
    location / {
        proxy_pass http://rag_qa_backend;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Host \$http_host;
        proxy_redirect off;
        proxy_buffering off;
    }

    # 야놀자 애플리케이션
    location /yanolja {
        proxy_pass http://yanolja_backend;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Host \$http_host;
        proxy_redirect off;
        
        # SSE 스트리밍 지원
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }

    # Swagger UI
    location /swagger {
        proxy_pass http://rag_qa_backend/swagger;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Host \$http_host;
    }

    # API 문서
    location /apidocs {
        proxy_pass http://rag_qa_backend/apidocs;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Host \$http_host;
    }
}

# HTTPS 설정 (Let's Encrypt 사용 시)
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 위와 동일한 location 블록들...
}
EOF

# 사이트 활성화
sudo ln -s /etc/nginx/sites-available/rag-qa-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 10. 서비스 시작 및 관리

```bash
# 서비스 리로드
sudo systemctl daemon-reload

# 서비스 시작
sudo systemctl start redis
sudo systemctl start ollama
sudo systemctl start rag-qa-system
sudo systemctl start yanolja-app

# 부팅 시 자동 시작
sudo systemctl enable redis
sudo systemctl enable ollama
sudo systemctl enable rag-qa-system
sudo systemctl enable yanolja-app

# 서비스 상태 확인
sudo systemctl status rag-qa-system
sudo systemctl status yanolja-app
sudo systemctl status ollama
```

## 11. 로그 모니터링

```bash
# 실시간 로그 확인
sudo journalctl -u rag-qa-system -f
sudo journalctl -u yanolja-app -f

# 애플리케이션 로그
tail -f /var/log/rag-qa-system/app.log
tail -f /var/log/rag-qa-system/access.log

# Nginx 로그
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 12. 성능 튜닝

### 시스템 최적화
```bash
# 파일 디스크립터 제한 증가
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 커널 파라미터 최적화
sudo tee -a /etc/sysctl.conf << EOF
# 네트워크 최적화
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65000
EOF

sudo sysctl -p
```

### GPU 설정 (NVIDIA)
```bash
# NVIDIA 드라이버 설치
sudo apt install nvidia-driver-530

# CUDA 툴킷 설치
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-3

# 환경 변수 설정
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

## 13. 백업 및 복구

### 백업 스크립트
```bash
# 백업 스크립트 생성
cat > /opt/rag-qa-system/backup.sh << EOF
#!/bin/bash
BACKUP_DIR="/backup/rag-qa-system"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업 디렉토리 생성
mkdir -p \$BACKUP_DIR

# Vector DB 백업
tar -czf \$BACKUP_DIR/chroma_db_\$DATE.tar.gz /opt/rag-qa-system/chroma_db

# 설정 파일 백업
tar -czf \$BACKUP_DIR/config_\$DATE.tar.gz /opt/rag-qa-system/.env /opt/rag-qa-system/*.py

# 로그 백업
tar -czf \$BACKUP_DIR/logs_\$DATE.tar.gz /var/log/rag-qa-system

# 7일 이상 된 백업 삭제
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "백업 완료: \$DATE"
EOF

chmod +x /opt/rag-qa-system/backup.sh

# Cron 작업 추가 (매일 새벽 3시 백업)
echo "0 3 * * * /opt/rag-qa-system/backup.sh" | crontab -
```

## 14. 모니터링 설정

### 헬스체크 스크립트
```bash
cat > /opt/rag-qa-system/healthcheck.sh << EOF
#!/bin/bash

# 서비스 체크
check_service() {
    if systemctl is-active --quiet \$1; then
        echo "✅ \$1 is running"
    else
        echo "❌ \$1 is not running"
        systemctl start \$1
    fi
}

# 포트 체크
check_port() {
    if nc -z localhost \$1; then
        echo "✅ Port \$1 is open"
    else
        echo "❌ Port \$1 is closed"
    fi
}

echo "=== RAG QA System Health Check ==="
date

check_service "rag-qa-system"
check_service "yanolja-app"
check_service "ollama"
check_service "redis"
check_service "nginx"

check_port 5000  # Flask
check_port 5001  # Yanolja
check_port 11434 # Ollama
check_port 6379  # Redis
check_port 80    # Nginx

# API 헬스체크
curl -s http://localhost:5000/health | jq '.'
curl -s http://localhost:5001/health | jq '.'

echo "================================="
EOF

chmod +x /opt/rag-qa-system/healthcheck.sh
```

## 15. 보안 설정

### 방화벽 설정
```bash
# UFW 설치 및 설정
sudo apt install ufw

# 기본 정책
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 필요한 포트만 열기
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 방화벽 활성화
sudo ufw enable
```

### SSL 인증서 설정 (Let's Encrypt)
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

## 16. 문제 해결

### 일반적인 문제 해결
```bash
# 서비스 재시작
sudo systemctl restart rag-qa-system
sudo systemctl restart yanolja-app

# 로그 확인
journalctl -xe
tail -f /var/log/rag-qa-system/error.log

# 포트 사용 확인
sudo netstat -tlnp | grep -E '5000|5001|11434'

# 프로세스 확인
ps aux | grep -E 'gunicorn|python|ollama'

# 디스크 공간 확인
df -h

# 메모리 사용량 확인
free -h

# GPU 상태 확인
nvidia-smi
```

## 17. 성능 모니터링

### Prometheus + Grafana 설정 (선택사항)
```bash
# Prometheus 설치
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvf prometheus-2.45.0.linux-amd64.tar.gz
sudo mv prometheus-2.45.0.linux-amd64 /opt/prometheus

# Grafana 설치
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt update
sudo apt install grafana

# 서비스 시작
sudo systemctl start prometheus
sudo systemctl start grafana-server
```

## 18. 배포 체크리스트

- [ ] 시스템 요구사항 확인
- [ ] 필수 패키지 설치 완료
- [ ] Python 가상환경 설정
- [ ] 프로젝트 파일 업로드
- [ ] 환경 변수 설정 (.env)
- [ ] Ollama 및 LLM 모델 설치
- [ ] Vector DB 초기화
- [ ] 서비스 파일 생성
- [ ] Nginx 설정
- [ ] SSL 인증서 설정
- [ ] 방화벽 설정
- [ ] 백업 스크립트 설정
- [ ] 모니터링 설정
- [ ] 서비스 시작 및 테스트
- [ ] 로그 확인
- [ ] 성능 테스트

## 마무리

배포가 완료되면 다음 URL로 접속하여 확인:
- 메인 애플리케이션: http://your-domain.com
- 야놀자 애플리케이션: http://your-domain.com/yanolja
- Swagger API 문서: http://your-domain.com/swagger
- 헬스체크: http://your-domain.com/health

문제가 발생하면 로그를 확인하고, 필요시 서비스를 재시작하세요.