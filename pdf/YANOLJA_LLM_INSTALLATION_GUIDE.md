# 🚀 야놀자 LLM + RAG QA 시스템 설치 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [야놀자 LLM 설치 (Ollama)](#야놀자-llm-설치-ollama)
3. [Python RAG 시스템 설치](#python-rag-시스템-설치)
4. [서비스 설정](#서비스-설정)
5. [Nginx 설정](#nginx-설정)
6. [야놀자 LLM 통합 설정](#야놀자-llm-통합-설정)
7. [모니터링 & 관리](#모니터링--관리)

---

## 🖥 시스템 요구사항

### 야놀자 LLM 권장 사양
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 8 코어 이상 (Intel Xeon 또는 AMD EPYC 권장)
- **RAM**: 32GB 이상 (야놀자 LLM 7B 모델 기준)
- **Storage**: 200GB SSD (모델 저장 + 캐시용)
- **Network**: 고속 인터넷 연결 (초기 모델 다운로드용)
- **GPU**: NVIDIA GPU 16GB+ (옵션, 추론 성능 향상용)

### 최소 사양
- **CPU**: 6 코어
- **RAM**: 16GB
- **Storage**: 100GB SSD
- **Network**: 100Mbps 이상

---

## 🏢 야놀자 LLM 설치 (Ollama)

### 1단계: 시스템 업데이트 및 기본 패키지 설치

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git python3 python3-pip python3-venv nginx htop

# CentOS/RHEL/Rocky Linux  
sudo dnf update -y
sudo dnf install -y curl wget git python3 python3-pip nginx htop

# 필수 개발 도구 설치
sudo apt install -y build-essential cmake
```

### 2단계: Ollama 설치

```bash
# 1. Ollama 설치 스크립트 실행
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 설치 확인
ollama --version

# 3. Ollama 서비스 상태 확인
systemctl status ollama
```

### 3단계: 야놀자 전용 사용자 및 디렉토리 생성

```bash
# 1. ollama 및 야놀자 시스템 사용자 생성
sudo useradd -r -s /bin/false -d /opt/ollama ollama
sudo useradd -r -s /bin/false -d /opt/yanolja yanolja

# 2. 야놀자 LLM 전용 디렉토리 생성
sudo mkdir -p /opt/yanolja/{models,data,logs,cache}
sudo mkdir -p /opt/ollama/models
sudo chown -R ollama:ollama /opt/ollama
sudo chown -R yanolja:yanolja /opt/yanolja

# 3. 모델 다운로드용 임시 공간 확보
sudo mkdir -p /tmp/yanolja-models
sudo chmod 777 /tmp/yanolja-models
```

### 4단계: 야놀자 LLM 최적화 Ollama 서비스 설정

```bash
# 야놀자 LLM 전용 Ollama 서비스 파일 생성
sudo tee /etc/systemd/system/yanolja-ollama.service <<'EOF'
[Unit]
Description=Yanolja LLM Server (Ollama)
Documentation=https://ollama.ai/
After=network.target

[Service]
Type=exec
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=5
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/opt/yanolja/models"
Environment="OLLAMA_DATA=/opt/yanolja/data"
Environment="OLLAMA_DEBUG=1"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_MAX_QUEUE=512"

# 야놀자 LLM 성능 최적화 설정
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_VRAM=16G"

# 리소스 제한 (야놀자 LLM에 맞게 조정)
MemoryMax=24G
CPUQuota=800%

[Install]
WantedBy=multi-user.target
EOF
```

### 5단계: 야놀자 LLM 서비스 시작

```bash
# 1. 기존 ollama 서비스 중지 (충돌 방지)
sudo systemctl stop ollama
sudo systemctl disable ollama

# 2. 야놀자 LLM 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable yanolja-ollama
sudo systemctl start yanolja-ollama

# 3. 서비스 상태 확인
sudo systemctl status yanolja-ollama
```

### 6단계: 야놀자 LLM 모델 다운로드

```bash
# 1. 야놀자 공식 LLM 모델 설치 (실제 모델명으로 변경 필요)
sudo -u ollama ollama pull yanolja/travel-assistant:7b
sudo -u ollama ollama pull yanolja/hotel-recommendation:7b  
sudo -u ollama ollama pull yanolja/travel-korean:13b

# 2. 야놀자 특화 모델들 (용도별)
sudo -u ollama ollama pull yanolja/customer-service:7b
sudo -u ollama ollama pull yanolja/booking-assistant:7b
sudo -u ollama ollama pull yanolja/travel-qa:7b

# 3. 백업용 한국어 모델 (야놀자 모델 실패시 대체용)
sudo -u ollama ollama pull llama3.2:3b-instruct-korean
sudo -u ollama ollama pull solar:10.7b-instruct-v1-q4_0

# 4. 설치된 모델 확인
sudo -u ollama ollama list

# 5. 야놀자 모델 테스트
sudo -u ollama ollama run yanolja/travel-assistant:7b "야놀자 서비스에 대해 알려주세요"
```

### 7단계: 야놀자 LLM 성능 최적화

```bash
# 1. 시스템 성능 튜닝
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 2. 메모리 사용량 최적화
sudo tee -a /etc/security/limits.conf <<EOF
ollama soft nofile 65536
ollama hard nofile 65536
ollama soft memlock unlimited
ollama hard memlock unlimited
EOF

# 3. CPU 거버너 설정 (성능 우선)
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### 8단계: 야놀자 LLM API 테스트

```bash
# 1. 기본 연결 테스트
curl http://localhost:11434/api/tags

# 2. 야놀자 모델 추론 테스트
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "yanolja/travel-assistant:7b",
    "prompt": "제주도 여행 추천 일정을 3박 4일로 알려주세요",
    "stream": false,
    "options": {
      "temperature": 0.7,
      "top_p": 0.9,
      "max_tokens": 1000
    }
  }'

# 3. 성능 벤치마크 테스트
time curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "yanolja/travel-assistant:7b",
    "prompt": "안녕하세요",
    "stream": false
  }'
```

---

## 🐍 Python RAG 시스템 설치 (야놀자 특화)

### 1단계: 야놀자 프로젝트 디렉토리 설정

```bash
# 1. 야놀자 RAG 시스템 디렉토리 생성
sudo mkdir -p /opt/yanolja-rag-system
cd /opt/yanolja-rag-system

# 2. 현재 사용자에게 권한 부여
sudo chown -R $USER:$USER /opt/yanolja-rag-system
```

### 2단계: 야놀자 특화 소스 코드 배포

```bash
# Git을 통한 클론 (권장)
git clone <your-yanolja-rag-repository> .

# 또는 기존 소스 복사 후 야놀자 설정 적용
cp -r /mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/rag-qa-system/* .
```

### 3단계: 야놀자 전용 Python 가상환경 설정

```bash
# 1. Python 3.9+ 설치 확인 (야놀자 LLM 호환성)
python3 --version

# 2. 야놀자 전용 가상환경 생성
cd /opt/yanolja-rag-system
python3 -m venv yanolja-venv

# 3. 가상환경 활성화
source yanolja-venv/bin/activate

# 4. pip 업그레이드
pip install --upgrade pip

# 5. 야놀자 특화 의존성 패키지 설치
pip install -r requirements.txt

# 6. 야놀자 추가 패키지 설치
pip install ollama==0.2.1 korean-tokenizer fastapi uvicorn
```

### 4단계: 야놀자 특화 환경변수 설정

```bash
# 야놀자 전용 .env 파일 생성
tee /opt/yanolja-rag-system/.env <<'EOF'
# 야놀자 프로젝트 설정
PROJECT_NAME=YANOLJA_RAG_SYSTEM
COMPANY=YANOLJA
VERSION=1.0.0

# OpenAI API Key (백업용)
OPENAI_API_KEY=your_openai_api_key_here

# Flask 설정
FLASK_DEBUG=False
FLASK_PORT=5000
SECRET_KEY=yanolja_secret_key_2024

# 야놀자 LLM (Ollama) 설정
OLLAMA_BASE_URL=http://localhost:11434
PRIMARY_LLM_MODEL=yanolja/travel-assistant:7b
SECONDARY_LLM_MODEL=yanolja/travel-qa:7b
FALLBACK_LLM_MODEL=llama3.2:3b-instruct-korean

# 야놀자 특화 모델 설정
YANOLJA_TRAVEL_MODEL=yanolja/travel-assistant:7b
YANOLJA_HOTEL_MODEL=yanolja/hotel-recommendation:7b
YANOLJA_CS_MODEL=yanolja/customer-service:7b

# 벡터 DB 설정
CHROMA_PERSIST_DIRECTORY=/opt/yanolja-rag-system/data/vectordb
EMBEDDING_MODEL=text-embedding-ada-002

# 야놀자 비즈니스 설정
YANOLJA_API_TIMEOUT=30
YANOLJA_MAX_RETRIES=3
YANOLJA_CACHE_TTL=3600

# 로그 설정
LOG_LEVEL=INFO
LOG_FILE=/opt/yanolja-rag-system/logs/yanolja-rag.log
EOF

# 환경변수 파일 보안 설정
chmod 600 /opt/yanolja-rag-system/.env
```

### 5단계: 야놀자 특화 디렉토리 구조 생성

```bash
# 야놀자 비즈니스 로직용 디렉토리들 생성
mkdir -p /opt/yanolja-rag-system/{
    data/{vectordb,documents,cache,config},
    logs,
    yanolja/{models,services,templates},
    backup,
    monitoring
}

# 권한 설정
chown -R $USER:$USER /opt/yanolja-rag-system/data
chown -R $USER:$USER /opt/yanolja-rag-system/logs
```

---

## 🔧 야놀자 서비스 설정

### 1단계: 야놀자 RAG 시스템 서비스 생성

```bash
# 야놀자 전용 Systemd 서비스 파일 생성
sudo tee /etc/systemd/system/yanolja-rag.service <<EOF
[Unit]
Description=Yanolja RAG QA System with LLM
Documentation=https://yanolja.com/
After=network.target yanolja-ollama.service
Wants=yanolja-ollama.service
Requires=yanolja-ollama.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/yanolja-rag-system
ExecStart=/opt/yanolja-rag-system/yanolja-venv/bin/python app.py
Restart=always
RestartSec=10
Environment="PATH=/opt/yanolja-rag-system/yanolja-venv/bin"
EnvironmentFile=/opt/yanolja-rag-system/.env

# 야놀자 서비스 리소스 제한
MemoryMax=8G
CPUQuota=400%

# 보안 설정
NoNewPrivileges=yes
PrivateTmp=yes

# 야놀자 로깅 설정
StandardOutput=append:/opt/yanolja-rag-system/logs/service.log
StandardError=append:/opt/yanolja-rag-system/logs/error.log

[Install]
WantedBy=multi-user.target
EOF
```

### 2단계: 야놀자 서비스 시작

```bash
# 1. Systemd 데몬 리로드
sudo systemctl daemon-reload

# 2. 야놀자 RAG 서비스 활성화 및 시작
sudo systemctl enable yanolja-rag
sudo systemctl start yanolja-rag

# 3. 서비스 상태 확인
sudo systemctl status yanolja-rag

# 4. 로그 실시간 확인
tail -f /opt/yanolja-rag-system/logs/service.log
```

---

## 🌐 야놀자 Nginx 설정

### 1단계: 야놀자 전용 Nginx 설정

```bash
# 야놀자 RAG 시스템용 Nginx 설정 파일 생성
sudo tee /etc/nginx/sites-available/yanolja-rag <<'EOF'
server {
    listen 80;
    server_name yanolja-rag.company.com;  # 실제 도메인으로 변경
    
    # 야놀자 브랜딩
    add_header X-Powered-By "Yanolja RAG System";
    
    # 클라이언트 업로드 크기 제한 (야놀자 문서용)
    client_max_body_size 500M;
    
    # 메인 야놀자 RAG 애플리케이션
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Company "Yanolja";
        
        # 야놀자 LLM 스트리밍 최적화
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
    }
    
    # 야놀자 API 엔드포인트
    location /api/yanolja {
        proxy_pass http://127.0.0.1:5000/api/yanolja;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Swagger UI (야놀자 내부용)
    location /swagger {
        proxy_pass http://127.0.0.1:5000/swagger;
        # 내부 IP만 접근 허용 (보안)
        allow 192.168.0.0/16;
        allow 10.0.0.0/8;
        deny all;
    }
    
    # 야놀자 정적 파일
    location /static {
        alias /opt/yanolja-rag-system/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }
    
    # 로그 설정
    access_log /var/log/nginx/yanolja-rag.access.log;
    error_log /var/log/nginx/yanolja-rag.error.log;
}
EOF
```

### 2단계: 야놀자 사이트 활성화

```bash
# 1. 사이트 활성화
sudo ln -s /etc/nginx/sites-available/yanolja-rag /etc/nginx/sites-enabled/

# 2. Nginx 설정 테스트
sudo nginx -t

# 3. Nginx 재시작
sudo systemctl restart nginx
```

---

## 🏢 야놀자 LLM 통합 설정

### 1단계: config.py 야놀자 특화 수정

```bash
# config.py 백업 후 야놀자 설정 적용
cp /opt/yanolja-rag-system/config.py /opt/yanolja-rag-system/config.py.backup

# 야놀자 특화 config.py 생성
tee /opt/yanolja-rag-system/config.py <<'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

class YanoljaConfig:
    # 야놀자 프로젝트 정보
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'YANOLJA_RAG_SYSTEM')
    COMPANY = os.getenv('COMPANY', 'YANOLJA')
    VERSION = os.getenv('VERSION', '1.0.0')
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Flask 설정
    SECRET_KEY = os.getenv('SECRET_KEY', 'yanolja-secret-2024')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # 야놀자 LLM 설정 (Ollama)
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    # 야놀자 특화 모델 설정
    YANOLJA_MODELS = {
        'travel_assistant': {
            'model_name': os.getenv('YANOLJA_TRAVEL_MODEL', 'yanolja/travel-assistant:7b'),
            'temperature': 0.7,
            'max_tokens': 2000,
            'system_prompt': """당신은 야놀자의 여행 전문 AI 어시스턴트입니다. 
                             한국의 여행, 숙박, 맛집에 대한 전문적이고 정확한 정보를 제공하세요."""
        },
        'hotel_recommendation': {
            'model_name': os.getenv('YANOLJA_HOTEL_MODEL', 'yanolja/hotel-recommendation:7b'),
            'temperature': 0.5,
            'max_tokens': 2000,
            'system_prompt': """당신은 야놀자의 숙박 추천 전문가입니다. 
                             고객의 요구사항에 맞는 최적의 숙박시설을 추천하세요."""
        },
        'customer_service': {
            'model_name': os.getenv('YANOLJA_CS_MODEL', 'yanolja/customer-service:7b'),
            'temperature': 0.3,
            'max_tokens': 1500,
            'system_prompt': """당신은 야놀자 고객서비스 전문 AI입니다. 
                             친절하고 정확한 고객 응대를 제공하세요."""
        }
    }
    
    # 벡터 DB 설정
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './data/vectordb')
    CHROMA_COLLECTION_NAME = 'yanolja_documents'
    
    # 야놀자 비즈니스 설정
    API_TIMEOUT = int(os.getenv('YANOLJA_API_TIMEOUT', 30))
    MAX_RETRIES = int(os.getenv('YANOLJA_MAX_RETRIES', 3))
    CACHE_TTL = int(os.getenv('YANOLJA_CACHE_TTL', 3600))

# 호환성을 위한 Config 클래스 (기존 코드 유지)
Config = YanoljaConfig
EOF
```

### 2단계: 야놀자 LLM 클라이언트 생성

```bash
# 야놀자 전용 LLM 클라이언트 생성
tee /opt/yanolja-rag-system/yanolja/yanolja_llm_client.py <<'EOF'
import ollama
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class YanoljaLLMClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.client = ollama.Client(host=base_url)
        self.models = {
            'travel': 'yanolja/travel-assistant:7b',
            'hotel': 'yanolja/hotel-recommendation:7b',
            'cs': 'yanolja/customer-service:7b'
        }
    
    def chat(self, 
             message: str, 
             model_type: str = 'travel',
             temperature: float = 0.7,
             context: Optional[List[str]] = None) -> str:
        """야놀자 LLM과 채팅"""
        try:
            model_name = self.models.get(model_type, self.models['travel'])
            
            # 컨텍스트가 있으면 추가
            if context:
                message = f"참고 정보:\n{chr(10).join(context)}\n\n질문: {message}"
            
            response = self.client.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': message}],
                options={
                    'temperature': temperature,
                    'top_p': 0.9,
                    'num_predict': 2000
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"야놀자 LLM 에러: {e}")
            return f"죄송합니다. 야놀자 AI 서비스에 일시적인 문제가 발생했습니다."
    
    def check_health(self) -> Dict:
        """야놀자 LLM 서비스 상태 체크"""
        try:
            models = self.client.list()
            yanolja_models = [m['name'] for m in models['models'] if 'yanolja' in m['name']]
            
            return {
                'status': 'healthy',
                'available_models': yanolja_models,
                'total_models': len(yanolja_models)
            }
        except Exception as e:
            return {
                'status': 'unhealthy', 
                'error': str(e)
            }
EOF
```

---

## 📊 야놀자 모니터링 & 관리

### 1단계: 야놀자 전용 모니터링 스크립트

```bash
# 야놀자 시스템 모니터링 스크립트 생성
tee /opt/yanolja-rag-system/monitoring/yanolja_monitor.sh <<'EOF'
#!/bin/bash

echo "🏢 야놀자 RAG 시스템 모니터링 대시보드"
echo "=========================================="

# 서비스 상태 확인
echo "🔧 서비스 상태:"
systemctl is-active yanolja-ollama && echo "✅ 야놀자 LLM: 활성" || echo "❌ 야놀자 LLM: 비활성"
systemctl is-active yanolja-rag && echo "✅ 야놀자 RAG: 활성" || echo "❌ 야놀자 RAG: 비활성"
systemctl is-active nginx && echo "✅ Nginx: 활성" || echo "❌ Nginx: 비활성"

# 포트 확인
echo -e "\n🌐 포트 상태:"
netstat -tlnp | grep -E ':(5000|11434|80|443)' || echo "포트 확인 필요"

# 메모리 사용량
echo -e "\n💾 메모리 사용량:"
free -h

# 야놀자 모델 상태
echo -e "\n🤖 야놀자 LLM 모델:"
curl -s http://localhost:11434/api/tags | jq -r '.models[] | select(.name | contains("yanolja")) | .name' 2>/dev/null || echo "모델 정보 확인 필요"

# 로그 확인 (최근 10줄)
echo -e "\n📋 최근 로그:"
tail -n 5 /opt/yanolja-rag-system/logs/service.log 2>/dev/null || echo "로그 파일 없음"
EOF

chmod +x /opt/yanolja-rag-system/monitoring/yanolja_monitor.sh
```

### 2단계: 야놀자 백업 스크립트

```bash
# 야놀자 시스템 백업 스크립트
tee /opt/yanolja-rag-system/backup/yanolja_backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/yanolja-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🏢 야놀자 RAG 시스템 백업 시작..."

# 소스 코드 백업 (가상환경 제외)
tar -czf "$BACKUP_DIR/yanolja-source.tar.gz" /opt/yanolja-rag-system --exclude="yanolja-venv" --exclude="data/vectordb" --exclude="logs"

# 벡터 DB 백업
cp -r /opt/yanolja-rag-system/data/vectordb "$BACKUP_DIR/"

# 설정 파일 백업
cp /opt/yanolja-rag-system/.env "$BACKUP_DIR/"
cp /etc/systemd/system/yanolja-*.service "$BACKUP_DIR/"

# Nginx 설정 백업
cp /etc/nginx/sites-available/yanolja-rag "$BACKUP_DIR/"

echo "✅ 야놀자 백업 완료: $BACKUP_DIR"
EOF

chmod +x /opt/yanolja-rag-system/backup/yanolja_backup.sh
```

### 3단계: Cron 작업 설정

```bash
# 야놀자 시스템 자동화 작업 설정
crontab -e

# 다음 내용 추가:
# 매일 새벽 2시 야놀자 시스템 백업
0 2 * * * /opt/yanolja-rag-system/backup/yanolja_backup.sh

# 매 시간마다 야놀자 서비스 상태 체크
0 * * * * /opt/yanolja-rag-system/monitoring/yanolja_monitor.sh >> /opt/yanolja-rag-system/logs/monitor.log
```

---

## ✅ 야놀자 설치 완료 체크리스트

### 🤖 야놀자 LLM 서비스
- [ ] Ollama 서비스 정상 동작
- [ ] 야놀자 LLM 모델 다운로드 완료
  - [ ] `yanolja/travel-assistant:7b`
  - [ ] `yanolja/hotel-recommendation:7b`
  - [ ] `yanolja/customer-service:7b`
- [ ] 야놀자 LLM API 응답 테스트 통과
- [ ] 모델 성능 벤치마크 완료

### 🐍 Python RAG 시스템
- [ ] 야놀자 전용 가상환경 설정 완료
- [ ] 야놀자 특화 환경변수 설정 완료
- [ ] 야놀자 RAG 서비스 정상 시작
- [ ] 야놀자 LLM 통합 테스트 완료

### 🌐 웹 서비스
- [ ] Nginx 야놀자 설정 완료
- [ ] 야놀자 도메인 접속 가능
- [ ] SSL/HTTPS 설정 완료 (선택사항)
- [ ] API 엔드포인트 정상 응답

### 📊 모니터링
- [ ] 야놀자 모니터링 스크립트 동작
- [ ] 로그 파일 정상 생성
- [ ] 백업 스크립트 동작 확인
- [ ] Cron 작업 등록 완료

---

## 🎯 야놀자 시스템 접속 정보

### 메인 서비스
- **야놀자 RAG 시스템**: `http://your-domain.com/`
- **야놀자 API 문서**: `http://your-domain.com/swagger/`
- **야놀자 관리자 패널**: `http://your-domain.com/enhanced`

### 야놀자 LLM 모델 사용법
```bash
# 여행 상담 모델
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "yanolja/travel-assistant:7b", "prompt": "제주도 3박4일 여행 계획 추천해주세요"}'

# 숙박 추천 모델  
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "yanolja/hotel-recommendation:7b", "prompt": "서울 명동 근처 호텔 추천해주세요"}'
```

---

**🏢 야놀자 RAG 시스템 설치 가이드**  
**생성일**: 2024년 12월 19일  
**버전**: 1.0  
**대상**: 야놀자 LLM + Ubuntu 20.04+  
**Contact**: 야놀자 AI팀