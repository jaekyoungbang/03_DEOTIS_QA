# 🐧 Linux 서버 설치 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [로컬 LLM 설치 (Ollama)](#로컬-llm-설치-ollama)
3. [Python RAG 시스템 설치](#python-rag-시스템-설치)
4. [서비스 설정](#서비스-설정)
5. [Nginx 설정](#nginx-설정)
6. [모니터링 & 관리](#모니터링--관리)

---

## 🖥 시스템 요구사항

### 최소 사양
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 4 코어 이상
- **RAM**: 8GB 이상 (LLM 모델에 따라 16GB+ 권장)
- **Storage**: 50GB 이상 (모델 저장용)
- **Network**: 인터넷 연결 (모델 다운로드용)

### 권장 사양
- **CPU**: 8 코어 이상
- **RAM**: 32GB 이상
- **Storage**: 200GB SSD
- **GPU**: NVIDIA GPU (옵션, 성능 향상용)

---

## 🤖 로컬 LLM 설치 (Ollama)

### 1단계: 시스템 업데이트 및 기본 패키지 설치

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git python3 python3-pip python3-venv nginx

# CentOS/RHEL/Rocky Linux
sudo dnf update -y
sudo dnf install -y curl wget git python3 python3-pip nginx
```

### 2단계: Ollama 설치

```bash
# 1. Ollama 설치 스크립트 실행
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 설치 확인
ollama --version
```

### 3단계: Ollama 사용자 및 디렉토리 생성

```bash
# 1. ollama 시스템 사용자 생성
sudo useradd -r -s /bin/false -d /opt/ollama ollama

# 2. 모델 저장 디렉토리 생성
sudo mkdir -p /opt/ollama/models
sudo chown -R ollama:ollama /opt/ollama
```

### 4단계: Ollama 서비스 설정

```bash
# Systemd 서비스 파일 생성
sudo tee /etc/systemd/system/ollama.service <<'EOF'
[Unit]
Description=Ollama Local LLM Server
Documentation=https://ollama.ai/
After=network.target

[Service]
Type=exec
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/opt/ollama/models"
Environment="OLLAMA_DATA=/opt/ollama/data"

[Install]
WantedBy=multi-user.target
EOF
```

### 5단계: 서비스 시작 및 활성화

```bash
# 1. Systemd 데몬 리로드
sudo systemctl daemon-reload

# 2. 서비스 활성화 및 시작
sudo systemctl enable ollama
sudo systemctl start ollama

# 3. 서비스 상태 확인
sudo systemctl status ollama
```

### 6단계: 기본 모델 다운로드

```bash
# 1. 기본 한국어 모델 설치
sudo -u ollama ollama pull llama3.2:3b
sudo -u ollama ollama pull qwen2.5:7b

# 2. 야놀자 커스텀 모델 (실제 모델명으로 변경)
# sudo -u ollama ollama pull yanolja/custom-model:latest

# 3. 설치된 모델 확인
sudo -u ollama ollama list
```

### 7단계: 방화벽 설정 (필요시)

```bash
# UFW (Ubuntu)
sudo ufw allow 11434/tcp

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=11434/tcp
sudo firewall-cmd --reload
```

### 8단계: Ollama API 테스트

```bash
# 1. API 연결 테스트
curl http://localhost:11434/api/tags

# 2. 모델 추론 테스트
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "안녕하세요",
    "stream": false
  }'
```

---

## 🐍 Python RAG 시스템 설치

### 1단계: 프로젝트 디렉토리 설정

```bash
# 1. 프로젝트 디렉토리 생성
sudo mkdir -p /opt/rag-qa-system
cd /opt/rag-qa-system

# 2. 현재 사용자에게 권한 부여
sudo chown -R $USER:$USER /opt/rag-qa-system
```

### 2단계: 소스 코드 배포

```bash
# 방법 1: Git을 통한 클론 (추천)
git clone <your-repository-url> .

# 방법 2: 파일 업로드 (SCP/SFTP 사용)
# scp -r ./rag-qa-system/* user@server:/opt/rag-qa-system/

# 방법 3: 압축 파일 업로드
# tar -czf rag-qa-system.tar.gz ./rag-qa-system/
# scp rag-qa-system.tar.gz user@server:/opt/
# tar -xzf /opt/rag-qa-system.tar.gz -C /opt/
```

### 3단계: Python 가상환경 설정

```bash
# 1. 가상환경 생성
cd /opt/rag-qa-system
python3 -m venv venv

# 2. 가상환경 활성화
source venv/bin/activate

# 3. pip 업그레이드
pip install --upgrade pip

# 4. 의존성 패키지 설치
pip install -r requirements.txt
```

### 4단계: 환경변수 설정

```bash
# .env 파일 생성
tee /opt/rag-qa-system/.env <<'EOF'
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Flask 설정
FLASK_DEBUG=False
FLASK_PORT=5000
SECRET_KEY=your_secret_key_here

# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.2:3b

# 벡터 DB 설정
CHROMA_PERSIST_DIRECTORY=/opt/rag-qa-system/data/vectordb

# 캐시 설정 (Redis 사용 시)
# REDIS_URL=redis://localhost:6379

# 로그 레벨
LOG_LEVEL=INFO
EOF

# 환경변수 파일 권한 설정 (보안)
chmod 600 /opt/rag-qa-system/.env
```

### 5단계: 데이터 디렉토리 생성

```bash
# 필요한 디렉토리들 생성
mkdir -p /opt/rag-qa-system/data/{vectordb,documents,cache,config}

# 권한 설정
chown -R $USER:$USER /opt/rag-qa-system/data
```

### 6단계: 초기 문서 로딩 (선택사항)

```bash
# S3 문서 로딩 (문서가 있는 경우)
cd /opt/rag-qa-system
source venv/bin/activate
python load_documents.py
```

---

## 🔧 서비스 설정

### 1단계: RAG QA 시스템 서비스 생성

```bash
# Systemd 서비스 파일 생성
sudo tee /etc/systemd/system/rag-qa.service <<EOF
[Unit]
Description=RAG QA System with Dual LLM
Documentation=https://github.com/your-repo/rag-qa-system
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/rag-qa-system
ExecStart=/opt/rag-qa-system/venv/bin/python app.py
Restart=always
RestartSec=5
Environment="PATH=/opt/rag-qa-system/venv/bin"
EnvironmentFile=/opt/rag-qa-system/.env

# 리소스 제한
MemoryMax=4G
CPUQuota=200%

# 보안 설정
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF
```

### 2단계: 서비스 등록 및 시작

```bash
# 1. Systemd 데몬 리로드
sudo systemctl daemon-reload

# 2. 서비스 활성화 및 시작
sudo systemctl enable rag-qa
sudo systemctl start rag-qa

# 3. 서비스 상태 확인
sudo systemctl status rag-qa
```

### 3단계: 서비스 테스트

```bash
# 1. 애플리케이션 포트 확인
sudo netstat -tlnp | grep 5000

# 2. 헬스체크
curl http://localhost:5000/health

# 3. Swagger UI 확인
curl http://localhost:5000/swagger/
```

---

## 🌐 Nginx 설정

### 1단계: Nginx 설정 파일 생성

```bash
# Nginx 사이트 설정 파일 생성
sudo tee /etc/nginx/sites-available/rag-qa <<'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 실제 도메인으로 변경
    
    # 클라이언트 업로드 크기 제한
    client_max_body_size 100M;
    
    # 메인 애플리케이션
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 스트리밍 지원
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Swagger UI
    location /swagger {
        proxy_pass http://127.0.0.1:5000/swagger;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 정적 파일 (있는 경우)
    location /static {
        alias /opt/rag-qa-system/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 로그 설정
    access_log /var/log/nginx/rag-qa.access.log;
    error_log /var/log/nginx/rag-qa.error.log;
}
EOF
```

### 2단계: 사이트 활성화

```bash
# 1. 사이트 활성화
sudo ln -s /etc/nginx/sites-available/rag-qa /etc/nginx/sites-enabled/

# 2. 기본 사이트 비활성화 (필요시)
sudo rm -f /etc/nginx/sites-enabled/default

# 3. Nginx 설정 테스트
sudo nginx -t

# 4. Nginx 서비스 재시작
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 3단계: SSL/HTTPS 설정 (Let's Encrypt)

```bash
# 1. Certbot 설치
sudo apt install -y certbot python3-certbot-nginx

# 2. SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 3. 자동 갱신 설정
sudo systemctl enable certbot.timer
```

---

## 📊 모니터링 & 관리

### 1단계: 로그 확인 명령어

```bash
# RAG QA 시스템 로그
sudo journalctl -u rag-qa -f

# Ollama 서비스 로그
sudo journalctl -u ollama -f

# Nginx 로그
sudo tail -f /var/log/nginx/rag-qa.access.log
sudo tail -f /var/log/nginx/rag-qa.error.log

# 시스템 리소스 모니터링
htop
```

### 2단계: 서비스 상태 확인

```bash
# 모든 서비스 상태 확인
sudo systemctl status rag-qa ollama nginx

# 포트 사용 현황
sudo netstat -tlnp | grep -E ':(5000|11434|80|443)'

# 디스크 사용량
df -h /opt/rag-qa-system
```

### 3단계: 성능 모니터링

```bash
# CPU, 메모리 사용량
top -p $(pgrep -f "python app.py")

# 로드 평균
uptime

# 디스크 I/O
iostat -x 1
```

### 4단계: 백업 스크립트

```bash
# 백업 스크립트 생성
sudo tee /opt/backup-rag-qa.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/rag-qa-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 소스 코드 백업
tar -czf "$BACKUP_DIR/source.tar.gz" /opt/rag-qa-system --exclude="venv" --exclude="data/vectordb"

# 벡터 DB 백업
cp -r /opt/rag-qa-system/data/vectordb "$BACKUP_DIR/"

# 설정 파일 백업
cp /opt/rag-qa-system/.env "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
EOF

# 실행 권한 부여
sudo chmod +x /opt/backup-rag-qa.sh
```

### 5단계: 자동 시작 확인

```bash
# 부팅 시 자동 시작 서비스 확인
sudo systemctl list-unit-files | grep -E "(ollama|rag-qa|nginx)" | grep enabled
```

---

## 🔧 트러블슈팅

### 일반적인 문제들

1. **Ollama가 시작되지 않는 경우**
```bash
# 로그 확인
sudo journalctl -u ollama -n 50

# 포트 충돌 확인
sudo lsof -i :11434
```

2. **Python 애플리케이션이 시작되지 않는 경우**
```bash
# 수동 실행으로 에러 확인
cd /opt/rag-qa-system
source venv/bin/activate
python app.py
```

3. **메모리 부족 문제**
```bash
# 스왑 파일 생성 (임시 해결)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

4. **권한 문제**
```bash
# 파일 권한 재설정
sudo chown -R $USER:$USER /opt/rag-qa-system
chmod -R 755 /opt/rag-qa-system
```

---

## ✅ 설치 완료 체크리스트

- [ ] Ollama 서비스 정상 동작
- [ ] 기본 LLM 모델 다운로드 완료
- [ ] Python 가상환경 설정 완료
- [ ] 환경변수 설정 완료
- [ ] RAG QA 서비스 정상 시작
- [ ] Nginx 프록시 설정 완료
- [ ] 방화벽 포트 개방 완료
- [ ] 헬스체크 API 응답 정상
- [ ] 웹 UI 접속 가능
- [ ] Swagger API 문서 접근 가능

---

**설치 완료 후 접속 URL:**
- 메인 애플리케이션: `http://your-domain.com/`
- Swagger API 문서: `http://your-domain.com/swagger/`
- 관리자 패널: `http://your-domain.com/enhanced`

**생성일**: 2024년 12월 19일  
**버전**: 1.0  
**대상**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+